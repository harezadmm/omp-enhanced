/**
 * Base Tool Class
 * All tools should inherit from this class and implement required methods
 */
class Tool {
    constructor(config) {
        // Required properties
        this.id = config.id; // Unique identifier (e.g., 'transforms', 'decoder')
        this.name = config.name; // Display name (e.g., 'Transform', 'Decoder')
        this.icon = config.icon || 'fa-circle'; // Font Awesome icon class
        this.title = config.title || this.name; // Tooltip/title text
        
        // Optional properties
        this.order = config.order || 999; // Order in tab bar (lower = earlier)
        this.enabled = config.enabled !== false; // Whether tool is enabled
    }
    
    /**
     * Get Vue data properties needed for this tool
     * Should return an object that will be merged into Vue's data
     * @returns {Object}
     */
    getVueData() {
        return {};
    }
    
    /**
     * Get Vue methods needed for this tool
     * Should return an object with method definitions
     * @returns {Object}
     */
    getVueMethods() {
        return {};
    }
    
    /**
     * Get Vue watchers needed for this tool
     * Should return an object with watcher definitions
     * @returns {Object}
     */
    getVueWatchers() {
        return {};
    }
    
    /**
     * Get Vue lifecycle hooks
     * Should return an object with lifecycle methods (mounted, created, etc.)
     * @returns {Object}
     */
    getVueLifecycle() {
        return {};
    }
    
    /**
     * Get HTML template for the tab button
     * @returns {String} HTML string for the tab button
     */
    getTabButtonHTML() {
        return `
            <button 
                :class="{ active: activeTab === '${this.id}' }" 
                @click="switchToTab('${this.id}')"
                title="${this.title}"
            >
                <i class="fas ${this.icon}"></i> ${this.name}
            </button>
        `;
    }
    
    /**
     * Initialize tool-specific functionality
     * Called when the tool's tab is activated
     * @param {Vue} vueInstance - The Vue app instance
     */
    onActivate(vueInstance) {
        // Override in subclasses
    }
    
    /**
     * Cleanup tool-specific functionality
     * Called when switching away from this tool's tab
     * @param {Vue} vueInstance - The Vue app instance
     */
    onDeactivate(vueInstance) {
        // Override in subclasses
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Tool;
} else {
    window.Tool = Tool;
}



