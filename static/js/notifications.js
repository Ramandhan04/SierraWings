/**
 * SierraWings Real-time Notification System
 * Automatically checks for notifications every 5 seconds
 */

class SierraWingsNotifications {
    constructor() {
        this.isActive = true;
        this.checkInterval = 5000; // 5 seconds
        this.shownNotifications = new Set();
        this.init();
    }

    init() {
        // Start automatic notification checking
        this.startNotificationLoop();
        
        // Add notification container to page if it doesn't exist
        this.createNotificationContainer();
    }

    createNotificationContainer() {
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                pointer-events: none;
            `;
            document.body.appendChild(container);
        }
    }

    async startNotificationLoop() {
        if (!this.isActive) return;

        try {
            await this.checkForNotifications();
        } catch (error) {
            console.error('Notification check failed:', error);
        }

        // Schedule next check
        setTimeout(() => this.startNotificationLoop(), this.checkInterval);
    }

    async checkForNotifications() {
        try {
            const response = await fetch('/api/notifications');
            if (!response.ok) {
                console.log('Notifications API not available:', response.status);
                return;
            }

            const notifications = await response.json();
            
            for (const notification of notifications) {
                if (!this.shownNotifications.has(notification.id)) {
                    this.showNotification(notification);
                    this.shownNotifications.add(notification.id);
                }
            }
        } catch (error) {
            console.log('Error checking notifications:', error);
        }
    }

    showNotification(notification) {
        const container = document.getElementById('notification-container');
        if (!container) return;

        const notificationEl = document.createElement('div');
        notificationEl.className = `alert alert-${this.getAlertClass(notification.type)} alert-dismissible fade show mb-2`;
        notificationEl.style.cssText = `
            pointer-events: auto;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: none;
            animation: slideInRight 0.3s ease-out;
        `;

        const icon = this.getNotificationIcon(notification.type);
        const actionButton = notification.url ? 
            `<a href="${notification.url}" class="btn btn-outline-light btn-sm ms-2">View</a>` : '';

        notificationEl.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="${icon} me-2"></i>
                <div class="flex-grow-1">
                    <div class="fw-bold">${this.getNotificationTitle(notification.type)}</div>
                    <small>${notification.message}</small>
                </div>
                ${actionButton}
                <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="alert"></button>
            </div>
        `;

        container.appendChild(notificationEl);

        // Auto-remove after specified duration
        const duration = notification.duration || 8000;
        setTimeout(() => {
            if (notificationEl.parentNode) {
                notificationEl.classList.add('fade');
                setTimeout(() => notificationEl.remove(), 150);
            }
        }, duration);

        // Play notification sound for emergency alerts
        if (notification.type === 'emergency') {
            this.playNotificationSound();
        }
    }

    getAlertClass(type) {
        const classes = {
            'mission_update': 'primary',
            'emergency': 'danger',
            'success': 'success',
            'payment': 'info',
            'warning': 'warning',
            'info': 'info'
        };
        return classes[type] || 'info';
    }

    getNotificationIcon(type) {
        const icons = {
            'mission_update': 'fas fa-drone',
            'emergency': 'fas fa-exclamation-triangle',
            'success': 'fas fa-check-circle',
            'payment': 'fas fa-money-bill-wave',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        };
        return icons[type] || 'fas fa-bell';
    }

    getNotificationTitle(type) {
        const titles = {
            'mission_update': 'Mission Update',
            'emergency': 'Emergency Alert',
            'success': 'Success',
            'payment': 'Payment Received',
            'warning': 'System Warning',
            'info': 'Information'
        };
        return titles[type] || 'Notification';
    }

    playNotificationSound() {
        // Create audio context for emergency notifications
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime + 0.2);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (error) {
            // Silent fail if audio not supported
        }
    }

    pause() {
        this.isActive = false;
    }

    resume() {
        this.isActive = true;
        this.startNotificationLoop();
    }
}

// CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .alert-danger {
        background: linear-gradient(135deg, #dc3545, #c82333) !important;
        color: white !important;
        border: none !important;
    }
    
    .alert-primary {
        background: linear-gradient(135deg, #007bff, #0056b3) !important;
        color: white !important;
        border: none !important;
    }
    
    .alert-success {
        background: linear-gradient(135deg, #28a745, #1e7e34) !important;
        color: white !important;
        border: none !important;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #17a2b8, #117a8b) !important;
        color: white !important;
        border: none !important;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #ffc107, #e0a800) !important;
        color: #212529 !important;
        border: none !important;
    }
`;
document.head.appendChild(style);

// Initialize notifications when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.sierraWingsNotifications = new SierraWingsNotifications();
});

// Global notification helper function
window.showSierraWingsNotification = function(message, type = 'info', duration = 5000) {
    const notification = {
        id: `manual_${Date.now()}`,
        type: type,
        message: message,
        duration: duration
    };
    
    if (window.sierraWingsNotifications) {
        window.sierraWingsNotifications.showNotification(notification);
    }
};