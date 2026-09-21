/**
 * Theme registry and application.
 * Add entries to `themes` to expose new themes in the UI dropdown.
 */
window.ThemeUtils = {
    defaultTheme: 'dark',

    themes: [
        { id: 'dark', name: 'Dark', icon: 'fa-moon' },
        { id: 'light', name: 'Light', icon: 'fa-sun' },
        { id: 'accessible', name: 'Accessible', icon: 'fa-universal-access' },
        { id: 'bt6', name: 'BT6', icon: 'fa-shield-halved' },
        { id: 'pliny', name: 'Pliny', icon: 'fa-dragon' },
        { id: 'cyberpunk', name: 'Cyberpunk', icon: 'fa-city' },
        { id: 'wildwest', name: 'Wild West', icon: 'fa-hat-cowboy' }
    ],

    getThemes() {
        return this.themes.slice();
    },

    isValidTheme(themeId) {
        return this.themes.some(function(theme) {
            return theme.id === themeId;
        });
    },

    normalizeThemeId(themeId) {
        if (this.isValidTheme(themeId)) {
            return themeId;
        }
        return this.defaultTheme;
    },

    applyTheme(themeId) {
        var resolved = this.normalizeThemeId(themeId);
        var body = document.body;

        this.themes.forEach(function(theme) {
            body.classList.remove('theme-' + theme.id);
        });
        body.classList.remove('dark-theme', 'light-theme');

        body.classList.add('theme-' + resolved);

        // Legacy aliases used by a few rules / older saved state
        if (resolved === 'light' || resolved === 'accessible') {
            body.classList.add('light-theme');
        } else {
            body.classList.add('dark-theme');
        }

        try {
            localStorage.setItem('theme', resolved);
        } catch (e) {
            console.warn('Failed to save theme preference:', e);
        }

        return resolved;
    },

    initializeTheme() {
        try {
            var saved = localStorage.getItem('theme');
            if (saved) {
                return this.normalizeThemeId(saved);
            }
        } catch (e) {
            console.warn('Failed to load theme preference:', e);
        }
        return this.defaultTheme;
    },

    cycleTheme(currentThemeId) {
        var current = this.normalizeThemeId(currentThemeId);
        var index = this.themes.findIndex(function(theme) {
            return theme.id === current;
        });
        if (index === -1) {
            index = 0;
        }
        var next = this.themes[(index + 1) % this.themes.length];
        return this.applyTheme(next.id);
    },

    /** Apply saved theme before Vue mounts (call from inline script in index). */
    applyInitialTheme() {
        return this.applyTheme(this.initializeTheme());
    }
};
