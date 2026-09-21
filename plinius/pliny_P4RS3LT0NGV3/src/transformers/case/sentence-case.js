// sentence-case transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Sentence Case',
    priority: 150,  // Higher priority to detect before Base64
    func: function(text) {
            if (!text) return '';
            const lower = text.toLowerCase();
            return lower.charAt(0).toUpperCase() + lower.slice(1);
        },
        preview: function(text) {
            if (!text) return '[Sentence]';
            return this.func(text.slice(0, 12)) + (text.length > 12 ? '...' : '');
        }

});