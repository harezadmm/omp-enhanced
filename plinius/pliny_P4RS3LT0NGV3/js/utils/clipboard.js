/**
 * Clipboard Utility
 * Provides unified clipboard copy functionality using Clipboard API
 */
window.ClipboardUtils = {
    /**
     * Copy text to clipboard using Clipboard API
     * @param {string} text - Text to copy
     * @param {Object} options - Options object
     * @param {Function} options.onSuccess - Callback on success
     * @param {Function} options.onError - Callback on error
     * @param {boolean} options.suppressNotification - Don't show notification
     * @returns {Promise<boolean>} - Success status
     */
    async copy(text, options = {}) {
        if (!text) return false;
        
        const {
            onSuccess,
            onError,
            suppressNotification = false
        } = options;
        
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
            const errorMsg = 'Clipboard API not available';
            console.error(errorMsg);
            if (!suppressNotification && window.NotificationUtils) {
                window.NotificationUtils.showNotification('Clipboard not supported', 'error', 'fas fa-exclamation-triangle');
            }
            if (onError) onError(new Error(errorMsg));
            return false;
        }
        
        try {
                await navigator.clipboard.writeText(text);
                if (!suppressNotification && window.NotificationUtils) {
                    window.NotificationUtils.showNotification('Copied!', 'success', 'fas fa-check');
                }
                if (onSuccess) onSuccess();
                return true;
        } catch (err) {
            console.error('Clipboard copy failed:', err);
            if (!suppressNotification && window.NotificationUtils) {
                window.NotificationUtils.showNotification('Copy failed', 'error', 'fas fa-exclamation-triangle');
                }
            if (onError) onError(err);
            return false;
        }
    }
};

