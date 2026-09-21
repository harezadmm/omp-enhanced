#!/usr/bin/env node

const assert = require('assert');
const path = require('path');
const vm = require('vm');
const fs = require('fs');

function createContext() {
    const store = {};
    const ctx = {
        window: null,
        globalThis: null,
        localStorage: {
            getItem: (key) => store[key] || null,
            setItem: (key, value) => { store[key] = value; }
        },
        console
    };
    ctx.window = ctx;
    ctx.globalThis = ctx;
    return { ctx, store };
}

function loadScript(ctx, relativePath) {
    const code = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
    vm.runInContext(code, vm.createContext(ctx), { filename: relativePath });
}

function buildAlphabet(prefix) {
    const alphabet = {};
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach((letter, index) => {
        alphabet[letter] = prefix + letter + index;
    });
    return alphabet;
}

const { ctx } = createContext();
loadScript(ctx, 'dist/js/bundles/transforms-bundle.js');
loadScript(ctx, 'js/core/spellingAlphabetTransform.js');
loadScript(ctx, 'js/core/customSpellingAlphabets.js');

const first = ctx.CustomSpellingAlphabets.saveMapping({
    name: 'Nautical Spelling Alphabet',
    category: 'nautical',
    alphabet: buildAlphabet('N')
});
const second = ctx.CustomSpellingAlphabets.saveMapping({
    name: 'Kitchen Spelling Alphabet',
    category: 'kitchen',
    alphabet: buildAlphabet('K')
});

assert.strictEqual(ctx.CustomSpellingAlphabets.loadAll().length, 2, 'Should persist multiple alphabets');

const customKeys = Object.keys(ctx.window.transforms).filter((key) => key.indexOf('custom_spelling_') === 0);
assert.strictEqual(customKeys.length, 2, 'Each saved alphabet should register as its own transform');

const names = customKeys.map((key) => ctx.window.transforms[key].name).sort();
assert.deepStrictEqual(names, [
    'Kitchen Spelling Alphabet',
    'Nautical Spelling Alphabet'
]);

customKeys.forEach((key) => {
    const transform = ctx.window.transforms[key];
    assert.strictEqual(transform.category, 'custom_spelling');
    assert.ok(transform.customSpellingId, 'Custom spelling transforms should expose customSpellingId');
    assert.strictEqual(typeof transform.func, 'function');
});

ctx.CustomSpellingAlphabets.deleteMapping(first.id);
assert.strictEqual(ctx.CustomSpellingAlphabets.loadAll().length, 1);
const remainingKeys = Object.keys(ctx.window.transforms).filter((key) => key.indexOf('custom_spelling_') === 0);
assert.strictEqual(remainingKeys.length, 1);
assert.strictEqual(ctx.window.transforms[remainingKeys[0]].name, 'Kitchen Spelling Alphabet');

console.log('Custom spelling transform tests passed');
