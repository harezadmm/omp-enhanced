/**
 * Emoji Compatibility Checker
 * Tests which emoji features the user's browser/device supports
 */

window.emojiCompatibility = {
    // Cache key for localStorage
    CACHE_KEY: 'emojiTestResults_v2_simple', // Simple pixel detection only
    CACHE_EXPIRY_DAYS: 30,
    
    // In-memory cache for emoji test results
    _emojiTestCache: null,
    
    /**
     * Load emoji test cache from localStorage
     */
    loadCache: function() {
        if (this._emojiTestCache) return this._emojiTestCache;
        
        try {
            const cached = localStorage.getItem(this.CACHE_KEY);
            if (!cached) return null;
            
            const data = JSON.parse(cached);
            
            // Check if cache is expired
            const now = Date.now();
            const age = now - data.timestamp;
            const maxAge = this.CACHE_EXPIRY_DAYS * 24 * 60 * 60 * 1000;
            
            if (age > maxAge) {
                localStorage.removeItem(this.CACHE_KEY);
                return null;
            }
            
            this._emojiTestCache = data.results;
            return this._emojiTestCache;
        } catch (e) {
            return null;
        }
    },
    
    /**
     * Save emoji test results to localStorage
     * (Called after testing all emojis)
     */
    saveCache: function() {
        if (!this._emojiTestCache) return;
        
        try {
            const data = {
                timestamp: Date.now(),
                results: this._emojiTestCache
            };
            localStorage.setItem(this.CACHE_KEY, JSON.stringify(data));
        } catch (e) {
            console.warn('⚠️  Could not save emoji test cache:', e);
        }
    },
    
    /**
     * Clear the emoji test cache (useful for debugging or forcing refresh)
     */
    clearCache: function() {
        localStorage.removeItem(this.CACHE_KEY);
        this._emojiTestCache = null;
    },
    
    /**
     * Test if a specific emoji actually renders in the browser
     * Uses canvas pixel detection - the definitive test for visual rendering
     */
    testEmojiRenders: function(emoji) {
        // Load cache if not already loaded
        if (!this._emojiTestCache) {
            this._emojiTestCache = this.loadCache() || {};
        }
        
        // Check cache first
        if (emoji in this._emojiTestCache) {
            return this._emojiTestCache[emoji];
        }
        
        // Cache canvas for performance
        if (!this._testCanvas) {
            this._testCanvas = document.createElement('canvas');
            this._testCanvas.width = 64;
            this._testCanvas.height = 64;
            // Set willReadFrequently for better performance with multiple getImageData calls
            this._testCtx = this._testCanvas.getContext('2d', { willReadFrequently: true });
        }
        
        const ctx = this._testCtx;
        // Use emoji font to ensure missing emojis render as boxes
        ctx.font = '48px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "EmojiOne Color", "Android Emoji", sans-serif';
        ctx.textBaseline = 'top';
        ctx.textAlign = 'left';
        
        // Width test - catches multi-character fallbacks like "???"
        const emojiWidth = ctx.measureText(emoji).width;
        const referenceWidth = ctx.measureText('😊').width;
        
        // If emoji is much wider than a single emoji, it's likely broken into multiple chars
        if (emojiWidth > referenceWidth * 1.8) {
            this._emojiTestCache[emoji] = false;
            return false;
        }
        
        // Pixel detection - does the emoji actually render visually?
        ctx.clearRect(0, 0, 64, 64);
        ctx.fillStyle = 'black';
        ctx.fillText(emoji, 8, 8);
        
        const imageData = ctx.getImageData(0, 0, 64, 64).data;
        
        // Check if any pixels were drawn (alpha channel > 0)
        let hasPixels = false;
        for (let i = 0; i < imageData.length; i += 4) {
            if (imageData[i + 3] > 0) {
                hasPixels = true;
                break;
            }
        }
        
        // Cache and return result
        this._emojiTestCache[emoji] = hasPixels;
        return hasPixels;
    },
    
    /**
     * Check if a specific emoji should be shown in the UI picker
     * based on browser compatibility
     */
    shouldShowInPicker: function(emoji, data) {
        // Simple check: Does it actually render?
        // This single test catches all broken emojis regardless of type
        return this.testEmojiRenders(emoji);
    },
    
    /**
     * Get compatible emojis from a list (batch testing with progress callback)
     * @param {Array<string>} allEmojis - Full list of emojis to test
     * @param {Function} progressCallback - Optional callback (tested, total, compatible)
     * @returns {Promise<Array<string>>} - Array of compatible emojis
     */
    getCompatibleEmojis: async function(allEmojis, progressCallback) {
        // Load cache first
        this.loadCache();
        
        const compatible = [];
        let tested = 0;
        const total = allEmojis.length;
        
        // Test emojis in batches to avoid blocking
        const batchSize = 50;
        
        function testBatch() {
            return new Promise((resolve) => {
                const end = Math.min(tested + batchSize, total);
                
                for (let i = tested; i < end; i++) {
                    const emoji = allEmojis[i];
                    if (this.shouldShowInPicker(emoji)) {
                        compatible.push(emoji);
                    }
                    tested++;
                }
                
                // Report progress
                if (progressCallback) {
                    progressCallback(tested, total, compatible.length);
                }
                
                // Continue or finish
                if (tested < total) {
                    requestAnimationFrame(() => {
                        setTimeout(() => resolve(testBatch.call(this)), 10);
                    });
                } else {
                    // Save cache when done
                    this.saveCache();
                    resolve();
                }
            });
        }
        
        await testBatch.call(this);
        return compatible;
    },
    
    /**
     * Get compatibility stats
     */
    getStats: function() {
        const cache = this.loadCache();
        if (cache) {
            const compatible = Object.values(cache).filter(v => v === true).length;
            const total = Object.keys(cache).length;
            return {
                compatible: compatible,
                total: total,
                percentage: total > 0 ? ((compatible / total) * 100).toFixed(1) : 0
            };
        }
        return null;
    }
};

