// html transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({
    name: 'HTML Entities',
    priority: 40,
    // Detector: Look for &...; pattern (HTML entities)
    detector: function(text) {
        return text.includes('&') && text.includes(';') && /&[a-zA-Z0-9#]+;/.test(text);
    },
    
    func: function(text) {
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        },
        preview: function(text) {
            return this.func(text);
        },
        reverse: function(text) {
            return text
                .replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>')
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, '\'');
        }

});