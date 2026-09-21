window.EscapeParser = {
    parseEscapeSequence(str) {
        if (!str || typeof str !== 'string') {
            return str;
        }
        
        const escapeMap = {
            '\\u200B': '\u200B', // Zero Width Space
            '\\u200C': '\u200C', // Zero Width Non-Joiner
            '\\u200D': '\u200D', // Zero Width Joiner
            '\\u2060': '\u2060', // Word Joiner
            '\\uFE0E': '\uFE0E', // Variation Selector-15
            '\\uFE0F': '\uFE0F', // Variation Selector-16
            '\\n': '\n',
            '\\r': '\r',
            '\\t': '\t',
            '\\0': '\0',
            '\\\'': '\'',
            '\\"': '"',
            '\\\\': '\\'
        };
        
        if (escapeMap[str] !== undefined) {
            return escapeMap[str];
        }
        
        const unicodeMatch = str.match(/^\\u([0-9A-Fa-f]{4})$/);
        if (unicodeMatch) {
            return String.fromCharCode(parseInt(unicodeMatch[1], 16));
        }
        
        const hexMatch = str.match(/^\\x([0-9A-Fa-f]{2})$/);
        if (hexMatch) {
            return String.fromCharCode(parseInt(hexMatch[1], 16));
        }
        
        return str;
    }
};

