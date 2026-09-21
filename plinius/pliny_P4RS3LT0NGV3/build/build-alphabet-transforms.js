#!/usr/bin/env node
/**
 * Generate symbol-alphabet transforms from data/alphabets/*.json
 * Output: src/transformers/symbol/<slug>.js (regenerated each build)
 */

const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const dataDir = path.join(root, 'data', 'alphabets');
const outDir = path.join(root, 'src', 'transformers', 'symbol');
const GENERATED_HEADER = '// @generated from data/alphabets — do not edit by hand\n';

function slugToExportName(slug) {
    return slug.replace(/-/g, '_');
}

function escapeJsString(s) {
    return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function escapeRegexCharClass(ch) {
    return ch.replace(/\\/g, '\\\\').replace(/\]/g, '\\]');
}

function buildDetectorBlock(entry) {
    if (entry.detectorHint) {
        return `,
    detector: function(text) {
        return new RegExp('${escapeJsString(entry.detectorHint)}', 'u').test(text);
    }`;
    }
    const chars = [...new Set(Object.values(entry.map))];
    if (chars.length === 0) return '';
    const classContent = chars.map(ch => escapeRegexCharClass(ch)).join('');
    return `,
    detector: function(text) {
        return /[${classContent}]/u.test(text);
    }`;
}

function buildMapObject(map) {
    const lines = [];
    for (const [key, value] of Object.entries(map)) {
        lines.push(`        '${escapeJsString(key)}': '${escapeJsString(value)}'`);
    }
    return lines.join(',\n');
}

function generateTransformFile(entry, slug) {
    const name = entry.name || slug;
    const priority = entry.priority != null ? entry.priority : 100;
    const description = entry.description ? `\n    description: '${escapeJsString(entry.description)}',` : '';
    const mapBlock = buildMapObject(entry.map);

    return `${GENERATED_HEADER}import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({
    name: '${escapeJsString(name)}',
    priority: ${priority},
    category: 'symbol',${description}
    map: {
${mapBlock}
    },
    func: function(text) {
        return [...text].map(c => this.map[c] || this.map[c.toUpperCase()] || c).join('');
    },
    preview: function(text) {
        if (!text) return '[${escapeJsString(slug)}]';
        return this.func(text.slice(0, 6)) + (text.length > 6 ? '…' : '');
    }${buildDetectorBlock(entry)}
});
`;
}

function validateEntry(entry, file) {
    if (!entry.name || !entry.map || typeof entry.map !== 'object') {
        throw new Error(`${file}: requires "name" and "map" object`);
    }
    const keys = Object.keys(entry.map);
    if (keys.length < 26) {
        console.warn(`⚠️  ${file}: map has only ${keys.length} entries`);
    }
}

function loadUnicodeMaps() {
    const unicodeDir = path.join(root, 'src', 'transformers', 'unicode');
    const maps = [];
    if (!fs.existsSync(unicodeDir)) return maps;
    for (const file of fs.readdirSync(unicodeDir)) {
        if (!file.endsWith('.js')) continue;
        const content = fs.readFileSync(path.join(unicodeDir, file), 'utf8');
        const nameMatch = content.match(/name:\s*'([^']+)'/);
        const map = {};
        for (const match of content.matchAll(/'([^']+)':\s*'([^']+)'/g)) {
            map[match[1]] = match[2];
        }
        if (Object.keys(map).length >= 20) {
            maps.push({ name: nameMatch ? nameMatch[1] : file, map });
        }
    }
    return maps;
}

function overlapScore(entryMap, existingMap) {
    let matched = 0;
    let total = 0;
    for (const [key, value] of Object.entries(entryMap)) {
        total++;
        const variants = [key, key.toLowerCase(), key.toUpperCase()];
        for (const variant of variants) {
            if (existingMap[variant] === value) {
                matched++;
                break;
            }
        }
    }
    return { matched, total };
}

function checkOverlap(entry, file, unicodeMaps) {
    for (const existing of unicodeMaps) {
        const { matched, total } = overlapScore(entry.map, existing.map);
        if (total >= 20 && matched / total >= 0.9) {
            throw new Error(
                `${file}: ${matched}/${total} glyphs match existing Unicode transform "${existing.name}" — use that instead or pick distinct symbols`
            );
        }
        if (total >= 20 && matched / total >= 0.75) {
            console.warn(`⚠️  ${file}: ${matched}/${total} glyphs overlap "${existing.name}"`);
        }
    }
}

function main() {
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
        console.log('Created data/alphabets/ (add JSON files to generate symbol transforms)');
        return;
    }

    fs.mkdirSync(outDir, { recursive: true });

    // Remove previously generated symbol transforms
    for (const file of fs.readdirSync(outDir)) {
        if (!file.endsWith('.js')) continue;
        const full = path.join(outDir, file);
        const head = fs.readFileSync(full, 'utf8').slice(0, 80);
        if (head.includes('@generated')) {
            fs.unlinkSync(full);
        }
    }

    const jsonFiles = fs.readdirSync(dataDir).filter(f => f.endsWith('.json')).sort();
    if (!jsonFiles.length) {
        console.log('No alphabet JSON files in data/alphabets/');
        return;
    }

    let count = 0;
    const unicodeMaps = loadUnicodeMaps();
    for (const file of jsonFiles) {
        const slug = file.replace(/\.json$/, '');
        const raw = fs.readFileSync(path.join(dataDir, file), 'utf8');
        const entry = JSON.parse(raw);
        validateEntry(entry, file);
        checkOverlap(entry, file, unicodeMaps);
        const outPath = path.join(outDir, `${slug}.js`);
        fs.writeFileSync(outPath, generateTransformFile(entry, slug), 'utf8');
        console.log(`✅ Alphabet: ${slug} → symbol/${slug}.js`);
        count++;
    }

    console.log(`\n✨ Generated ${count} symbol alphabet transform(s)`);
}

main();
