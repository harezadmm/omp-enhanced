/**
 * Fetch, cache, and normalize OpenRouter model lists for UI dropdowns.
 */
window.OpenRouterModels = {
    CACHE_KEY: 'openrouter-models-cache-v1',
    CACHE_TTL_MS: 60 * 60 * 1000,

    ENABLED_STORAGE_KEY: 'openrouter-models-disabled-v1',

    VIRTUAL: [
        {
            id: 'openrouter/free',
            name: 'Free router',
            summary: 'Zero cost — random free model matched to your request',
            provider: 'OpenRouter',
            virtual: true,
            routerKind: 'free'
        },
        {
            id: 'openrouter/auto',
            name: 'Auto router',
            summary: 'Smart routing — billed at whichever model is picked',
            provider: 'OpenRouter',
            virtual: true,
            routerKind: 'auto'
        }
    ],

    getApiKey: function() {
        try {
            return (
                localStorage.getItem('openrouter-api-key') ||
                localStorage.getItem('plinyos-api-key') ||
                localStorage.getItem('openrouter_api_key') ||
                ''
            ).trim();
        } catch (e) {
            return '';
        }
    },

    getStaticFallback: function() {
        if (window.OPENROUTER_MODELS_FALLBACK && window.OPENROUTER_MODELS_FALLBACK.length) {
            return window.OPENROUTER_MODELS_FALLBACK.slice();
        }
        if (window.OPENROUTER_MODELS && window.OPENROUTER_MODELS.length) {
            return window.OPENROUTER_MODELS.slice();
        }
        return this.VIRTUAL.slice();
    },

    isFreePricing: function(pricing) {
        if (!pricing) return false;
        return String(pricing.prompt) === '0' && String(pricing.completion) === '0';
    },

    normalize: function(raw) {
        var id = raw && raw.id ? raw.id : '';
        var provider = id.indexOf('/') !== -1 ? id.split('/')[0] : '';
        return {
            id: id,
            name: (raw && raw.name) || id,
            provider: provider,
            free: this.isFreePricing(raw && raw.pricing),
            contextLength: raw && raw.context_length ? raw.context_length : null,
            pricing: raw && raw.pricing ? raw.pricing : null
        };
    },

    formatLabel: function(model) {
        if (!model) return '';
        if (model.virtual) {
            return model.name + ' — ' + (model.summary || model.provider);
        }
        var label = model.name || model.id;
        if (model.provider) {
            label += ' (' + model.provider + ')';
        }
        if (model.free) {
            label += ' · free';
        }
        return label;
    },

    getRouterHint: function(modelId) {
        var match = this.VIRTUAL.find(function(model) {
            return model.id === modelId;
        });
        return match ? match.summary : '';
    },

    loadDisabledIds: function() {
        try {
            var raw = localStorage.getItem(this.ENABLED_STORAGE_KEY);
            if (!raw) return [];
            var parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            return [];
        }
    },

    saveDisabledIds: function(ids) {
        try {
            localStorage.setItem(this.ENABLED_STORAGE_KEY, JSON.stringify(ids || []));
        } catch (e) {
            console.warn('Failed to save OpenRouter model preferences:', e);
        }
    },

    isModelEnabled: function(modelId, disabledIds) {
        if (!modelId) return true;
        disabledIds = disabledIds || [];
        return disabledIds.indexOf(modelId) === -1;
    },

    filterForDropdown: function(catalog, disabledIds, pinnedIds) {
        catalog = catalog || [];
        disabledIds = disabledIds || [];
        pinnedIds = pinnedIds || [];

        return catalog.filter(function(model) {
            if (!model || !model.id) return false;
            if (pinnedIds.indexOf(model.id) !== -1) return true;
            return disabledIds.indexOf(model.id) === -1;
        });
    },

    getPinnedModelIds: function(context) {
        context = context || {};
        var ids = [];
        ['pcModel', 'acModel', 'saModel', 'translateModel'].forEach(function(field) {
            if (context[field]) ids.push(context[field]);
        });
        return ids;
    },

    loadCache: function(apiKey) {
        try {
            var raw = localStorage.getItem(this.CACHE_KEY);
            if (!raw) return null;
            var parsed = JSON.parse(raw);
            if (parsed.apiKey !== (apiKey || '')) return null;
            if (Date.now() - parsed.fetchedAt > this.CACHE_TTL_MS) return null;
            return Array.isArray(parsed.models) ? parsed.models : null;
        } catch (e) {
            return null;
        }
    },

    saveCache: function(apiKey, models) {
        try {
            localStorage.setItem(this.CACHE_KEY, JSON.stringify({
                apiKey: apiKey || '',
                fetchedAt: Date.now(),
                models: models
            }));
        } catch (e) {
            console.warn('Failed to cache OpenRouter models:', e);
        }
    },

    mergeWithVirtual: function(models) {
        var seen = {};
        var merged = [];

        this.VIRTUAL.forEach(function(model) {
            seen[model.id] = true;
            merged.push(Object.assign({}, model));
        });

        (models || []).forEach(function(model) {
            if (!model || !model.id || seen[model.id]) return;
            seen[model.id] = true;
            merged.push(model);
        });

        return merged;
    },

    fetch: async function(apiKey, options) {
        options = options || {};
        var key = (apiKey || '').trim();

        if (!options.force) {
            var cached = this.loadCache(key);
            if (cached && cached.length) {
                return cached;
            }
        }

        var url = key
            ? 'https://openrouter.ai/api/v1/models/user'
            : 'https://openrouter.ai/api/v1/models?sort=most-popular';

        var headers = {};
        if (key) {
            headers.Authorization = 'Bearer ' + key;
        }

        var resp = await fetch(url, { headers: headers });
        if (!resp.ok) {
            var error = new Error('Failed to load models (HTTP ' + resp.status + ')');
            error.status = resp.status;
            throw error;
        }

        var json = await resp.json();
        var models = (json.data || []).map(this.normalize.bind(this));
        models = this.mergeWithVirtual(models);
        this.saveCache(key, models);
        return models;
    },

    fetchKeyInfo: async function(apiKey) {
        var key = (apiKey || '').trim();
        if (!key) return null;

        try {
            var resp = await fetch('https://openrouter.ai/api/v1/key', {
                headers: { Authorization: 'Bearer ' + key }
            });
            if (!resp.ok) return null;
            var json = await resp.json();
            return json.data || null;
        } catch (e) {
            return null;
        }
    },

    ensureValidSelection: function(currentId, models, preferredId) {
        if (!models || !models.length) return currentId || preferredId || '';
        if (currentId && models.some(function(model) { return model.id === currentId; })) {
            return currentId;
        }
        if (preferredId && models.some(function(model) { return model.id === preferredId; })) {
            return preferredId;
        }
        return models[0].id;
    }
};
