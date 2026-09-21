window.EmojiUtils = {
    splitEmojis(text) {
        if (Intl.Segmenter) {
            const segmenter = new Intl.Segmenter('en', { granularity: 'grapheme' });
            return Array.from(segmenter.segment(text), ({ segment }) => segment);
        }
        return Array.from(text);
    },
    
    joinEmojis(emojis) {
        return emojis.join('');
    },
    
    getAllEmojis() {
        if (!window.emojiData || typeof window.emojiData !== 'object') {
            return [];
        }
        return Object.keys(window.emojiData).filter(key => {
            const value = window.emojiData[key];
            return typeof value === 'object' && value !== null && 'official' in value;
        });
    },
    
    async getCompatibleEmojis(progressCallback) {
        const allEmojis = this.getAllEmojis();
        
        if (window.emojiCompatibility && typeof window.emojiCompatibility.getCompatibleEmojis === 'function') {
            return await window.emojiCompatibility.getCompatibleEmojis(allEmojis, progressCallback);
        }
        return allEmojis;
    }
};

