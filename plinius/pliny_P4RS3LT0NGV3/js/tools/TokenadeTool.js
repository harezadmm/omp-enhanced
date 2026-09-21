/**
 * Tokenade Tool - Token bomb generator tool
 * Note: This is a complex tool, so we'll include the key methods
 */
class TokenadeTool extends Tool {
    constructor() {
        super({
            id: 'tokenade',
            name: 'Tokenade',
            icon: 'fa-bomb',
            title: 'Tokenade Generator',
            order: 4
        });
    }
    
    getVueData() {
        return {
            tbDepth: 3,
            tbBreadth: 4,
            tbRepeats: 5,
            tbSeparator: 'zwnj',
            tbIncludeVS: true,
            tbIncludeNoise: true,
            tbRandomizeEmojis: true,
            tbAutoCopy: true,
            tbSingleCarrier: true,
            tbCarrier: '',
            tbPayloadEmojis: [],
            tokenBombOutput: '',
            tpBase: '',
            tpRepeat: 100,
            tpCombining: true,
            tpZW: false,
            textPayload: '',
            dangerThresholdTokens: 25_000_000,
            quickCarrierEmojis: ['🐍','🐉','🐲','🔥','💥','🗿','⚓','⭐','✨','🚀','💀','🪨','🍃','🪶','🔮','🐢','🐊','🦎'],
            tbCarrierManual: '',
            carrierEmojiList: [...(window.EmojiUtils ? window.EmojiUtils.getAllEmojis() : [])]
        };
    }
    
    getVueMethods() {
        return {
            generateTokenBomb: function() {
                const depth = Math.max(1, Math.min(8, Number(this.tbDepth) || 1));
                const breadth = Math.max(1, Math.min(10, Number(this.tbBreadth) || 1));
                const repeats = Math.max(1, Math.min(50, Number(this.tbRepeats) || 1));
                const sep = this.tbSeparator === 'zwj' ? '\u200D' : this.tbSeparator === 'zwnj' ? '\u200C' : this.tbSeparator === 'zwsp' ? '\u200B' : '';
                const includeVS = !!this.tbIncludeVS;
                const includeNoise = !!this.tbIncludeNoise;
                const randomize = !!this.tbRandomizeEmojis;

                const emojiList = (this.carrierEmojiList && this.carrierEmojiList.length) ? this.carrierEmojiList : 
                    (window.EmojiUtils ? window.EmojiUtils.getAllEmojis() : this.quickCarrierEmojis);

                function pickEmojis(count) {
                    const out = [];
                    for (let i = 0; i < count; i++) {
                        const idx = randomize ? Math.floor(Math.random() * emojiList.length) : (i % emojiList.length);
                        out.push(String(emojiList[idx]));
                    }
                    return out;
                }

                function addVS(str) {
                    if (!includeVS) return str;
                    // Alternate VS16/VS15 to maximize tokenization churn
                    const vs16 = '\uFE0F';
                    const vs15 = '\uFE0E';
                    let out = '';
                    for (let i = 0; i < str.length; i++) {
                        const ch = str[i];
                        out += ch + (i % 2 === 0 ? vs16 : vs15);
                    }
                    return out;
                }

                function noise() {
                    if (!includeNoise) return '';
                    const parts = ['\u200B','\u200C','\u200D','\u2060','\u2062','\u2063'];
                    let s = '';
                    const n = 1 + Math.floor(Math.random() * 3);
                    for (let i = 0; i < n; i++) s += parts[Math.floor(Math.random() * parts.length)];
                    return s;
                }

                function buildLevel(level) {
                    if (level === 0) {
                        const base = pickEmojis(breadth).join('');
                        return addVS(base);
                    }
                    const items = [];
                    for (let i = 0; i < breadth; i++) {
                        const inner = buildLevel(level - 1);
                        items.push(inner + noise());
                    }
                    return items.join(sep);
                }

                if (this.tbSingleCarrier) {
                    const manual = (this.tbCarrierManual || '').trim();
                    const carrier = manual || (this.tbCarrier && String(this.tbCarrier)) || (this.selectedEmoji ? String(this.selectedEmoji) : '💥');
                    function countUnits(level) {
                        if (level === 0) return breadth;
                        return breadth * countUnits(level - 1);
                    }
                    const unitsPerBlock = countUnits(depth - 1);
                    const totalUnits = Math.max(1, repeats * unitsPerBlock);

                    let payload = [];
                    payload = pickEmojis(totalUnits);

                    function toTagSeqForEmojiChar(ch) {
                        const cp = ch.codePointAt(0);
                        const hex = cp.toString(16);
                        let seq = '';
                        for (const d of hex) {
                            if (d >= '0' && d <= '9') {
                                const base = 0xE0030 + (d.charCodeAt(0) - '0'.charCodeAt(0));
                                seq += String.fromCodePoint(base);
                            } else {
                                const base = 0xE0061 + (d.charCodeAt(0) - 'a'.charCodeAt(0));
                                seq += String.fromCodePoint(base);
                            }
                        }
                        seq += String.fromCodePoint(0xE007F);
                        return seq;
                    }

                    const vs16 = includeVS ? '\uFE0F' : '';
                    let out = carrier + vs16;
                    for (let i = 0; i < payload.length; i++) {
                        out += sep + toTagSeqForEmojiChar(payload[i]) + noise();
                    }
                    this.tokenBombOutput = out;
                } else {
                    let block = buildLevel(depth - 1);
                    // Repeat the block to increase token length
                    const blocks = [];
                    for (let i = 0; i < repeats; i++) {
                        blocks.push(block + noise());
                    }
                    this.tokenBombOutput = blocks.join(sep);
                }

                // Auto-copy if enabled
                if (this.tbAutoCopy && this.tokenBombOutput) {
                    this.$nextTick(() => {
                        this.forceCopyToClipboard(this.tokenBombOutput);
                        this.showNotification('Tokenade generated and copied!', 'success', 'fas fa-bomb');
                    });
                } else {
                    this.showNotification('Tokenade generated!', 'success', 'fas fa-bomb');
                }
            },
            applyTokenadePreset: function(preset) {
                if (preset === 'feather') {
                    this.tbDepth = 1; this.tbBreadth = 3; this.tbRepeats = 2; this.tbSeparator = 'zwnj';
                    this.tbIncludeVS = false; this.tbIncludeNoise = false; this.tbRandomizeEmojis = true;
                } else if (preset === 'light') {
                    this.tbDepth = 2; this.tbBreadth = 3; this.tbRepeats = 3; this.tbSeparator = 'zwnj';
                    this.tbIncludeVS = false; this.tbIncludeNoise = true; this.tbRandomizeEmojis = true;
                } else if (preset === 'middle') {
                    this.tbDepth = 3; this.tbBreadth = 4; this.tbRepeats = 6; this.tbSeparator = 'zwnj';
                    this.tbIncludeVS = true; this.tbIncludeNoise = true; this.tbRandomizeEmojis = true;
                } else if (preset === 'heavy') {
                    this.tbDepth = 4; this.tbBreadth = 6; this.tbRepeats = 12; this.tbSeparator = 'zwnj';
                    this.tbIncludeVS = true; this.tbIncludeNoise = true; this.tbRandomizeEmojis = true;
                } else if (preset === 'super') {
                    this.tbDepth = 5; this.tbBreadth = 8; this.tbRepeats = 18; this.tbSeparator = 'zwnj';
                    this.tbIncludeVS = true; this.tbIncludeNoise = true; this.tbRandomizeEmojis = true;
                }
                this.showNotification('Preset applied', 'success', 'fas fa-sliders-h');
            },
            estimateTokenadeLength: function() {
                const depth = Math.max(1, Math.min(8, Number(this.tbDepth) || 1));
                const breadth = Math.max(1, Math.min(10, Number(this.tbBreadth) || 1));
                const repeats = Math.max(1, Math.min(50, Number(this.tbRepeats) || 1));
                const sepLen = this.tbSeparator === 'none' ? 0 : 1;
                const vsPerEmoji = this.tbIncludeVS ? 1 : 0;
                const noiseAvg = this.tbIncludeNoise ? 2 : 0;

                function lenLevel(level) {
                    if (level === 0) {
                        return breadth * (1 + vsPerEmoji);
                    }
                    const inner = lenLevel(level - 1);
                    return breadth * (inner + noiseAvg) + Math.max(0, breadth - 1) * sepLen;
                }

                if (this.tbSingleCarrier) {
                    function countUnits(level) { return level === 0 ? breadth : breadth * countUnits(level - 1); }
                    const unitsPerBlock = countUnits(depth - 1);
                    const totalUnits = Math.max(1, repeats * unitsPerBlock);
                    const avgDigits = 5;
                    const perUnit = avgDigits + 1 + sepLen + (this.tbIncludeNoise ? 2 : 0);
                    const carrierLen = 1 + (this.tbIncludeVS ? 1 : 0);
                    return carrierLen + totalUnits * perUnit;
                } else {
                    const blockLen = lenLevel(depth - 1);
                    return repeats * (blockLen + noiseAvg) + Math.max(0, repeats - 1) * sepLen;
                }
            },
            estimateTokenadeTokens: function() {
                return Math.max(0, this.estimateTokenadeLength());
            },
            setCarrierFromSelected: function() {
                if (this.selectedEmoji) this.tbCarrier = String(this.selectedEmoji);
            },
            generateTextPayload: function() {
                const base = String(this.tpBase || 'A');
                const count = Math.max(1, Math.min(10000, Number(this.tpRepeat) || 1));
                const combining = this.tpCombining;
                const addZW = this.tpZW;
                const marks = ['\u0301','\u0300','\u0302','\u0303','\u0308','\u0307','\u0304'];
                const zw = ['\u200B','\u200C','\u200D','\u2060'];
                let out = '';
                for (let i=0;i<count;i++) {
                    let token = base;
                    if (combining) {
                        const m = marks[i % marks.length];
                        token += m;
                    }
                    if (addZW) {
                        const z = zw[i % zw.length];
                        token += z;
                    }
                    out += token;
                }
                this.textPayload = out;
                this.showNotification('Text payload generated', 'success', 'fas fa-bomb');
            }
        };
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TokenadeTool;
} else {
    window.TokenadeTool = TokenadeTool;
}



