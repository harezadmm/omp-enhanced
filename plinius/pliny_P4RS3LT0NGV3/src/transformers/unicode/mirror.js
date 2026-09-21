// mirror transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Mirror Text',
    priority: 85,
    func: function(text) {
            return [...text].reverse().join('');
        },
        preview: function(text) {
            if (!text) return '[math]';
            return this.func(text.slice(0, 3)) + '...';
        },
        reverse: function(text) {
            return this.func(text); // Mirror is its own inverse
        }

});