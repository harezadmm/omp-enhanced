// Base122 encoding (Kevin Albs) — UTF-8 binary-to-text, ~14% smaller than Base64
import BaseTransformer from '../BaseTransformer.js';

export default (function() {
    const kIllegals = [
        0, 10, 13, 34, 38, 92
    ];
    const kShortened = 0b111;

    function encodeBase122Bytes(bytes) {
        let curIndex = 0;
        let curBit = 0;
        const outData = [];

        function get7() {
            if (curIndex >= bytes.length) {
                return false;
            }

            const firstByte = bytes[curIndex];
            let firstPart = ((0b11111110 >>> curBit) & firstByte) << curBit;
            firstPart >>= 1;
            curBit += 7;

            if (curBit < 8) {
                return firstPart;
            }

            curBit -= 8;
            curIndex++;

            if (curIndex >= bytes.length) {
                return firstPart;
            }

            const secondByte = bytes[curIndex];
            let secondPart = ((0xFF00 >>> curBit) & secondByte) & 0xFF;
            secondPart >>= 8 - curBit;
            return firstPart | secondPart;
        }

        while (true) {
            const bits = get7();
            if (bits === false) {
                break;
            }

            const illegalIndex = kIllegals.indexOf(bits);
            if (illegalIndex !== -1) {
                let nextBits = get7();
                let b1 = 0b11000010;
                let b2 = 0b10000000;

                if (nextBits === false) {
                    b1 |= (kShortened & 0b111) << 2;
                    nextBits = bits;
                } else {
                    b1 |= (illegalIndex & 0b111) << 2;
                }

                const firstBit = (nextBits & 0b01000000) > 0 ? 1 : 0;
                b1 |= firstBit;
                b2 |= nextBits & 0b00111111;
                outData.push(b1, b2);
            } else {
                outData.push(bits);
            }
        }

        return new TextDecoder('utf-8').decode(new Uint8Array(outData));
    }

    function decodeBase122String(strData) {
        const decoded = [];
        let curByte = 0;
        let bitOfByte = 0;

        function push7(byte) {
            byte <<= 1;
            curByte |= (byte >>> bitOfByte);
            bitOfByte += 7;

            if (bitOfByte >= 8) {
                decoded.push(curByte);
                bitOfByte -= 8;
                curByte = (byte << (7 - bitOfByte)) & 255;
            }
        }

        for (let i = 0; i < strData.length; i++) {
            const c = strData.charCodeAt(i);

            if (c > 127) {
                const illegalIndex = (c >>> 8) & 7;
                if (illegalIndex !== kShortened) {
                    push7(kIllegals[illegalIndex]);
                }
                push7(c & 127);
            } else {
                push7(c);
            }
        }

        return new Uint8Array(decoded);
    }

    return new BaseTransformer({
        name: 'Base122',
        priority: 250,
        category: 'encoding',
        func: function(text) {
            const bytes = new TextEncoder().encode(text);
            return encodeBase122Bytes(bytes);
        },
        reverse: function(text) {
            try {
                const bytes = decodeBase122String(text);
                return new TextDecoder().decode(bytes);
            } catch (e) {
                return '';
            }
        },
        preview: function(text) {
            if (!text) {
                return '[base122]';
            }
            const result = this.func(text.slice(0, 10));
            return result.substring(0, 15) + (result.length > 15 ? '...' : '');
        },
        detector: function(text) {
            if (!text || text.length < 4) {
                return false;
            }
            return /[\u0080-\uFFFF]/.test(text) || (text.length >= 8 && text !== text.trim());
        }
    });
})();
