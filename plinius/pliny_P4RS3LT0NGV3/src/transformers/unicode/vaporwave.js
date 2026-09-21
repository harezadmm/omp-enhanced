// vaporwave transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Vaporwave',
    priority: 85,
    func: function(text) {
            return [...text].join(' ');
        },
        preview: function(text) {
            if (!text) return '[vaporwave]';
            return [...text.slice(0, 3)].join(' ') + '...';
        },
        reverse: function(text) {
            // Remove single spaces between characters, but preserve word boundaries (double+ spaces)
            // Replace double spaces with a marker, remove single spaces, restore markers
            return text.replace(/  +/g, '\x00').replace(/ /g, '').replace(/\x00/g, ' ');
        }

});