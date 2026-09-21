// leetspeak transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Leetspeak',
    priority: 40,
    map: {
            'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7', 'l': '1',
            'A': '4', 'E': '3', 'I': '1', 'O': '0', 'S': '5', 'T': '7', 'L': '1'
        },
        func: function(text) {
            return [...text].map(c => this.map[c] || c).join('');
        },
        preview: function(text) {
            if (!text) return '[double-struck]';
            return this.func(text.slice(0, 3)) + '...';
        },
        // Create reverse map for decoding
        reverseMap: function() {
            const revMap = {};
            for (const [key, value] of Object.entries(this.map)) {
                revMap[value] = key.toLowerCase();
            }
            return revMap;
        },
        reverse: function(text) {
            const revMap = this.reverseMap();
            return [...text].map(c => revMap[c] || c).join('');
        }

});