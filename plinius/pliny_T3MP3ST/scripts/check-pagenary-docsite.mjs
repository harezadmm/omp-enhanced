#!/usr/bin/env node
import { access, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = process.cwd();
const TENANT_ID = 't3mp3st-docs';
const DIST = join(ROOT, 'dist', TENANT_ID);
const TENANT = join(ROOT, 'docsite', TENANT_ID);

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

function fail(message) {
  console.error(`✖ ${message}`);
  process.exitCode = 1;
}

async function main() {
  const required = [
    'index.html',
    'manifest.js',
    'sitemap.xml',
    'robots.txt',
    'llms.txt',
    'search-index/manifest.json',
    'search-index/metadata.json',
    'content-index.json',
    'documents.jsonl',
  ];

  for (const rel of required) {
    if (!(await exists(join(DIST, rel)))) fail(`missing ${join('dist', TENANT_ID, rel)}`);
  }

  const manifest = await readJson(join(TENANT, 'manifest.json'));
  const expectedPages = flattenSections(manifest.sections || []).filter((section) => section.file).length;
  const metadata = await readJson(join(DIST, 'search-index', 'metadata.json'));
  const indexedPages = Array.isArray(metadata.pages) ? metadata.pages.length : 0;

  if (indexedPages !== expectedPages) {
    fail(`search metadata indexed ${indexedPages} page(s), expected ${expectedPages}`);
  }

  const sitemap = await readFile(join(DIST, 'sitemap.xml'), 'utf8');
  const sitemapUrls = [...sitemap.matchAll(/<url>/g)].length;
  if (sitemapUrls < expectedPages) {
    fail(`sitemap has ${sitemapUrls} URL(s), expected at least ${expectedPages}`);
  }

  const llms = await readFile(join(DIST, 'llms.txt'), 'utf8');
  if (!llms.includes('T3MP3ST Documentation') || !llms.includes('Getting Started')) {
    fail('llms.txt does not include expected site/page metadata');
  }

  if (process.exitCode) process.exit(process.exitCode);
  console.log(`Pagenary docsite artifacts verified: ${expectedPages} pages indexed.`);
}

function flattenSections(sections) {
  const out = [];
  for (const section of sections || []) {
    out.push(section);
    out.push(...flattenSections(section.sections || section.subsections || []));
  }
  return out;
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
