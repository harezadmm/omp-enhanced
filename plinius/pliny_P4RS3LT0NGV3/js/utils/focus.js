window.FocusUtils = {
    focusWithoutScroll(element) {
        if (!element) return;
        
        try {
            const scrollX = window.pageXOffset || window.scrollX || 0;
            const scrollY = window.pageYOffset || window.scrollY || 0;
            element.focus();
            window.scrollTo(scrollX, scrollY);
        } catch (e) {
            try {
                element.focus();
            } catch (err) {
                console.warn('Failed to focus element:', err);
            }
        }
    },
    
    clearFocusAndSelection() {
        if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
        }
        if (window.getSelection) {
            window.getSelection().removeAllRanges();
        }
        document.body.focus();
    }
};

