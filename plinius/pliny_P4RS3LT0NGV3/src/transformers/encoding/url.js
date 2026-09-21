// url transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({
    name: 'URL Encode',
    priority: 40,
    // Detector: Look for %XX pattern (URL encoding)
    detector: function(text) {
        return text.includes('%') && /%[0-9A-Fa-f]{2}/.test(text);
    },
    
    func: function(text) {
            try {
                return encodeURIComponent(text);
            } catch (e) {
                // Catch malformed Unicode or unpaired surrogates
                return '[Invalid input]';
            }
        },
        preview: function(text) {
            return this.func(text);
        },
        reverse: function(text) {
            try {
                return decodeURIComponent(text);
            } catch (e) {
                return text;
            }
        }

});