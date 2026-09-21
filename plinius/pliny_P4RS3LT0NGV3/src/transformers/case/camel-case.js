// camel-case transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'camelCase',
    priority: 275,
    func: function(text) {
            const parts = text.split(/[^a-zA-Z0-9]+/).filter(Boolean);
            if (parts.length === 0) return '';
            const first = parts[0].toLowerCase();
            const rest = parts.slice(1).map(p => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()).join('');
            return first + rest;
        },
        preview: function(text) {
            if (!text) return '[camel]';
            return this.func(text);
        }

});