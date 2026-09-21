const __STEG_DEFAULTS__ = {
    bitZeroVS: '\ufe0e',
    bitOneVS: '\ufe0f',
    initialPresentation: 'emoji',
    trailingZW: '\u200B',
    interBitZW: null,
    interBitEvery: 1,
    bitOrder: 'msb'
};
let __stegOptions__ = Object.assign({}, __STEG_DEFAULTS__);
function setStegOptions(opts) {
    if (!opts) return;
    __stegOptions__ = Object.assign({}, __stegOptions__, opts);
}

function encodeForPreview(emoji, text) {
    return encodeEmoji(emoji, text);
}

function hasEmojiInText(text) {
    if (!text) return false;
    if (window.emojiData && typeof window.emojiData === 'object') {
        const emojiKeys = Object.keys(window.emojiData).filter(key => {
            const value = window.emojiData[key];
            return typeof value === 'object' && value !== null && 'official' in value;
        });
        if (emojiKeys.some(emoji => text.includes(emoji))) return true;
    }
    return /[\u{1F300}-\u{1F9FF}\u{1FA00}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F1E6}-\u{1F1FF}\u{2300}-\u{23FF}\u{2B50}\u{1F004}]/u.test(text);
}

function findEmojiMatch(text) {
    if (!text) return null;
    
    if (window.emojiData && typeof window.emojiData === 'object') {
        const emojiKeys = Object.keys(window.emojiData).filter(key => {
            const value = window.emojiData[key];
            return typeof value === 'object' && value !== null && 'official' in value;
        });
        
        if (emojiKeys.length > 0) {
            emojiKeys.sort((a, b) => b.length - a.length);
            const escapedEmojis = emojiKeys.map(emoji => 
                emoji.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            );
            const emojiRegex = new RegExp(`(${escapedEmojis.join('|')})`, 'u');
            const match = text.match(emojiRegex);
            if (match) return match;
        }
    }
    
    const flagEmojiRegex = /([\u{1F1E6}-\u{1F1FF}][\u{1F1E6}-\u{1F1FF}])/u;
    const singleEmojiRegex = /([\u{1F300}-\u{1F9FF}\u{1FA00}-\u{1FAFF}\u{2600}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}\u{1F004}])/u;
    
    return text.match(flagEmojiRegex) || text.match(singleEmojiRegex);
}

const carriers = [
    { 
        emoji: '🐍', 
        name: 'SNAKE', 
        desc: 'Classic Snake', 
        preview: function(text) {
            return encodeForPreview(this.emoji, text);
        }
    },
    { 
        emoji: '🐉', 
        name: 'DRAGON', 
        desc: 'Mystical Dragon', 
        preview: function(text) {
            return encodeForPreview(this.emoji, text);
        }
    },
    { 
        emoji: '🦎', 
        name: 'LIZARD', 
        desc: 'Sneaky Lizard', 
        preview: function(text) {
            return encodeForPreview(this.emoji, text);
        }
    },
    { 
        emoji: '🐊', 
        name: 'CROCODILE', 
        desc: 'Dangerous Croc', 
        preview: function(text) {
            return encodeForPreview(this.emoji, text);
        }
    }
];

function encodeEmoji(emoji, text) {
    if (!text) return emoji;
    
    let binary = '';
    try {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(text);
        const bitOrder = __stegOptions__.bitOrder || 'msb';
        binary = Array.from(bytes)
            .map(byte => {
                let byteStr = byte.toString(2).padStart(8, '0');
                if (bitOrder === 'lsb') {
                    byteStr = byteStr.split('').reverse().join('');
                }
                return byteStr;
            })
            .join('');
    } catch (e) {
        const bitOrder = __stegOptions__.bitOrder || 'msb';
        binary = Array.from(text)
            .map(c => {
                const codePoint = c.codePointAt(0);
                let bytes = [];
                if (codePoint <= 0x7F) {
                    bytes.push(codePoint);
                } else if (codePoint <= 0x7FF) {
                    bytes.push(0xC0 | (codePoint >> 6));
                    bytes.push(0x80 | (codePoint & 0x3F));
                } else if (codePoint <= 0xFFFF) {
                    bytes.push(0xE0 | (codePoint >> 12));
                    bytes.push(0x80 | ((codePoint >> 6) & 0x3F));
                    bytes.push(0x80 | (codePoint & 0x3F));
                } else {
                    bytes.push(0xF0 | (codePoint >> 18));
                    bytes.push(0x80 | ((codePoint >> 12) & 0x3F));
                    bytes.push(0x80 | ((codePoint >> 6) & 0x3F));
                    bytes.push(0x80 | (codePoint & 0x3F));
                }
                return bytes.map(byte => {
                    let byteStr = byte.toString(2).padStart(8, '0');
                    if (bitOrder === 'lsb') {
                        byteStr = byteStr.split('').reverse().join('');
                    }
                    return byteStr;
                }).join('');
            })
            .join('');
    }
    
    const vs0 = __stegOptions__.bitZeroVS || '\ufe0e';
    const vs1 = __stegOptions__.bitOneVS || '\ufe0f';
    
    let result = emoji;
    if (__stegOptions__.initialPresentation === 'emoji') result += '\ufe0f';
    else if (__stegOptions__.initialPresentation === 'text') result += '\ufe0e';
    
    for (let i=0;i<binary.length;i++) {
        const bit = binary[i];
        result += bit === '0' ? vs0 : vs1;
        if (__stegOptions__.interBitZW && i < binary.length-1 && ((i+1) % Math.max(1, __stegOptions__.interBitEvery)) === 0) {
            result += __stegOptions__.interBitZW;
        }
    }
    
    if (__stegOptions__.trailingZW) {
        result += __stegOptions__.trailingZW;
    }
    
    return result;
}

function decodeEmoji(text) {
    if (!text) return '';
    
    const emojiMatch = findEmojiMatch(text);
    if (!emojiMatch) return '';
    
    const emojiChar = emojiMatch[1];
    const emojiIndex = emojiMatch.index;
    
    const fromEmoji = text.substring(emojiIndex);
    const emojiCharEscaped = emojiChar.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`^${emojiCharEscaped}([\ufe0e\ufe0f\u200B\u200C\u200D\ufeff]+)`, 'u');
    const emojiData = fromEmoji.match(pattern);
    
    if (!emojiData || !emojiData[1]) return '';
    
    const rawSeq = emojiData[1];
    const matches = [...rawSeq.matchAll(/[\ufe0e\ufe0f]/g)];
    if (matches.length === 0) return '';
    
    const skip = (__stegOptions__.initialPresentation === 'none') ? 0 : 1;
    if (matches.length <= skip) return '';
    
    const zeroSel = __stegOptions__.bitZeroVS || '\ufe0e';
    const oneSel  = __stegOptions__.bitOneVS || '\ufe0f';
    let binary = matches.slice(skip).map(m => m[0] === zeroSel ? '0' : (m[0] === oneSel ? '1' : '')).join('');
    
    const validBinaryLength = Math.floor(binary.length / 8) * 8;
    const bytes = [];
    for (let i = 0; i < validBinaryLength; i += 8) {
        let byte = binary.slice(i, i + 8);
        if (__stegOptions__.bitOrder === 'lsb') {
            byte = byte.split('').reverse().join('');
        }
        if (byte.length === 8) {
            const byteValue = parseInt(byte, 2);
            bytes.push(byteValue);
        }
    }
    
    try {
        const decoder = new TextDecoder('utf-8', { fatal: false });
        const uint8Array = new Uint8Array(bytes);
        return decoder.decode(uint8Array);
    } catch (e) {
        let decoded = '';
        for (const byteValue of bytes) {
            if (byteValue >= 0 && byteValue <= 255) {
                decoded += String.fromCharCode(byteValue);
            }
        }
        try {
            return decodeURIComponent(escape(decoded));
        } catch (e2) {
            return decoded;
        }
    }
}

function encodeInvisible(text) {
    if (!text) return '';
    
    const bytes = new TextEncoder().encode(text);
    return Array.from(bytes)
        .map(byte => String.fromCodePoint(0xE0000 + byte))
        .join('');
}

function decodeInvisible(text) {
    if (!text) return '';
    
    const matches = [...text.matchAll(/[\uE0000-\uE007F]/g)];
    if (!matches.length) return '';
    
    const bytes = new Uint8Array(matches.length);
    for (let i = 0; i < matches.length; i++) {
        bytes[i] = matches[i][0].codePointAt(0) - 0xE0000;
    }
    
    try {
        const decoder = new TextDecoder('utf-8', {fatal: false});
        let decoded = decoder.decode(bytes);
        decoded = decoded.replace(/@+(?=[a-zA-Z0-9])/g, '');
        decoded = decoded.replace(/([a-zA-Z0-9])@+/g, '$1');
        decoded = decoded.replace(/@+/g, '');
        return decoded;
    } catch (e) {
        console.error('Error decoding invisible text:', e);
        let result = '';
        for (let i = 0; i < bytes.length; i++) {
            if (bytes[i] >= 32 && bytes[i] <= 126) {
                result += String.fromCharCode(bytes[i]);
            }
        }
        return result;
    }
}

window.steganography = {
    carriers,
    encodeEmoji,
    decodeEmoji,
    encodeInvisible,
    decodeInvisible,
    setStegOptions,
    hasEmojiInText
};
