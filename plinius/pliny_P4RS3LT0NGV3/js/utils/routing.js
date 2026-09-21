/**
 * Hash-based tab routing for static hosting (GitHub Pages friendly).
 * Examples: #decoder, #/transforms, #codes/decode
 */
(function(global) {
    var suppressHashChange = false;

    function normalizeSegment(value) {
        return String(value || '').trim().toLowerCase();
    }

    function parseHash() {
        var raw = (global.location.hash || '').replace(/^#\/?/, '');
        if (!raw) {
            return null;
        }

        var slashIndex = raw.indexOf('/');
        if (slashIndex === -1) {
            return {
                tab: normalizeSegment(decodeURIComponent(raw)),
                sub: ''
            };
        }

        return {
            tab: normalizeSegment(decodeURIComponent(raw.slice(0, slashIndex))),
            sub: normalizeSegment(decodeURIComponent(raw.slice(slashIndex + 1)))
        };
    }

    function buildHash(tab, sub) {
        var hash = '#' + encodeURIComponent(String(tab || '').trim());
        if (sub) {
            hash += '/' + encodeURIComponent(String(sub).trim());
        }
        return hash;
    }

    function setHash(tab, sub, replace) {
        var next = buildHash(tab, sub);
        if (global.location.hash === next) {
            return;
        }

        suppressHashChange = true;
        if (replace && global.history && typeof global.history.replaceState === 'function') {
            global.history.replaceState(null, '', next);
            suppressHashChange = false;
            return;
        }

        global.location.hash = next;
        global.setTimeout(function() {
            suppressHashChange = false;
        }, 0);
    }

    global.TabRouting = {
        parse: parseHash,
        buildHash: buildHash,
        setHash: setHash,
        shouldIgnoreHashChange: function() {
            return suppressHashChange;
        }
    };
})(typeof window !== 'undefined' ? window : globalThis);
