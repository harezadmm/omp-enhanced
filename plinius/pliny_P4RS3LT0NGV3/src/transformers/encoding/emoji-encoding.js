// Base256Emoji — multiformats/multibase (1 byte ↔ 1 emoji, lossless)
// https://github.com/multiformats/multibase/blob/master/rfcs/Base256Emoji.md
import BaseTransformer from '../BaseTransformer.js';

export default (function() {
    // Official 256-rune table (go-multibase / base256emoji crate)
    const ALPHABET = '🚀🪐☄🛰🌌🌑🌒🌓🌔🌕🌖🌗🌘🌍🌏🌎🐉☀💻🖥💾💿😂❤😍🤣😊🙏💕😭😘👍😅👏😁🔥🥰💔💖💙😢🤔😆🙄💪😉☺👌🤗💜😔😎😇🌹🤦🎉💞✌✨🤷😱😌🌸🙌😋💗💚😏💛🙂💓🤩😄😀🖤😃💯🙈👇🎶😒🤭❣😜💋👀😪😑💥🙋😞😩😡🤪👊🥳😥🤤👉💃😳✋😚😝😴🌟😬🙃🍀🌷😻😓⭐✅🥺🌈😈🤘💦✔😣🏃💐☹🎊💘😠☝😕🌺🎂🌻😐🖕💝🙊😹🗣💫💀👑🎵🤞😛🔴😤🌼😫⚽🤙☕🏆🤫👈😮🙆🍻🍃🐶💁😲🌿🧡🎁⚡🌞🎈❌✊👋😰🤨😶🤝🚶💰🍓💢🤟🙁🚨💨🤬✈🎀🍺🤓😙💟🌱😖👶🥴▶➡❓💎💸⬇😨🌚🦋😷🕺⚠🙅😟😵👎🤲🤠🤧📌🔵💅🧐🐾🍒😗🤑🌊🤯🐷☎💧😯💆👆🎤🙇🍑❄🌴💣🐸💌📍🥀🤢👅💡💩👐📸👻🤐🤮🎼🥵🚩🍎🍊👼💍📣🥂';
    const TABLE = [...ALPHABET];
    const MULTIBASE_PREFIX = TABLE[0]; // U+1F680 🚀 — multibase code for this encoding

    if (TABLE.length !== 256) {
        throw new Error('Base256Emoji alphabet must contain exactly 256 codepoints');
    }

    const REVERSE = new Map(TABLE.map(function(emoji, index) {
        return [emoji, index];
    }));

    function encodeBytes(bytes, multibase) {
        const emojis = Array.from(bytes, function(byte) {
            return TABLE[byte];
        });
        if (multibase) {
            return MULTIBASE_PREFIX + emojis.join('');
        }
        return emojis.join('');
    }

    function decodeToBytes(text, multibase) {
        let runes = [...String(text).replace(/\s/g, '')];
        if (multibase && runes[0] === MULTIBASE_PREFIX) {
            runes = runes.slice(1);
        }
        if (runes.length === 0) {
            return null;
        }
        const bytes = new Uint8Array(runes.length);
        for (let i = 0; i < runes.length; i++) {
            const value = REVERSE.get(runes[i]);
            if (value === undefined) {
                return null;
            }
            bytes[i] = value;
        }
        return bytes;
    }

    return new BaseTransformer({
        name: 'Base256Emoji',
        priority: 265,
        category: 'encoding',
        description: 'Multiformats Base256Emoji encoding (multibase): each byte maps to one emoji from the standard 256-codepoint alphabet.',
        configurableOptions: [
            {
                key: 'multibase',
                label: 'Multibase prefix',
                type: 'boolean',
                default: false,
                help: 'Prepend the 🚀 multibase code on encode; strip it on decode (interoperable with IPFS/multibase tools).'
            }
        ],
        func: function(text, options) {
            if (!text) {
                return '';
            }
            const multibase = !!(options && options.multibase);
            const bytes = new TextEncoder().encode(text);
            return encodeBytes(bytes, multibase);
        },
        reverse: function(text, options) {
            if (!text) {
                return '';
            }
            const multibase = !!(options && options.multibase);
            let bytes = decodeToBytes(text, multibase);
            if (!bytes && !multibase) {
                bytes = decodeToBytes(text, true);
            }
            if (!bytes) {
                return '';
            }
            try {
                return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
            } catch (e) {
                return '';
            }
        },
        preview: function(text, options) {
            if (!text) {
                return '[base256emoji]';
            }
            return this.func(text.slice(0, 4), options);
        },
        detector: function(text) {
            const runes = [...String(text).replace(/\s/g, '')];
            if (runes.length < 3) {
                return false;
            }
            let start = 0;
            if (runes[0] === MULTIBASE_PREFIX && runes.length > 3) {
                start = 1;
            }
            let hits = 0;
            for (let i = start; i < runes.length; i++) {
                if (REVERSE.has(runes[i])) {
                    hits++;
                }
            }
            const checked = runes.length - start;
            return checked >= 3 && hits / checked >= 0.85;
        }
    });
})();
