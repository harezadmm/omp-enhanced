// title-case transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Title Case',
    priority: 150,  // Higher priority to detect before Base64
    func: function(text) {
            return text.replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
        },
        preview: function(text) {
            if (!text) return '[Title Case]';
            return this.func(text.slice(0, 12)) + (text.length > 12 ? '...' : '');
        }

});