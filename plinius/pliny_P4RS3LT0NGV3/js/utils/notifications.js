window.NotificationUtils = {
    showNotification(message, type = 'success', iconClass = null) {
        const existing = document.querySelector('.copy-notification');
        if (existing) {
            existing.remove();
        }
        
        const notification = document.createElement('div');
        notification.className = `copy-notification ${type || 'success'}`;
        
        if (iconClass) {
            const icon = document.createElement('i');
            icon.className = iconClass;
            notification.appendChild(icon);
        }
        
        const text = document.createElement('span');
        text.textContent = message;
        notification.appendChild(text);
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    },
    
    showCopiedPopup() {
        this.showNotification('Copied!', 'success', 'fas fa-check');
    }
};

