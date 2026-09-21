window.HistoryUtils = {
    addToHistory(historyArray, maxItems, source, content) {
        if (!historyArray || !Array.isArray(historyArray)) {
            console.warn('HistoryUtils.addToHistory: historyArray is not an array');
            return;
        }
        
        if (!content) {
            return;
        }
        
        const entry = {
            source: source || 'Unknown',
            content: content,
            timestamp: new Date().toISOString(),
            id: Date.now() + Math.random()
        };
        
        historyArray.unshift(entry);
        
        if (historyArray.length > maxItems) {
            historyArray.splice(maxItems);
        }
    },
    
    clearHistory(historyArray) {
        if (historyArray && Array.isArray(historyArray)) {
            // Use splice to remove all items (same approach as removeFromHistory)
            historyArray.splice(0, historyArray.length);
        }
    },
    
    removeFromHistory(historyArray, id) {
        if (!historyArray || !Array.isArray(historyArray)) {
            return;
        }
        
        const index = historyArray.findIndex(item => item.id === id);
        if (index !== -1) {
            historyArray.splice(index, 1);
        }
    },
    
    getHistorySource(activeTab, context = {}) {
        if (activeTab === 'transforms' && context.activeTransform) {
            return `Transform: ${context.activeTransform.name}`;
        } else if (activeTab === 'steganography') {
            if (context.activeSteg === 'invisible') {
                return 'Invisible Text';
            } else if (context.selectedEmoji) {
                return `Emoji: ${context.selectedEmoji}`;
            }
            return 'Steganography';
        } else if (activeTab === 'transforms') {
            return 'Transform';
        }
        return 'Unknown';
    }
};

