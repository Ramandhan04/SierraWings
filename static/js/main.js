// SierraWings Main JavaScript

// Global variables
let currentUser = null;
let notificationInterval = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    
    // Setup form validation
    setupFormValidation();
    
    // Setup auto-refresh for mission data
    setupAutoRefresh();
    
    // Setup notification system
    setupNotifications();
    
    // Add loading states to buttons
    setupButtonLoading();
}

// Form Validation
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
            
            // Add loading state to submit button
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                addLoadingState(submitBtn);
            }
        });
    });
}

// Auto-refresh system
function setupAutoRefresh() {
    // Refresh mission statistics every 30 seconds
    if (window.location.pathname.includes('/dashboard') || 
        window.location.pathname.includes('/clinic') || 
        window.location.pathname.includes('/admin')) {
        
        setInterval(refreshMissionStats, 30000);
    }
}

function refreshMissionStats() {
    fetch('/api/missions/stats')
        .then(response => response.json())
        .then(stats => {
            updateMissionBadges(stats);
        })
        .catch(error => {
            console.error('Error refreshing mission stats:', error);
        });
}

function updateMissionBadges(stats) {
    // Update tab badges if they exist
    const pendingTab = document.querySelector('#pending-tab');
    const acceptedTab = document.querySelector('#accepted-tab');
    const inflightTab = document.querySelector('#inflight-tab');
    
    if (pendingTab) {
        pendingTab.innerHTML = `<i class="fas fa-clock me-2"></i>Pending Requests (${stats.pending})`;
    }
    
    if (acceptedTab) {
        acceptedTab.innerHTML = `<i class="fas fa-check me-2"></i>Accepted (${stats.accepted})`;
    }
    
    if (inflightTab) {
        inflightTab.innerHTML = `<i class="fas fa-plane me-2"></i>In Flight (${stats.in_flight})`;
    }
    
    // Update stat cards
    updateStatCards(stats);
}

function updateStatCards(stats) {
    const statElements = {
        'total_missions': stats.total,
        'pending_missions': stats.pending,
        'in_flight_missions': stats.in_flight,
        'completed_missions': stats.completed
    };
    
    Object.entries(statElements).forEach(([id, value]) => {
        const element = document.querySelector(`#${id}, .stat-content h3`);
        if (element && !isNaN(value)) {
            element.textContent = value;
        }
    });
}

// Notification system
function setupNotifications() {
    // Check for new notifications every minute
    notificationInterval = setInterval(checkNotifications, 60000);
}

function checkNotifications() {
    if (window.location.pathname.includes('/patient/')) {
        checkPatientNotifications();
    } else if (window.location.pathname.includes('/clinic/')) {
        checkClinicNotifications();
    }
}

function checkPatientNotifications() {
    // Check for mission status updates
    fetch('/api/missions/stats')
        .then(response => response.json())
        .then(stats => {
            // Show notification for completed missions
            if (stats.completed > (localStorage.getItem('lastCompletedCount') || 0)) {
                showNotification('Mission completed successfully!', 'success');
                localStorage.setItem('lastCompletedCount', stats.completed);
            }
        })
        .catch(error => {
            console.error('Error checking notifications:', error);
        });
}

function checkClinicNotifications() {
    // Check for new pending missions
    fetch('/api/missions/stats')
        .then(response => response.json())
        .then(stats => {
            if (stats.pending > (localStorage.getItem('lastPendingCount') || 0)) {
                showNotification('New delivery request received!', 'info');
                localStorage.setItem('lastPendingCount', stats.pending);
            }
        })
        .catch(error => {
            console.error('Error checking notifications:', error);
        });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Button loading states
function setupButtonLoading() {
    // Add loading state to form submit buttons
    document.addEventListener('submit', function(event) {
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn && !submitBtn.disabled) {
            addLoadingState(submitBtn);
        }
    });
}

function addLoadingState(button) {
    if (button.classList.contains('loading')) return;
    
    button.classList.add('loading');
    button.disabled = true;
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    
    // Remove loading state after 10 seconds (fallback)
    setTimeout(() => {
        removeLoadingState(button, originalText);
    }, 10000);
}

function removeLoadingState(button, originalText) {
    button.classList.remove('loading');
    button.disabled = false;
    button.innerHTML = originalText;
}

// Utility functions
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatDuration(startTime, endTime = null) {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const diff = end - start;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy to clipboard', 'danger');
    });
}

// API Helper functions
function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return fetch(url, mergedOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
}

function apiPost(url, data) {
    return apiRequest(url, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

function apiPut(url, data) {
    return apiRequest(url, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

function apiDelete(url) {
    return apiRequest(url, {
        method: 'DELETE'
    });
}

// Map utilities
function createDroneIcon(color = '#0d6efd') {
    return L.divIcon({
        className: 'drone-marker',
        html: `<i class="fas fa-helicopter" style="color: ${color}; font-size: 16px;"></i>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
}

function createMarkerIcon(icon, color = '#0d6efd') {
    return L.divIcon({
        className: 'custom-marker',
        html: `<i class="fas fa-${icon}" style="color: ${color}; font-size: 16px;"></i>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
}

// Map initialization helper
function initializeMap(containerId, center = [37.7749, -122.4194], zoom = 12) {
    const map = L.map(containerId).setView(center, zoom);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    return map;
}

// Cleanup function
function cleanup() {
    if (notificationInterval) {
        clearInterval(notificationInterval);
    }
    
    // Clear any ongoing tracking intervals
    if (window.trackingInterval) {
        clearInterval(window.trackingInterval);
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', cleanup);

// Export functions for global use
window.SierraWings = {
    showNotification,
    addLoadingState,
    removeLoadingState,
    apiRequest,
    apiPost,
    apiPut,
    apiDelete,
    formatDateTime,
    formatDuration,
    copyToClipboard,
    createDroneIcon,
    createMarkerIcon,
    initializeMap
};

// Theme toggle (if needed in the future)
function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
}

// Apply saved theme
function applySavedTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
}

// Initialize theme on load
document.addEventListener('DOMContentLoaded', applySavedTheme);

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Alt + D: Dashboard
    if (event.altKey && event.key === 'd') {
        event.preventDefault();
        const dashboardLink = document.querySelector('a[href*="dashboard"]');
        if (dashboardLink) dashboardLink.click();
    }
    
    // Alt + R: Refresh
    if (event.altKey && event.key === 'r') {
        event.preventDefault();
        location.reload();
    }
    
    // Escape: Close modals
    if (event.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            const modal = bootstrap.Modal.getInstance(openModal);
            if (modal) modal.hide();
        }
    }
});

// Performance monitoring
function logPerformance(label) {
    if (performance && performance.mark) {
        performance.mark(label);
        console.log(`Performance mark: ${label}`);
    }
}

// Error handling
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showNotification('An unexpected error occurred. Please refresh the page.', 'danger');
});

// Unhandled promise rejection handling
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showNotification('A network error occurred. Please check your connection.', 'warning');
});
