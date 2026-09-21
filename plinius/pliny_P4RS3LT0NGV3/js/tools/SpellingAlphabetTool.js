/**
 * Spelling Alphabet Tool — create custom ICAO-style alphabets (OpenRouter or manual).
 */
class SpellingAlphabetTool extends Tool {
    constructor() {
        super({
            id: 'spellingalphabet',
            name: 'Spelling',
            icon: 'fa-spell-check',
            title: 'Custom spelling alphabets',
            order: 8
        });
    }

    getVueData() {
        return {
            saView: 'list',
            saAlphabets: [],
            saEditingId: null,
            saName: '',
            saCategory: '',
            saAlphabet: SpellingAlphabetTransform.emptyAlphabet(),
            saLoading: false,
            saError: '',
            saModel: localStorage.getItem('sa-model') || 'openrouter/free',
            saLetters: SpellingAlphabetTransform.LETTERS
        };
    }

    getVueMethods() {
        return {
            saGetApiKey: function() {
                var key = localStorage.getItem('openrouter-api-key') ||
                    localStorage.getItem('plinyos-api-key') ||
                    localStorage.getItem('openrouter_api_key') || '';
                if (!key && this.openrouterApiKey) {
                    key = this.openrouterApiKey;
                    localStorage.setItem('openrouter-api-key', key.trim());
                }
                return key.trim();
            },
            saHasApiKey: function() {
                return !!this.saGetApiKey();
            },
            saLoadAlphabets: function() {
                this.saAlphabets = CustomSpellingAlphabets.loadAll();
            },
            saStartNew: function() {
                this.saView = 'edit';
                this.saEditingId = null;
                this.saName = '';
                this.saCategory = '';
                this.saAlphabet = SpellingAlphabetTransform.emptyAlphabet();
                this.saError = '';
            },
            saEditAlphabet: function(entry) {
                this.saView = 'edit';
                this.saEditingId = entry.id;
                this.saName = entry.name;
                this.saCategory = entry.category || '';
                this.saAlphabet = Object.assign(
                    SpellingAlphabetTransform.emptyAlphabet(),
                    SpellingAlphabetTransform.normalizeAlphabet(entry.alphabet)
                );
                this.saError = '';
            },
            saCancelEdit: function() {
                this.saView = 'list';
                this.saEditingId = null;
                this.saError = '';
            },
            saDeleteAlphabet: function(entry) {
                if (!entry || !entry.id) {
                    return;
                }
                if (!window.confirm('Delete "' + entry.name + '"? This removes it from the Transforms page too.')) {
                    return;
                }
                CustomSpellingAlphabets.deleteMapping(entry.id);
                this.saLoadAlphabets();
                this.saRefreshTransforms();
                if (typeof this.showNotification === 'function') {
                    this.showNotification('Spelling alphabet deleted', 'success', 'fas fa-trash');
                }
            },
            saSuggestName: function() {
                var category = String(this.saCategory || '').trim();
                if (!category) {
                    return 'Custom Spelling Alphabet';
                }
                return category.replace(/\b\w/g, function(c) { return c.toUpperCase(); }) + ' Spelling Alphabet';
            },
            saParseAlphabetJson: function(rawText) {
                return SpellingAlphabetTransform.parseAlphabetResponse(rawText);
            },
            saBuildGenerationRequest: function(category) {
                var prompts = SpellingAlphabetTransform.buildAlphabetPrompts(category);
                var body = {
                    model: this.saModel,
                    temperature: 0.2,
                    max_tokens: 1200,
                    messages: [
                        { role: 'system', content: prompts.system },
                        { role: 'user', content: prompts.user }
                    ]
                };

                if (this.saModel !== 'openrouter/free') {
                    body.response_format = { type: 'json_object' };
                }

                return body;
            },
            saGenerateAlphabet: function() {
                var category = String(this.saCategory || '').trim();
                if (!category) {
                    this.saError = 'Enter a category or theme first (e.g. nautical, cooking, astronomy).';
                    return;
                }

                var apiKey = this.saGetApiKey();
                if (!apiKey) {
                    this.saError = 'No OpenRouter API key. Add one in Advanced Settings, or fill in letters manually below.';
                    return;
                }

                this.saLoading = true;
                this.saError = '';

                var self = this;
                var requestBody = this.saBuildGenerationRequest(category);

                fetch('https://openrouter.ai/api/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json',
                        'HTTP-Referer': window.location.origin,
                        'X-Title': 'P4RS3LT0NGV3 Spelling Alphabet'
                    },
                    body: JSON.stringify(requestBody)
                })
                    .then(function(response) {
                        if (response.status === 401) {
                            throw new Error('Invalid API key. Check your OpenRouter key in Advanced Settings.');
                        }
                        if (response.status === 402) {
                            throw new Error('Insufficient credits on your OpenRouter account.');
                        }
                        if (response.status === 400 && requestBody.response_format) {
                            delete requestBody.response_format;
                            return fetch('https://openrouter.ai/api/v1/chat/completions', {
                                method: 'POST',
                                headers: {
                                    'Authorization': 'Bearer ' + apiKey,
                                    'Content-Type': 'application/json',
                                    'HTTP-Referer': window.location.origin,
                                    'X-Title': 'P4RS3LT0NGV3 Spelling Alphabet'
                                },
                                body: JSON.stringify(requestBody)
                            });
                        }
                        if (!response.ok) {
                            throw new Error('OpenRouter request failed (HTTP ' + response.status + ').');
                        }
                        return response;
                    })
                    .then(function(response) {
                        if (!response.ok) {
                            throw new Error('OpenRouter request failed (HTTP ' + response.status + ').');
                        }
                        return response.json();
                    })
                    .then(function(data) {
                        var message = data &&
                            data.choices &&
                            data.choices[0] &&
                            data.choices[0].message;
                        var content = SpellingAlphabetTransform.extractMessageContent(message);
                        var parsed = self.saParseAlphabetJson(content);
                        self.saAlphabet = parsed.alphabet;
                        if (!self.saName.trim()) {
                            self.saName = self.saSuggestName();
                        }
                        if (parsed.partial) {
                            self.saError = 'Parsed ' + parsed.filledCount + '/26 letters. Fill in the rest below.';
                        } else {
                            self.saError = '';
                        }
                        if (typeof self.showNotification === 'function') {
                            var note = parsed.partial
                                ? 'Partial alphabet generated — complete missing letters before saving'
                                : 'Alphabet generated — review and edit letters before saving';
                            self.showNotification(note, parsed.partial ? 'warning' : 'success', 'fas fa-wand-magic-sparkles');
                        }
                    })
                    .catch(function(err) {
                        self.saError = err.message || 'Failed to generate alphabet.';
                    })
                    .finally(function() {
                        self.saLoading = false;
                    });
            },
            saValidateAlphabet: function() {
                var name = String(this.saName || '').trim();
                if (!name) {
                    return 'Enter a name for this spelling alphabet.';
                }

                var duplicateName = (this.saAlphabets || []).some(function(entry) {
                    return entry.id !== this.saEditingId &&
                        String(entry.name || '').trim().toLowerCase() === name.toLowerCase();
                }, this);
                if (duplicateName) {
                    return 'Another spelling alphabet already uses this name. Choose a unique name.';
                }

                var missing = this.saLetters.filter(function(letter) {
                    return !String(this.saAlphabet[letter] || '').trim();
                }, this);
                if (missing.length) {
                    return 'Fill in all 26 letters. Missing: ' + missing.join(', ');
                }

                var seen = {};
                for (var i = 0; i < this.saLetters.length; i++) {
                    var letter = this.saLetters[i];
                    var word = String(this.saAlphabet[letter] || '').toUpperCase();
                    if (seen[word]) {
                        return 'Duplicate word "' + word + '" for letters ' + seen[word] + ' and ' + letter + '.';
                    }
                    seen[word] = letter;
                }

                return '';
            },
            saSaveAlphabet: function() {
                var validationError = this.saValidateAlphabet();
                if (validationError) {
                    this.saError = validationError;
                    return;
                }

                var saved = CustomSpellingAlphabets.saveMapping({
                    id: this.saEditingId,
                    name: this.saName.trim(),
                    category: this.saCategory.trim(),
                    alphabet: this.saAlphabet
                });

                localStorage.setItem('sa-model', this.saModel);
                this.saLoadAlphabets();
                this.saRefreshTransforms();
                this.saView = 'list';
                this.saEditingId = saved.id;
                this.saError = '';

                if (typeof this.showNotification === 'function') {
                    this.showNotification('Saved — find it on the Transforms page under custom_spelling', 'success', 'fas fa-check');
                }
            },
            saRefreshTransforms: function() {
                if (typeof this.refreshCustomSpellingTransforms === 'function') {
                    this.refreshCustomSpellingTransforms();
                }
            },
            saPreviewSample: function() {
                var sample = SpellingAlphabetTransform.SAMPLE_TEXT;
                if (!window.SpellingAlphabetTransform) {
                    return '';
                }
                var temp = SpellingAlphabetTransform.create({
                    name: this.saName || 'Preview',
                    alphabet: this.saAlphabet
                });
                return temp.func(sample);
            },
            saSampleForEntry: function(entry) {
                if (!entry || !window.SpellingAlphabetTransform) {
                    return '';
                }
                var temp = SpellingAlphabetTransform.create({
                    name: entry.name,
                    alphabet: entry.alphabet
                });
                return temp.func(SpellingAlphabetTransform.SAMPLE_TEXT);
            },
            saFilledLetterCount: function() {
                return this.saLetters.filter(function(letter) {
                    return String(this.saAlphabet[letter] || '').trim().length > 0;
                }, this).length;
            }
        };
    }

    getVueLifecycle() {
        return {
            mounted: function() {
                this.saLoadAlphabets();
            }
        };
    }

    onActivate(vueInstance) {
        vueInstance.saLoadAlphabets();
        if (typeof vueInstance.refreshCustomSpellingTransforms === 'function') {
            vueInstance.refreshCustomSpellingTransforms();
        }
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SpellingAlphabetTool;
} else {
    window.SpellingAlphabetTool = SpellingAlphabetTool;
}
