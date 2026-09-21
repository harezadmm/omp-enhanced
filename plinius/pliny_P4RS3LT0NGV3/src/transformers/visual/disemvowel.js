// disemvowel transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Disemvowel',
    priority: 40,
    func: function(text) {
            return text.replace(/[aeiouAEIOU]/g, '');
        },
        preview: function(text) {
            if (!text) return '[dsmvwl]';
            return this.func(text.slice(0, 12)) + (text.length > 12 ? '...' : '');
        }

});