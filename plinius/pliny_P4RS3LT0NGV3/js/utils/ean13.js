/**
 * EAN-13 normalization helpers for the Codes tool.
 */
(function(global) {
    'use strict';

    function checksum(base12) {
        var sum = 0;
        for (var i = 0; i < 12; i++) {
            var digit = parseInt(base12.charAt(i), 10);
            sum += (i % 2 === 0) ? digit : digit * 3;
        }
        return String((10 - (sum % 10)) % 10);
    }

    function upcChecksum(upc12) {
        var sum = 0;
        for (var i = 0; i < 11; i++) {
            var digit = parseInt(upc12.charAt(i), 10);
            sum += (i % 2 === 0) ? digit * 3 : digit;
        }
        return String((10 - (sum % 10)) % 10);
    }

    function isValidUpcA(digits) {
        return digits.length === 12
            && digits.charAt(0) === '0'
            && upcChecksum(digits) === digits.charAt(11);
    }

    function fromUpcA(upc12) {
        var ean12 = '0' + upc12.slice(0, 11);
        return ean12 + checksum(ean12);
    }

    function normalize(input) {
        var digits = String(input || '').replace(/\D/g, '');
        if (digits.length < 12) {
            return {
                ok: false,
                error: 'EAN-13 requires 12 or 13 digits.'
            };
        }
        if (digits.length > 13) {
            return {
                ok: false,
                error: 'EAN-13 accepts at most 13 digits.'
            };
        }

        if (digits.length === 12 && isValidUpcA(digits)) {
            return { ok: true, value: fromUpcA(digits) };
        }

        var base12 = digits.length === 12 ? digits : digits.slice(0, 12);
        return { ok: true, value: base12 + checksum(base12) };
    }

    var api = {
        checksum: checksum,
        upcChecksum: upcChecksum,
        isValidUpcA: isValidUpcA,
        fromUpcA: fromUpcA,
        normalize: normalize
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        global.Ean13Utils = api;
    }
})(typeof window !== 'undefined' ? window : globalThis);
