/**
 * Persist user-created spelling alphabets in localStorage and register them on window.transforms.
 */
(function(global) {
    'use strict';

    var STORAGE_KEY = 'customSpellingAlphabets';
    var TRANSFORM_KEY_PREFIX = 'custom_spelling_';

    function createId() {
        if (global.crypto && typeof global.crypto.randomUUID === 'function') {
            return global.crypto.randomUUID();
        }
        return 'sa_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 10);
    }

    function loadAll() {
        try {
            var raw = global.localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return [];
            }
            var parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) {
                return [];
            }
            return parsed.filter(function(entry) {
                return entry && entry.id && entry.name && entry.alphabet;
            });
        } catch (e) {
            console.warn('Failed to load custom spelling alphabets:', e);
            return [];
        }
    }

    function saveAll(entries) {
        global.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    }

    function transformKeyForId(id) {
        return TRANSFORM_KEY_PREFIX + id.replace(/[^a-zA-Z0-9_-]/g, '_');
    }

    function removeRegisteredCustomTransforms() {
        if (!global.transforms) {
            return;
        }
        Object.keys(global.transforms).forEach(function(key) {
            if (key.indexOf(TRANSFORM_KEY_PREFIX) === 0) {
                delete global.transforms[key];
            }
        });
    }

    function registerCustomTransforms() {
        if (!global.transforms) {
            global.transforms = {};
        }
        if (!global.SpellingAlphabetTransform) {
            console.warn('SpellingAlphabetTransform module missing; custom alphabets not registered.');
            return;
        }

        removeRegisteredCustomTransforms();

        loadAll().forEach(function(entry) {
            var key = transformKeyForId(entry.id);
            global.transforms[key] = global.SpellingAlphabetTransform.create({
                id: entry.id,
                name: entry.name,
                category: 'custom_spelling',
                alphabet: entry.alphabet,
                priority: 150
            });
        });
    }

    function syncCustomSpellingAlphabets() {
        registerCustomTransforms();
    }

    function saveMapping(mapping) {
        var entries = loadAll();
        var now = Date.now();
        var normalizedAlphabet = global.SpellingAlphabetTransform
            ? global.SpellingAlphabetTransform.normalizeAlphabet(mapping.alphabet)
            : mapping.alphabet;
        var payload = {
            id: mapping.id || createId(),
            name: String(mapping.name || '').trim(),
            category: String(mapping.category || '').trim(),
            alphabet: normalizedAlphabet,
            createdAt: mapping.createdAt || now,
            updatedAt: now
        };

        var index = entries.findIndex(function(entry) {
            return entry.id === payload.id;
        });
        if (index >= 0) {
            payload.createdAt = entries[index].createdAt || payload.createdAt;
            entries[index] = payload;
        } else {
            entries.push(payload);
        }

        saveAll(entries);
        syncCustomSpellingAlphabets();
        return payload;
    }

    function deleteMapping(id) {
        var entries = loadAll().filter(function(entry) {
            return entry.id !== id;
        });
        saveAll(entries);
        syncCustomSpellingAlphabets();
    }

    function getById(id) {
        return loadAll().find(function(entry) {
            return entry.id === id;
        }) || null;
    }

    global.CustomSpellingAlphabets = {
        STORAGE_KEY: STORAGE_KEY,
        loadAll: loadAll,
        saveAll: saveAll,
        saveMapping: saveMapping,
        deleteMapping: deleteMapping,
        getById: getById,
        syncCustomSpellingAlphabets: syncCustomSpellingAlphabets
    };

    global.syncCustomSpellingAlphabets = syncCustomSpellingAlphabets;

    syncCustomSpellingAlphabets();
})(typeof window !== 'undefined' ? window : globalThis);
