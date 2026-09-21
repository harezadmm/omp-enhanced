#!/usr/bin/env node
/**
 * Compact legacy telemetry/ files into monthly archives under archive/legacy/.
 *
 * Usage:
 *   node scripts/compact-hf-telemetry.mjs                  # dry-run (default)
 *   node scripts/compact-hf-telemetry.mjs --apply          # commit archives + delete legacy
 *
 * Requires: HF_TOKEN env var with write access to the dataset.
 *
 * Safety guarantees:
 *   - Dry-run is default; --apply required for any writes
 *   - FAIL-CLOSED: aborts on ANY download failure
 *   - Paginates the full file listing (HF API returns max 1000/page)
 *   - RESUMABLE: derives a stable run ID from source file list hash;
 *     stores archives under archive/legacy/<runId>/. On rerun after partial
 *     deletion, detects existing manifest and resumes deletion from the
 *     manifest's original source list — never rebuilds archives from a
 *     reduced file set.
 *   - Verifies ALL uploaded artifacts (archives + manifest + invalid-records)
 *     by re-downloading and checking checksums
 *   - Batches delete operations (max 50 per HF commit)
 *   - Preserves FULL invalid lines in a separate artifact
 *   - Post-deletion relist confirms all manifest sources are gone
 */

const HF_API = 'https://huggingface.co/api';
const DATASET_REPO = process.env.HF_DATASET_REPO || 'pliny-the-prompter/g0dm0d3';
const BRANCH = process.env.HF_DATASET_BRANCH || 'main';
const TOKEN = process.env.HF_TOKEN;
const APPLY = process.argv.includes('--apply');
const DELETE_BATCH_SIZE = 50;

if (!TOKEN) {
  console.error('ERROR: HF_TOKEN environment variable required');
  process.exit(1);
}

const headers = { Authorization: `Bearer ${TOKEN}` };

// ── Paginated file listing ──────────────────────────────────────────
async function listAllFiles(prefix, recursive = false) {
  const allFiles = [];
  let cursor = null;

  while (true) {
    const params = new URLSearchParams();
    if (cursor) params.set('cursor', cursor);
    if (recursive) params.set('recursive', 'true');
    const url = `${HF_API}/datasets/${DATASET_REPO}/tree/${BRANCH}/${prefix}?${params}`;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`List failed (${res.status}): ${await res.text()}`);

    const page = await res.json();
    if (!Array.isArray(page) || page.length === 0) break;

    allFiles.push(...page);
    console.log(`  Listed ${allFiles.length} entries so far...`);

    const linkHeader = res.headers.get('link') || '';
    const nextMatch = linkHeader.match(/<[^>]*[?&]cursor=([^&>]+)[^>]*>;\s*rel="next"/);
    if (nextMatch) {
      cursor = decodeURIComponent(nextMatch[1]);
    } else {
      break;
    }
  }

  return allFiles;
}

async function downloadFile(path) {
  const url = `https://huggingface.co/datasets/${DATASET_REPO}/resolve/${BRANCH}/${path}`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`Download failed (${res.status}): ${path}`);
  return res.text();
}

async function fileExists(path) {
  const url = `https://huggingface.co/datasets/${DATASET_REPO}/resolve/${BRANCH}/${path}`;
  const res = await fetch(url, { method: 'HEAD', headers });
  return res.ok;
}

async function sha256(text) {
  const data = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

function utf8ToBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let binStr = '';
  for (let i = 0; i < bytes.length; i++) binStr += String.fromCharCode(bytes[i]);
  return btoa(binStr);
}

async function commitFiles(operations, summary) {
  const url = `${HF_API}/datasets/${DATASET_REPO}/commit/${BRANCH}`;
  const lines = [
    JSON.stringify({ key: 'header', value: { summary } }),
    ...operations.map(op => JSON.stringify({ key: op.key, value: op.value })),
  ];
  const res = await fetch(url, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/x-ndjson' },
    body: lines.join('\n'),
  });
  if (!res.ok) throw new Error(`Commit failed (${res.status}): ${(await res.text()).slice(0, 500)}`);
  return res.json();
}

// ── Derive stable run ID from the sorted source file list ───────────
async function deriveRunId(sourceFiles) {
  const pathList = sourceFiles.map(f => f.path).sort().join('\n');
  const hash = await sha256(pathList);
  return hash.slice(0, 12);
}

async function main() {
  console.log(`Mode: ${APPLY ? 'APPLY (will write)' : 'DRY-RUN (read-only)'}`);
  console.log(`Repo: ${DATASET_REPO} (branch: ${BRANCH})`);
  console.log('');

  // ── Step 1: Paginated listing ─────────────────────────────────────
  console.log('Step 1: Listing ALL legacy telemetry/ files (paginated)...');
  const allEntries = await listAllFiles('telemetry');
  const jsonlFiles = allEntries.filter(f => f.type === 'file' && f.path.endsWith('.jsonl'));
  console.log(`  Total entries: ${allEntries.length}`);
  console.log(`  JSONL files: ${jsonlFiles.length}`);

  if (jsonlFiles.length === 0) {
    console.log('  Nothing to compact. Done.');
    return;
  }

  // ── Step 2: Check for existing manifest (resume detection) ────────
  // Derive run ID from the FULL original source list. If a prior run
  // already archived everything, its manifest contains the original
  // source paths — we can resume deletion without re-downloading.
  const currentRunId = await deriveRunId(jsonlFiles);
  const runDir = `archive/legacy/${currentRunId}`;
  const manifestPath = `${runDir}/manifest.json`;

  console.log('');
  console.log(`Step 2: Checking for existing manifest (run ID: ${currentRunId})...`);

  // Also check if a DIFFERENT run's manifest exists (partial deletion scenario)
  let archiveLegacyEntries = [];
  try {
    archiveLegacyEntries = await listAllFiles('archive/legacy', true);
  } catch (err) {
    if (!/404|EntryNotFound|does not exist/i.test(String(err.message))) throw err;
  }
  const existingManifests = archiveLegacyEntries.filter(
    f => f.type === 'file' && f.path.endsWith('/manifest.json')
  );

  let resumeManifest = null;

  if (existingManifests.length > 0) {
    // Check each manifest to see if it contains source files that are now missing
    // (meaning deletion already started from that run)
    for (const mf of existingManifests) {
      try {
        const mfContent = await downloadFile(mf.path);
        const mfData = JSON.parse(mfContent);
        if (mfData.sourceFilePaths && Array.isArray(mfData.sourceFilePaths)) {
          const currentPaths = new Set(jsonlFiles.map(f => f.path));
          const manifestPaths = new Set(mfData.sourceFilePaths);

          // If manifest has paths that no longer exist, deletion already started
          const alreadyDeleted = mfData.sourceFilePaths.filter(p => !currentPaths.has(p));
          if (alreadyDeleted.length > 0) {
            console.log(`  Found prior manifest at ${mf.path}`);
            console.log(`    Original sources: ${mfData.sourceFilePaths.length}`);
            console.log(`    Already deleted: ${alreadyDeleted.length}`);
            console.log(`    Remaining: ${mfData.sourceFilePaths.length - alreadyDeleted.length}`);
            console.log('  RESUMING from prior manifest (archives already verified).');
            resumeManifest = mfData;
            break;
          }

          // If current files exactly match or are a superset, this is a fresh run
          // for the same data — use the existing archives if checksums match
          if (mf.path === manifestPath) {
            console.log(`  Found matching manifest at ${manifestPath}`);
            console.log('  Verifying existing archives...');
            let allValid = true;
            for (const arch of mfData.archives) {
              try {
                const content = await downloadFile(arch.path);
                const checksum = await sha256(content);
                if (checksum !== arch.checksum) {
                  console.error(`    CHECKSUM MISMATCH: ${arch.path}`);
                  allValid = false;
                  break;
                }
              } catch {
                console.error(`    MISSING: ${arch.path}`);
                allValid = false;
                break;
              }
            }
            if (allValid) {
              console.log('  All archives verified. Resuming deletion phase.');
              resumeManifest = mfData;
              break;
            } else {
              console.log('  Archives invalid — rebuilding from scratch.');
            }
          }
        }
      } catch (err) {
        console.warn(`  Could not parse manifest ${mf.path}: ${err.message}`);
      }
    }
  }

  // ── RESUME PATH: skip download/archive, go straight to deletion ───
  if (resumeManifest) {
    if (!APPLY) {
      const remaining = resumeManifest.sourceFilePaths.filter(
        p => jsonlFiles.some(f => f.path === p)
      );
      console.log('');
      console.log('DRY-RUN: Would resume deletion of remaining files.');
      console.log(`  Files still to delete: ${remaining.length}`);
      console.log(`  Batches: ${Math.ceil(remaining.length / DELETE_BATCH_SIZE)}`);
      return;
    }

    // Delete only files that still exist AND are in the manifest
    const manifestPathSet = new Set(resumeManifest.sourceFilePaths);
    const toDelete = jsonlFiles.filter(f => manifestPathSet.has(f.path));

    console.log('');
    console.log(`Resuming deletion: ${toDelete.length} files remaining...`);

    const batches = [];
    for (let i = 0; i < toDelete.length; i += DELETE_BATCH_SIZE) {
      batches.push(toDelete.slice(i, i + DELETE_BATCH_SIZE));
    }

    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i];
      const deleteOps = batch.map(f => ({
        key: 'deletedFile',
        value: { path: f.path },
      }));
      await commitFiles(deleteOps, `[maintenance] Remove legacy telemetry batch ${i + 1}/${batches.length} (${batch.length} files)`);
      console.log(`  Batch ${i + 1}/${batches.length}: deleted ${batch.length} files`);
    }

    // Post-deletion verification
    console.log('');
    console.log('Post-deletion verification: relisting telemetry/...');
    const remaining = await listAllFiles('telemetry');
    const remainingJsonl = remaining.filter(f => f.type === 'file' && f.path.endsWith('.jsonl'));
    const leftover = remainingJsonl.filter(f => manifestPathSet.has(f.path));
    if (leftover.length > 0) {
      console.error(`  WARNING: ${leftover.length} manifest sources still exist after deletion!`);
      console.error('  Paths:', leftover.map(f => f.path).slice(0, 10).join(', '));
      process.exit(1);
    }
    console.log(`  Confirmed: 0 manifest sources remain. ${remainingJsonl.length} non-manifest files present.`);

    console.log('');
    console.log('DONE (resumed). Legacy telemetry compacted successfully.');
    return;
  }

  // ── FRESH PATH: download, archive, verify, delete ─────────────────

  // ── Step 3: Download and parse ALL files (fail-closed) ────────────
  console.log('');
  console.log('Step 3: Downloading and parsing events (fail-closed)...');
  const monthBuckets = {};
  let totalEvents = 0;
  let totalSourceBytes = 0;
  let downloadFailures = 0;
  let invalidLines = 0;
  const invalidRecords = [];
  const failedFiles = [];

  for (let i = 0; i < jsonlFiles.length; i++) {
    const file = jsonlFiles[i];
    if (i % 200 === 0 || i === jsonlFiles.length - 1) {
      console.log(`  Progress: ${i + 1}/${jsonlFiles.length} files...`);
    }

    let content;
    try {
      content = await downloadFile(file.path);
    } catch (err) {
      downloadFailures++;
      failedFiles.push({ path: file.path, error: err.message });
      continue;
    }

    totalSourceBytes += new TextEncoder().encode(content).byteLength;
    const lines = content.split('\n').filter(l => l.trim());

    for (const line of lines) {
      try {
        const event = JSON.parse(line);
        const ts = event.timestamp;
        let monthKey;
        if (ts && typeof ts === 'number') {
          const d = new Date(ts);
          monthKey = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
        } else {
          monthKey = 'unknown';
        }
        if (!monthBuckets[monthKey]) monthBuckets[monthKey] = [];
        monthBuckets[monthKey].push(line);
        totalEvents++;
      } catch {
        invalidLines++;
        invalidRecords.push({ file: file.path, line });
      }
    }
  }

  console.log(`  Total events parsed: ${totalEvents}`);
  console.log(`  Total source bytes: ${(totalSourceBytes / 1024 / 1024).toFixed(2)} MiB`);
  console.log(`  Download failures: ${downloadFailures}`);
  console.log(`  Invalid lines: ${invalidLines}`);
  console.log(`  Month buckets: ${Object.keys(monthBuckets).sort().join(', ')}`);

  // ── FAIL-CLOSED: abort if any downloads failed ────────────────────
  if (downloadFailures > 0) {
    console.error('');
    console.error(`ABORT: ${downloadFailures} file(s) failed to download.`);
    console.error('Cannot guarantee data preservation. Fix network/auth issues and retry.');
    console.error('Failed files:', failedFiles.map(f => f.path).join(', '));
    process.exit(1);
  }

  // ── Step 4: Build archives ────────────────────────────────────────
  console.log('');
  console.log(`Step 4: Building monthly archives under ${runDir}/...`);
  const archives = [];
  for (const [month, events] of Object.entries(monthBuckets).sort()) {
    const content = events.join('\n') + '\n';
    const checksum = await sha256(content);
    const archivePath = `${runDir}/telemetry-${month}.jsonl`;
    const bytes = new TextEncoder().encode(content).byteLength;
    archives.push({ month, path: archivePath, events: events.length, bytes, checksum, content });
    console.log(`  ${archivePath}: ${events.length} events, ${(bytes / 1024).toFixed(0)} KiB, sha256:${checksum.slice(0, 16)}...`);
  }

  // ── Step 5: Verify counts ─────────────────────────────────────────
  const archiveEventTotal = archives.reduce((s, a) => s + a.events, 0);
  const sourceFileCount = jsonlFiles.length;

  console.log('');
  console.log('Step 5: Count verification');
  console.log(`  Source files examined: ${sourceFileCount}`);
  console.log(`  Events parsed from sources: ${totalEvents}`);
  console.log(`  Events in archives: ${archiveEventTotal}`);
  console.log(`  Invalid lines preserved: ${invalidLines}`);

  if (archiveEventTotal !== totalEvents) {
    console.error('  COUNT MISMATCH — aborting. No changes made.');
    process.exit(1);
  }
  console.log('  COUNTS MATCH.');

  // ── Build manifest (includes full source path list for resumability) ─
  const invalidRecordsContent = invalidRecords.length > 0
    ? JSON.stringify(invalidRecords, null, 2)
    : null;
  const invalidRecordsChecksum = invalidRecordsContent
    ? await sha256(invalidRecordsContent)
    : null;

  const manifest = {
    runId: currentRunId,
    timestamp: new Date().toISOString(),
    repo: DATASET_REPO,
    branch: BRANCH,
    sourceFiles: sourceFileCount,
    sourceBytes: totalSourceBytes,
    sourceFilePaths: jsonlFiles.map(f => f.path).sort(),
    totalEvents,
    invalidLines,
    invalidRecordCount: invalidRecords.length,
    invalidRecordsChecksum,
    archives: archives.map(a => ({
      path: a.path, month: a.month, events: a.events,
      bytes: a.bytes, checksum: a.checksum,
    })),
  };

  const manifestContent = JSON.stringify(manifest, null, 2);
  const manifestChecksum = await sha256(manifestContent);

  console.log('');
  console.log('Manifest:');
  console.log(manifestContent);

  if (!APPLY) {
    console.log('');
    console.log('DRY-RUN complete. Re-run with --apply to commit changes.');
    console.log(`Would upload ${archives.length} archive files + manifest + invalid-records.`);
    console.log(`Would delete ${sourceFileCount} legacy files in ${Math.ceil(sourceFileCount / DELETE_BATCH_SIZE)} batches.`);
    return;
  }

  // ── Step 6: Upload archives ───────────────────────────────────────
  console.log('');
  console.log('Step 6: Uploading archives...');

  // Check if archives already exist and match (idempotent upload)
  let archivesAlreadyExist = false;
  if (await fileExists(manifestPath)) {
    try {
      const existing = await downloadFile(manifestPath);
      const existingChecksum = await sha256(existing);
      if (existingChecksum === manifestChecksum) {
        console.log('  Archives already uploaded (manifest checksum matches). Skipping upload.');
        archivesAlreadyExist = true;
      }
    } catch { /* not found or parse error — upload fresh */ }
  }

  if (!archivesAlreadyExist) {
    const uploadOps = archives.map(a => ({
      key: 'file',
      value: { content: utf8ToBase64(a.content), path: a.path, encoding: 'base64' },
    }));
    uploadOps.push({
      key: 'file',
      value: {
        content: utf8ToBase64(manifestContent),
        path: manifestPath,
        encoding: 'base64',
      },
    });
    if (invalidRecordsContent) {
      uploadOps.push({
        key: 'file',
        value: {
          content: utf8ToBase64(invalidRecordsContent),
          path: `${runDir}/invalid-records.json`,
          encoding: 'base64',
        },
      });
    }

    await commitFiles(uploadOps, `[maintenance] Archive ${totalEvents} legacy telemetry events into ${archives.length} monthly files (run ${currentRunId})`);
    console.log('  Archives committed.');
  }

  // ── Step 7: Verify ALL uploaded artifacts ─────────────────────────
  console.log('');
  console.log('Step 7: Verifying uploaded artifacts...');

  // Verify manifest
  const dlManifest = await downloadFile(manifestPath);
  const dlManifestChecksum = await sha256(dlManifest);
  if (dlManifestChecksum !== manifestChecksum) {
    console.error(`  MANIFEST CHECKSUM MISMATCH!`);
    console.error(`    Expected: ${manifestChecksum}`);
    console.error(`    Got:      ${dlManifestChecksum}`);
    console.error('  ABORTING — will not delete sources.');
    process.exit(1);
  }
  console.log(`  ${manifestPath}: checksum verified`);

  // Verify each archive
  for (const archive of archives) {
    const downloaded = await downloadFile(archive.path);
    const remoteChecksum = await sha256(downloaded);
    if (remoteChecksum !== archive.checksum) {
      console.error(`  CHECKSUM MISMATCH for ${archive.path}!`);
      console.error(`    Expected: ${archive.checksum}`);
      console.error(`    Got:      ${remoteChecksum}`);
      console.error('  ABORTING — archives uploaded but legacy files NOT deleted.');
      process.exit(1);
    }
    console.log(`  ${archive.path}: checksum verified`);
  }

  // Verify invalid-records if present
  if (invalidRecordsContent) {
    const dlInvalid = await downloadFile(`${runDir}/invalid-records.json`);
    const dlInvalidChecksum = await sha256(dlInvalid);
    if (dlInvalidChecksum !== invalidRecordsChecksum) {
      console.error(`  INVALID-RECORDS CHECKSUM MISMATCH!`);
      console.error('  ABORTING — will not delete sources.');
      process.exit(1);
    }
    console.log(`  ${runDir}/invalid-records.json: checksum verified`);
  }

  console.log('  All artifacts verified.');

  // ── Step 8: Delete legacy files in batches ────────────────────────
  console.log('');
  console.log(`Step 8: Deleting ${sourceFileCount} legacy files in batches of ${DELETE_BATCH_SIZE}...`);
  const batches = [];
  for (let i = 0; i < jsonlFiles.length; i += DELETE_BATCH_SIZE) {
    batches.push(jsonlFiles.slice(i, i + DELETE_BATCH_SIZE));
  }

  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const deleteOps = batch.map(f => ({
      key: 'deletedFile',
      value: { path: f.path },
    }));
    await commitFiles(deleteOps, `[maintenance] Remove legacy telemetry batch ${i + 1}/${batches.length} (${batch.length} files)`);
    console.log(`  Batch ${i + 1}/${batches.length}: deleted ${batch.length} files`);
  }

  // ── Step 9: Post-deletion verification ────────────────────────────
  console.log('');
  console.log('Step 9: Post-deletion verification...');
  const postDeleteEntries = await listAllFiles('telemetry');
  const postDeleteJsonl = postDeleteEntries.filter(f => f.type === 'file' && f.path.endsWith('.jsonl'));
  const sourcePathSet = new Set(jsonlFiles.map(f => f.path));
  const leftover = postDeleteJsonl.filter(f => sourcePathSet.has(f.path));

  if (leftover.length > 0) {
    console.error(`  WARNING: ${leftover.length} source files still exist after deletion!`);
    console.error('  First 10:', leftover.slice(0, 10).map(f => f.path).join(', '));
    console.error('  Rerun with --apply to retry deletion of remaining files.');
    process.exit(1);
  }
  console.log(`  Confirmed: all ${sourceFileCount} manifest sources deleted.`);
  if (postDeleteJsonl.length > 0) {
    console.log(`  Note: ${postDeleteJsonl.length} non-manifest JSONL files remain (new incoming data).`);
  }

  console.log('');
  console.log('DONE. Legacy telemetry compacted successfully.');
  console.log(`  Run ID: ${currentRunId}`);
  console.log(`  ${archives.length} monthly archives in ${runDir}/`);
  console.log(`  ${sourceFileCount} legacy files removed`);
  console.log(`  ${totalEvents} events preserved`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
