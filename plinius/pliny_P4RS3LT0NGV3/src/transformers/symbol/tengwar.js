// tengwar transform
import BaseTransformer from '../BaseTransformer.js';

export default new BaseTransformer({

        name: 'Tengwar Script',
    priority: 100,
    map: {
            'a': 'ᚪ', 'b': 'ᛒ', 'c': 'ᛣ', 'd': 'ᛞ', 'e': 'ᛖ', 'f': 'ᚠ', 'g': 'ᚷ', 'h': 'ᚺ', 'i': 'ᛁ',
            'j': 'ᛃ', 'k': 'ᛣ', 'l': 'ᛚ', 'm': 'ᛗ', 'n': 'ᚾ', 'o': 'ᚩ', 'p': 'ᛈ', 'q': 'ᛩ', 'r': 'ᚱ',
            's': 'ᛋ', 't': 'ᛏ', 'u': 'ᚢ', 'v': 'ᚡ', 'w': 'ᚹ', 'x': 'ᛉ', 'y': 'ᚣ', 'z': 'ᛉ',
            'A': 'ᚪ', 'B': 'ᛒ', 'C': 'ᛣ', 'D': 'ᛞ', 'E': 'ᛖ', 'F': 'ᚠ', 'G': 'ᚷ', 'H': 'ᚺ', 'I': 'ᛁ',
            'J': 'ᛃ', 'K': 'ᛣ', 'L': 'ᛚ', 'M': 'ᛗ', 'N': 'ᚾ', 'O': 'ᚩ', 'P': 'ᛈ', 'Q': 'ᛩ', 'R': 'ᚱ',
            'S': 'ᛋ', 'T': 'ᛏ', 'U': 'ᚢ', 'V': 'ᚡ', 'W': 'ᚹ', 'X': 'ᛉ', 'Y': 'ᚣ', 'Z': 'ᛉ'
        },
        func: function(text) {
            return [...text.toLowerCase()].map(c => this.map[c] || c).join('');
        },
        reverse: function(text) {
            const revMap = {};
            for (const [key, value] of Object.entries(this.map)) {
                revMap[value] = key;
            }
            return [...text].map(c => revMap[c] || c).join('');
        },
        // Detector: Check for Tengwar Script characters
        detector: function(text) {
            // Tengwar has unique characters like ᚪ, ᛣ, ᚩ, ᛩ, ᚣ
            return /[ᚪᛣᚩᛩᚣᛒᛞᛖᚠᚷᚺᛁᛃᛚᛗᚾᛈᚱᛋᛏᚢᚡᚹᛉ]/.test(text);
        }

});