/**
 * SierraWings Global Notification System
 * Ensures notifications work across all sections and pages
 */

// Create notification container on every page
function ensureNotificationContainer() {
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
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
    return container;
}

// Enhanced global notification function
function showSierraWingsNotification(message, type = 'info', duration = 10000) {
    const container = ensureNotificationContainer();

    const notificationEl = document.createElement('div');
    const alertClass = type === 'error' ? 'danger' : type;
    
    notificationEl.className = `alert alert-${alertClass} alert-dismissible fade show mb-2 sierrra-notification`;
    notificationEl.style.cssText = `
        pointer-events: auto;
        min-width: 300px;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border: none;
        animation: slideInRight 0.3s ease-out;
        position: relative;
    `;

    const icon = type === 'success' ? 'fas fa-check-circle' : 
                 type === 'error' ? 'fas fa-exclamation-triangle' :
                 type === 'warning' ? 'fas fa-exclamation-circle' : 
                 type === 'emergency' ? 'fas fa-bell' : 'fas fa-info-circle';

    notificationEl.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="${icon} me-2"></i>
            <div class="flex-grow-1">
                <div class="fw-bold">SierraWings Alert</div>
                <small>${message}</small>
            </div>
            <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(notificationEl);

    // Play sound for emergency notifications
    if (type === 'emergency') {
        playNotificationSound();
    }

    // Auto-remove after 10 seconds
    const timeoutId = setTimeout(() => {
        if (notificationEl && notificationEl.parentNode) {
            notificationEl.classList.remove('show');
            notificationEl.classList.add('fade-out');
            setTimeout(() => {
                if (notificationEl && notificationEl.parentNode) {
                    notificationEl.remove();
                }
            }, 300);
        }
    }, duration);

    // Allow manual dismissal
    const closeBtn = notificationEl.querySelector('.btn-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            clearTimeout(timeoutId);
            notificationEl.remove();
        });
    }

    // Return element for potential manipulation
    return notificationEl;
}

// Play notification sound for emergencies
function playNotificationSound() {
    try {
        // Create audio context and play notification beep
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.log('Audio notification not supported');
    }
}

// Show flash messages from Flask as notifications
function showFlashMessages() {
    const flashMessages = window.flashMessages || [];
    flashMessages.forEach(([category, message]) => {
        const type = category === 'error' ? 'error' : 
                    category === 'success' ? 'success' :
                    category === 'warning' ? 'warning' : 'info';
        showSierraWingsNotification(message, type);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    ensureNotificationContainer();
    
    // Show any flash messages
    showFlashMessages();
    
    // Add CSS animations if not already present
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
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
            
            @keyframes fadeOut {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100%);
                }
            }
            
            .fade-out {
                animation: fadeOut 0.3s ease-out forwards;
            }
            
            .sierrra-notification {
                backdrop-filter: blur(10px);
            }
            
            .alert-danger {
                background: linear-gradient(135deg, #dc3545, #c82333) !important;
                color: white !important;
                border: none !important;
            }
            
            .alert-success {
                background: linear-gradient(135deg, #28a745, #1e7e34) !important;
                color: white !important;
                border: none !important;
            }
            
            .alert-warning {
                background: linear-gradient(135deg, #ffc107, #e0a800) !important;
                color: #212529 !important;
                border: none !important;
            }
            
            .alert-info {
                background: linear-gradient(135deg, #17a2b8, #138496) !important;
                color: white !important;
                border: none !important;
            }
            
            .alert-primary {
                background: linear-gradient(135deg, #007bff, #0056b3) !important;
                color: white !important;
                border: none !important;
            }
        `;
        document.head.appendChild(style);
    }
});

// Test notification function for debugging
function testNotification() {
    showSierraWingsNotification('Test notification - SierraWings system is working!', 'success');
}

// Export for global use
window.showSierraWingsNotification = showSierraWingsNotification;
window.testNotification = testNotification;