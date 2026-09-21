// invisible-text transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Invisible Text',
    priority: 100, // High confidence - uses exclusive Unicode Private Use Area (U+E0000-U+E00FF)
    func: function(text) {
            if (!text) return '';
            const bytes = new TextEncoder().encode(text);
            return Array.from(bytes)
                .map(byte => String.fromCodePoint(0xE0000 + byte))
                .join('');
        },
        preview: function(text) {
            return '[invisible]';
        },
        reverse: function(text) {
            if (!text) return '';
            const matches = [...text.matchAll(/[\u{E0000}-\u{E00FF}]/gu)];
            if (!matches.length) return '';
            
            // Convert invisible characters back to bytes
            const bytes = new Uint8Array(
                matches.map(match => match[0].codePointAt(0) - 0xE0000)
            );
            
            // Use TextDecoder to properly handle UTF-8 encoded bytes (including emoji)
            return new TextDecoder().decode(bytes);
        },
        // Detector: Check for at least one invisible Unicode character
        detector: function(text) {
            // Invisible text uses Unicode Private Use Area (U+E0000-U+E00FF for full byte range)
            const invisibleMatches = text.match(/[\u{E0000}-\u{E00FF}]/gu);
            // Return true if at least one invisible character is found
            return invisibleMatches && invisibleMatches.length > 0;
        }

});