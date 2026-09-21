// rot47 transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'ROT47',
    priority: 60,
    func: function(text) {
            return [...text].map(c => {
                const code = c.charCodeAt(0);
                // ROT47 operates on ASCII 33-126 (94 chars), rotating by 47 (half of 94)
                // This makes ROT47 self-inverse (encoding = decoding)
                if (code >= 33 && code <= 126) {
                    return String.fromCharCode(33 + ((code - 33 + 47) % 94));
                }
                return c;
            }).join('');
        },
        preview: function(text) {
            return this.func(text);
        },
        reverse: function(text) {
            // ROT47 is self-inverse, so reverse is the same as forward
            return this.func(text);
        }

});