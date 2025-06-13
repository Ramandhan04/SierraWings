/**
 * SierraWings Notification System
 * Automatic popup notifications for real-time updates
 */

class SierraWingsNotifications {
    constructor() {
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultDuration = 8000; // 8 seconds
        this.container = null;
        this.isInitialized = false;
        this.updateInterval = null;
        
        this.init();
    }
    
    init() {
        if (this.isInitialized) return;
        
        // Create notification container
        this.createNotificationContainer();
        
        // Request notification permission
        this.requestPermission();
        
        // Start checking for new notifications
        this.startNotificationUpdates();
        
        this.isInitialized = true;
    }
    
    createNotificationContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            pointer-events: none;
        `;
        document.body.appendChild(this.container);
    }
    
    async requestPermission() {
        if ("Notification" in window) {
            if (Notification.permission === "default") {
                const permission = await Notification.requestPermission();
                if (permission === "granted") {
                    this.showSuccess("Notifications enabled! You'll receive real-time updates.");
                }
            }
        }
    }
    
    startNotificationUpdates() {
        // Check for new notifications every 5 seconds
        this.updateInterval = setInterval(() => {
            this.checkForNewNotifications();
        }, 5000);
    }
    
    async checkForNewNotifications() {
        try {
            const response = await fetch('/api/notifications');
            if (response.ok) {
                const notifications = await response.json();
                
                notifications.forEach(notification => {
                    if (!this.hasBeenShown(notification.id)) {
                        this.showNotification(notification);
                        this.markAsShown(notification.id);
                    }
                });
            }
        } catch (error) {
            console.error('Error checking notifications:', error);
        }
    }
    
    hasBeenShown(notificationId) {
        const shown = localStorage.getItem('shown_notifications') || '[]';
        const shownIds = JSON.parse(shown);
        return shownIds.includes(notificationId);
    }
    
    markAsShown(notificationId) {
        const shown = localStorage.getItem('shown_notifications') || '[]';
        const shownIds = JSON.parse(shown);
        shownIds.push(notificationId);
        
        // Keep only last 100 notifications to prevent localStorage bloat
        if (shownIds.length > 100) {
            shownIds.splice(0, shownIds.length - 100);
        }
        
        localStorage.setItem('shown_notifications', JSON.stringify(shownIds));
    }
    
    showNotification(notification) {
        // Show in-app notification
        this.showInApp(notification.message, notification.type, notification.duration);
        
        // Show browser notification if permission granted
        if (Notification.permission === "granted") {
            this.showBrowserNotification(notification);
        }
    }
    
    showInApp(message, type = 'info', duration = null) {
        const notification = this.createNotificationElement(message, type);
        
        // Add to container
        this.container.appendChild(notification);
        this.notifications.push(notification);
        
        // Remove old notifications if exceeding max
        while (this.notifications.length > this.maxNotifications) {
            const oldest = this.notifications.shift();
            if (oldest.parentNode) {
                oldest.remove();
            }
        }
        
        // Auto remove after duration
        const timeout = duration || this.defaultDuration;
        setTimeout(() => {
            this.removeNotification(notification);
        }, timeout);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
    }
    
    createNotificationElement(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${this.getBootstrapType(type)} alert-dismissible fade notification-item`;
        notification.style.cssText = `
            margin-bottom: 10px;
            pointer-events: auto;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: none;
            border-radius: 8px;
            font-weight: 500;
            transform: translateX(100%);
            transition: all 0.3s ease-in-out;
        `;
        
        const icon = this.getIcon(type);
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="${icon} me-2"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close" onclick="sierraNotifications.removeNotification(this.parentElement.parentElement)"></button>
            </div>
        `;
        
        return notification;
    }
    
    showBrowserNotification(notification) {
        const options = {
            body: notification.message,
            icon: '/static/images/sierrawings-icon.png',
            badge: '/static/images/sierrawings-badge.png',
            tag: notification.type,
            requireInteraction: notification.type === 'emergency',
            actions: notification.actions || []
        };
        
        const browserNotification = new Notification('SierraWings', options);
        
        browserNotification.onclick = function() {
            window.focus();
            if (notification.url) {
                window.location.href = notification.url;
            }
            browserNotification.close();
        };
        
        // Auto close after 10 seconds unless it's an emergency
        if (notification.type !== 'emergency') {
            setTimeout(() => {
                browserNotification.close();
            }, 10000);
        }
    }
    
    removeNotification(element) {
        if (element && element.parentNode) {
            element.style.transform = 'translateX(100%)';
            element.style.opacity = '0';
            
            setTimeout(() => {
                if (element.parentNode) {
                    element.remove();
                }
                
                const index = this.notifications.indexOf(element);
                if (index > -1) {
                    this.notifications.splice(index, 1);
                }
            }, 300);
        }
    }
    
    getBootstrapType(type) {
        const typeMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'info',
            'emergency': 'danger',
            'mission_update': 'primary',
            'payment': 'success'
        };
        return typeMap[type] || 'info';
    }
    
    getIcon(type) {
        const iconMap = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle',
            'emergency': 'fas fa-ambulance',
            'mission_update': 'fas fa-drone',
            'payment': 'fas fa-credit-card'
        };
        return iconMap[type] || 'fas fa-bell';
    }
    
    // Public methods for manual notifications
    showSuccess(message, duration = null) {
        this.showInApp(message, 'success', duration);
    }
    
    showError(message, duration = null) {
        this.showInApp(message, 'error', duration);
    }
    
    showWarning(message, duration = null) {
        this.showInApp(message, 'warning', duration);
    }
    
    showInfo(message, duration = null) {
        this.showInApp(message, 'info', duration);
    }
    
    showEmergency(message, duration = 15000) {
        this.showInApp(message, 'emergency', duration);
        
        // Also show browser notification for emergencies
        if (Notification.permission === "granted") {
            this.showBrowserNotification({
                message: message,
                type: 'emergency',
                duration: duration
            });
        }
    }
    
    showMissionUpdate(message, duration = null) {
        this.showInApp(message, 'mission_update', duration);
    }
    
    showPaymentUpdate(message, duration = null) {
        this.showInApp(message, 'payment', duration);
    }
    
    // Cleanup
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.container && this.container.parentNode) {
            this.container.remove();
        }
        
        this.notifications = [];
        this.isInitialized = false;
    }
}

// Global notification instance
let sierraNotifications;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    sierraNotifications = new SierraWingsNotifications();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (sierraNotifications) {
        sierraNotifications.destroy();
    }
});

// Export for use in other scripts
window.sierraNotifications = sierraNotifications;