/**
 * Factory for ICAO-style spelling alphabet transforms (built-in or user-saved).
 */
(function(global) {
    'use strict';

    var LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    var SAMPLE_TEXT = 'hello world';

    function emptyAlphabet() {
        var alphabet = {};
        LETTERS.forEach(function(letter) {
            alphabet[letter] = '';
        });
        return alphabet;
    }

    function normalizeWord(word) {
        return word ? String(word).toUpperCase().replace(/[^A-Z0-9]/g, '') : '';
    }

    function countFilled(alphabet) {
        return LETTERS.filter(function(letter) {
            return !!alphabet[letter];
        }).length;
    }

    function mergeAlphabet(target, source) {
        LETTERS.forEach(function(letter) {
            var word = normalizeWord(source && source[letter]);
            if (word && !target[letter]) {
                target[letter] = word;
            }
        });
        return target;
    }

    function tryParseJsonObject(text) {
        var start = text.indexOf('{');
        var end = text.lastIndexOf('}');
        if (start === -1 || end <= start) {
            return null;
        }

        var candidates = [
            text.slice(start, end + 1),
            text.slice(start, end + 1).replace(/,\s*([}\]])/g, '$1')
        ];

        for (var i = 0; i < candidates.length; i++) {
            try {
                var parsed = JSON.parse(candidates[i]);
                if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                    return parsed;
                }
            } catch (e) {
                // try next candidate
            }
        }
        return null;
    }

    function extractPairsFromText(text) {
        var alphabet = emptyAlphabet();
        var patterns = [
            /"([A-Z])"\s*:\s*"([^"]+)"/g,
            /'([A-Z])'\s*:\s*'([^']+)'/g,
            /(?:^|[\n,{])\s*([A-Z])\s*[:=\-–]\s*"?([A-Za-z0-9]+)"?/g,
            /(?:^|\n)\s*([A-Z])\s+[—–-]\s+([A-Za-z0-9]+)/g
        ];

        patterns.forEach(function(pattern) {
            var match;
            while ((match = pattern.exec(text)) !== null) {
                var letter = match[1].toUpperCase();
                var word = normalizeWord(match[2]);
                if (LETTERS.indexOf(letter) !== -1 && word && !alphabet[letter]) {
                    alphabet[letter] = word;
                }
            }
        });

        return alphabet;
    }

    function parseAlphabetResponse(rawText) {
        var text = String(rawText || '').trim();
        if (!text) {
            throw new Error('Empty response from model.');
        }

        var fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
        if (fenced) {
            text = fenced[1].trim();
        }

        var merged = emptyAlphabet();
        var jsonObject = tryParseJsonObject(text);
        if (jsonObject) {
            mergeAlphabet(merged, normalizeAlphabet(jsonObject));
        }
        mergeAlphabet(merged, extractPairsFromText(text));

        var filledCount = countFilled(merged);
        if (filledCount === 0) {
            throw new Error('Model did not return JSON. Try again or fill letters manually.');
        }

        return {
            alphabet: merged,
            filledCount: filledCount,
            partial: filledCount < LETTERS.length
        };
    }

    function extractMessageContent(message) {
        if (!message) {
            return '';
        }
        var content = message.content;
        if (typeof content === 'string') {
            return content;
        }
        if (Array.isArray(content)) {
            return content.map(function(part) {
                if (typeof part === 'string') {
                    return part;
                }
                if (part && typeof part.text === 'string') {
                    return part.text;
                }
                return '';
            }).join('\n');
        }
        return content == null ? '' : String(content);
    }

    function buildAlphabetPrompts(category) {
        var theme = String(category || '').trim() || 'general';

        var system = [
            'You create NATO/ICAO-style spelling alphabets.',
            '',
            'Task: given a theme, produce one codeword per letter A–Z for spelling text aloud.',
            '',
            'Hard rules:',
            '- Output ONLY valid JSON — one object, no markdown, no code fences, no explanation.',
            '- Exactly 26 keys: "A" through "Z" (uppercase).',
            '- Each value is ONE uppercase English word with no spaces.',
            '- Every word MUST start with its key letter (A→ANCHOR, not A→HARBOR).',
            '- All 26 words must be unique.',
            '- Words must fit the theme and be easy to say aloud (prefer 1–3 syllables).',
            '- Avoid obscure jargon unless the theme requires it.',
            '',
            'Letter tips:',
            '- Q, X, and Z are hard: pick the best theme word that starts with that letter.',
            '- For X, XRAY or a theme word starting with X is fine.',
            '',
            'Example theme "nautical" (format only — use different words for other themes):',
            '{"A":"ANCHOR","B":"BUOY","C":"CORAL","D":"DOCK","E":"EDDY","F":"FOG","G":"GALLEY","H":"HARBOR","I":"ISLAND","J":"JIB","K":"KNOT","L":"LAGOON","M":"MAST","N":"NAVY","O":"OCEAN","P":"PORT","Q":"QUAY","R":"REEF","S":"SAIL","T":"TIDE","U":"UNDERTOW","V":"VOYAGE","W":"WHARF","X":"XRAY","Y":"YACHT","Z":"ZEPHYR"}'
        ].join('\n');

        var user = [
            'Theme: "' + theme + '"',
            '',
            'Return the complete A–Z JSON object now.',
            'Double-check: 26 keys, each word starts with its letter, all unique, theme-appropriate.'
        ].join('\n');

        return { system: system, user: user };
    }

    function buildAlphabetPrompt(category) {
        return buildAlphabetPrompts(category).user;
    }

    function normalizeAlphabet(alphabet) {
        var normalized = emptyAlphabet();
        if (!alphabet || typeof alphabet !== 'object') {
            return normalized;
        }
        LETTERS.forEach(function(letter) {
            var word = alphabet[letter] || alphabet[letter.toLowerCase()];
            normalized[letter] = normalizeWord(word);
        });
        return normalized;
    }

    function createSpellingAlphabetTransform(config) {
        var alphabet = normalizeAlphabet(config.alphabet);
        var name = config.name || 'Spelling Alphabet';
        var category = config.category || 'custom_spelling';
        var priority = typeof config.priority === 'number' ? config.priority : 200;
        var customId = config.id || null;

        var transform = {
            name: name,
            priority: priority,
            category: category,
            alphabet: alphabet,
            customSpellingId: customId,
            func: function(text) {
                var cleaned = text.toUpperCase().replace(/[^A-Z]/g, '');
                if (cleaned.length === 0) {
                    return text;
                }

                var result = '';
                for (var i = 0; i < cleaned.length; i++) {
                    var char = cleaned[i];
                    if (this.alphabet[char]) {
                        result += this.alphabet[char] + ' ';
                    } else {
                        result += char + ' ';
                    }
                }
                return result.trim();
            },
            reverse: function(text) {
                var reverseMap = {};
                for (var letter in this.alphabet) {
                    if (Object.prototype.hasOwnProperty.call(this.alphabet, letter)) {
                        reverseMap[this.alphabet[letter].toUpperCase()] = letter;
                    }
                }

                var words = text.toUpperCase().split(/\s+/);
                var decoded = '';
                for (var j = 0; j < words.length; j++) {
                    var word = words[j];
                    if (reverseMap[word]) {
                        decoded += reverseMap[word];
                    } else if (word.length === 1 && /[A-Z]/.test(word)) {
                        decoded += word;
                    }
                }
                return decoded;
            },
            preview: function(text) {
                if (!text) {
                    return '[spelling]';
                }
                return this.func(text.slice(0, 3));
            },
            detector: function(text) {
                var words = Object.values(this.alphabet).filter(Boolean);
                if (words.length < 2) {
                    return false;
                }
                var upper = text.toUpperCase();
                var matches = words.filter(function(word) {
                    return upper.includes(word);
                });
                return matches.length >= 2;
            }
        };

        return transform;
    }

    global.SpellingAlphabetTransform = {
        LETTERS: LETTERS,
        SAMPLE_TEXT: SAMPLE_TEXT,
        emptyAlphabet: emptyAlphabet,
        normalizeAlphabet: normalizeAlphabet,
        parseAlphabetResponse: parseAlphabetResponse,
        extractMessageContent: extractMessageContent,
        buildAlphabetPrompts: buildAlphabetPrompts,
        buildAlphabetPrompt: buildAlphabetPrompt,
        create: createSpellingAlphabetTransform
    };
})(typeof window !== 'undefined' ? window : globalThis);
