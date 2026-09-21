// reverse-words transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Reverse Words',
    priority: 40,
    func: function(text) {
            return text.split(/(\s+)/).reverse().join('');
        },
        preview: function(text) {
            if (!text) return '[rev words]';
            // Take last 2-3 words and reverse them to show the effect
            const words = text.split(/\s+/);
            const lastWords = words.slice(-3).join(' ');
            return this.func(lastWords) + '...';
        },
        reverse: function(text) {
            // Reversing words twice restores
            return this.func(text);
        }

});