// base64 transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({
    name: 'Base64',
    priority: 270,
    // Detector: Only Base64 characters (A-Z, a-z, 0-9, +, /, =)
    detector: function(text) {
        const cleaned = text.trim().replace(/\s/g, '');
        return cleaned.length >= 4 && /^[A-Za-z0-9+\/=]+$/.test(cleaned);
    },
    
    func: function(text) {
            try {
                // Properly encode UTF-8 text (including emojis) to Base64
                const encoder = new TextEncoder();
                const bytes = encoder.encode(text);
                let binaryString = '';
                for (let i = 0; i < bytes.length; i++) {
                    binaryString += String.fromCharCode(bytes[i]);
                }
                return btoa(binaryString);
            } catch (e) {
                return '[Invalid input]';
            }
        },
        preview: function(text) {
            if (!text) return '[base64]';
            try {
                const full = this.func(text);
                return full.substring(0, 12) + (full.length > 12 ? '...' : '');
            } catch (e) {
                return '[Invalid input]';
            }
        },
        reverse: function(text) {
            try {
                // Properly decode Base64 to UTF-8 text (including emojis)
                const binaryString = atob(text);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                const decoder = new TextDecoder('utf-8');
                return decoder.decode(bytes);
            } catch (e) {
                return text;
            }
        }

});