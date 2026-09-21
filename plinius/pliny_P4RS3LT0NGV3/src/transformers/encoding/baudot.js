// Baudot / ITA2 telegraph code — 5-bit letters/figures with shift codes
import BaseTransformer from '../BaseTransformer.js';

export default (function() {
    const FIGS = 0b11011;
    const LTRS = 0b11111;

    const LETTERS = {
        'A': 0b00100,
        'B': 0b11010,
        'C': 0b01111,
        'D': 0b01010,
        'E': 0b00010,
        'F': 0b01110,
        'G': 0b00001,
        'H': 0b10101,
        'I': 0b00111,
        'J': 0b01100,
        'K': 0b10000,
        'L': 0b10011,
        'M': 0b11101,
        'N': 0b01101,
        'O': 0b11001,
        'P': 0b10111,
        'Q': 0b11000,
        'R': 0b01011,
        'S': 0b00110,
        'T': 0b10001,
        'U': 0b01000,
        'V': 0b11100,
        'W': 0b10100,
        'X': 0b11110,
        'Y': 0b10110,
        'Z': 0b10010
    };

    const FIGURES = {
        '-': 0b00100,
        '?': 0b11010,
        ':': 0b01111,
        '$': 0b01010,
        '3': 0b00010,
        '!': 0b01110,
        '&': 0b11011,
        '8': 0b00111,
        '7': 0b01000,
        '4': 0b01011,
        ',': 0b01101,
        '(': 0b10000,
        ')': 0b10011,
        '.': 0b11101,
        '0': 0b10111,
        '1': 0b11000,
        '9': 0b11001,
        '5': 0b10001,
        '+': 0b10010,
        '2': 0b10100,
        '6': 0b10110,
        '/': 0b11110
    };

    const LETTER_BY_CODE = {};
    const FIGURE_BY_CODE = {};

    for (const [char, code] of Object.entries(LETTERS)) {
        LETTER_BY_CODE[code] = char;
    }
    for (const [char, code] of Object.entries(FIGURES)) {
        if (char !== '&') {
            FIGURE_BY_CODE[code] = char;
        }
    }
    FIGURE_BY_CODE[FIGS] = '&';

    function isFigureChar(char) {
        return Object.prototype.hasOwnProperty.call(FIGURES, char);
    }

    function isLetterChar(char) {
        return Object.prototype.hasOwnProperty.call(LETTERS, char);
    }

    function codesToDisplay(codes) {
        return codes.map(code => code.toString(2).padStart(5, '0')).join(' ');
    }

    function parseDisplayCodes(text) {
        return text.trim().split(/\s+/).map(token => {
            if (!/^[01]{5}$/.test(token)) {
                return null;
            }
            return parseInt(token, 2);
        }).filter(code => code !== null);
    }

    return new BaseTransformer({
        name: 'Baudot Code (ITA2)',
        priority: 250,
        category: 'encoding',
        func: function(text) {
            const upper = text.toUpperCase();
            const codes = [];
            let inFigures = false;

            for (const char of upper) {
                if (char === '\n') {
                    codes.push(0b00011);
                    continue;
                }
                if (char === '\r') {
                    codes.push(0b01001);
                    continue;
                }
                if (char === ' ') {
                    codes.push(0b00101);
                    continue;
                }

                const wantsFigure = isFigureChar(char);
                const wantsLetter = isLetterChar(char);

                if (wantsFigure && !inFigures) {
                    codes.push(FIGS);
                    inFigures = true;
                } else if (wantsLetter && inFigures && char !== '&') {
                    codes.push(LTRS);
                    inFigures = false;
                }

                if (char === '&' && !inFigures) {
                    codes.push(FIGS);
                    inFigures = true;
                }

                const map = inFigures ? FIGURES : LETTERS;
                if (Object.prototype.hasOwnProperty.call(map, char)) {
                    codes.push(map[char]);
                }
            }

            return codesToDisplay(codes);
        },
        reverse: function(text) {
            const codes = parseDisplayCodes(text);
            if (codes.length === 0) {
                return '';
            }

            let result = '';
            let inFigures = false;

            for (const code of codes) {
                if (code === FIGS && !inFigures) {
                    inFigures = true;
                    continue;
                }
                if (code === LTRS && inFigures) {
                    inFigures = false;
                    continue;
                }
                if (code === 0b00011) {
                    result += '\n';
                    continue;
                }
                if (code === 0b01001) {
                    result += '\r';
                    continue;
                }
                if (code === 0b00101) {
                    result += ' ';
                    continue;
                }

                const map = inFigures ? FIGURE_BY_CODE : LETTER_BY_CODE;
                const char = map[code];
                if (char) {
                    result += char;
                }
            }

            return result;
        },
        preview: function(text) {
            if (!text) {
                return '[baudot]';
            }
            return this.func(text.slice(0, 5));
        },
        detector: function(text) {
            const tokens = text.trim().split(/\s+/);
            if (tokens.length < 4) {
                return false;
            }
            return tokens.every(token => /^[01]{5}$/.test(token));
        }
    });
})();
