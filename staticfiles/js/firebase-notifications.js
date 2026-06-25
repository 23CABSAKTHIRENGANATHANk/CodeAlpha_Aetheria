// ──────────────────────────────────────────────────────────────
// AETHERIA Firebase Push Notification Integration
// Device Token Registration & Push Handling
// ──────────────────────────────────────────────────────────────

class AetheriaFirebaseNotifications {
    constructor(firebaseConfig) {
        this.firebaseConfig = firebaseConfig;
        this.app = null;
        this.messaging = null;
        this.isInitialized = false;
        this.vapidKey = firebaseConfig.vapidKey || 'REPLACE_WITH_VAPID_KEY'; // Set from environment
    }
    
    /**
     * Initialize Firebase and request notification permissions
     */
    async initialize() {
        if (this.isInitialized) {
            console.warn('[Firebase] Already initialized');
            return;
        }
        
        try {
            if (typeof firebase === 'undefined') {
                throw new Error('Firebase SDK is not loaded');
            }

            // Initialize Firebase
            this.app = firebase.initializeApp(this.firebaseConfig);
            this.messaging = firebase.messaging();
            
            console.log('[Firebase] Initialized successfully');
            
            // Check for notification support
            if (!('Notification' in window)) {
                console.warn('[Firebase] Browser does not support notifications');
                return;
            }
            
            // Request permission if needed
            if (Notification.permission === 'granted') {
                await this.registerDeviceToken();
            } else if (Notification.permission !== 'denied') {
                this._requestNotificationPermission();
            }
            
            // Set up foreground message handler
            this._setupForegroundHandler();
            
            this.isInitialized = true;
            
        } catch (error) {
            console.error('[Firebase] Initialization error:', error);
            this._notifyError('Firebase initialization failed', error);
        }
    }
    
    /**
     * Request notification permission from user
     */
    async _requestNotificationPermission() {
        try {
            console.log('[Firebase] Requesting notification permission...');
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('[Firebase] Notification permission granted');
                await this.registerDeviceToken();
            } else {
                console.warn('[Firebase] Notification permission denied');
            }
        } catch (error) {
            console.error('[Firebase] Permission request error:', error);
        }
    }
    
    /**
     * Register device token with backend
     */
    async registerDeviceToken() {
        try {
            // Get registration token
            const token = await this.messaging.getToken({
                vapidKey: this.vapidKey
            });
            
            if (!token) {
                console.warn('[Firebase] No registration token available');
                return;
            }
            
            console.log('[Firebase] Device token obtained:', token.substring(0, 20) + '...');
            
            // Send token to backend
            await this._sendTokenToBackend(token);
            
            // Refresh token on update
            this._setupTokenRefresh();
            
        } catch (error) {
            console.error('[Firebase] Token registration error:', error);
            this._notifyError('Failed to register device token', error);
        }
    }
    
    /**
     * Send device token to Django backend
     */
    async _sendTokenToBackend(token) {
        try {
            const csrfToken = this._getCookie('csrftoken');
            
            const response = await fetch('/api/register-device-token/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    token: token,
                    user_agent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                throw new Error(`Backend error: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('[Firebase] Device token registered successfully');
            
            // Store token locally for reference
            localStorage.setItem('aetheria_fcm_token', token);
            localStorage.setItem('aetheria_fcm_token_time', new Date().toISOString());
            
            // Dispatch success event
            document.dispatchEvent(new CustomEvent('aetheria:token-registered', { 
                detail: { token: token.substring(0, 20) + '...' } 
            }));
            
        } catch (error) {
            console.error('[Firebase] Failed to send token to backend:', error);
            this._notifyError('Could not register device for notifications', error);
        }
    }
    
    /**
     * Setup token refresh listener
     */
    _setupTokenRefresh() {
        try {
            // Firebase automatically refreshes tokens
            // We can optionally refresh manually
            setInterval(async () => {
                try {
                    const token = await this.messaging.getToken({
                        vapidKey: this.vapidKey
                    });
                    
                    const oldToken = localStorage.getItem('aetheria_fcm_token');
                    if (token && token !== oldToken) {
                        console.log('[Firebase] Token refreshed');
                        await this._sendTokenToBackend(token);
                    }
                } catch (error) {
                    console.warn('[Firebase] Token refresh error:', error);
                }
            }, 3600000); // Every hour
            
        } catch (error) {
            console.warn('[Firebase] Token refresh setup error:', error);
        }
    }
    
    /**
     * Setup foreground message handler
     */
    _setupForegroundHandler() {
        try {
            this.messaging.onMessage((payload) => {
                console.log('[Firebase] Foreground message received:', payload);
                
                const { notification, data } = payload;
                
                // Show notification UI
                if (notification) {
                    this._showNotificationUI({
                        title: notification.title,
                        body: notification.body,
                        icon: notification.icon,
                        data: data
                    });
                }
                
                // Dispatch event for app to handle
                document.dispatchEvent(new CustomEvent('aetheria:push-received', {
                    detail: { notification, data }
                }));
            });
            
            console.log('[Firebase] Foreground message handler setup complete');
            
        } catch (error) {
            console.error('[Firebase] Foreground handler setup error:', error);
        }
    }
    
    /**
     * Show notification in UI (when app is in foreground)
     */
    _showNotificationUI(options) {
        try {
            // Create notification toast
            const notifContainer = document.querySelector('#notification-toast-container');
            if (!notifContainer) {
                console.warn('[Firebase] Notification container not found');
                return;
            }
            
            const toast = document.createElement('div');
            toast.className = 'notification-toast';
            const iconUrl = this._safeAssetUrl(options.icon);
            toast.innerHTML = `
                <div class="notification-toast-content">
                    ${iconUrl ? `<img src="${iconUrl}" alt="" class="notification-icon">` : ''}
                    <div class="notification-text">
                        <strong class="notification-title">${this._escapeHtml(options.title || 'Notification')}</strong>
                        <p class="notification-body">${this._escapeHtml(options.body || '')}</p>
                    </div>
                    <button class="notification-close" aria-label="Close">&times;</button>
                </div>
            `;
            
            // Auto-dismiss after 5 seconds
            const timeout = setTimeout(() => {
                toast.classList.add('dismissing');
                setTimeout(() => toast.remove(), 300);
            }, 5000);
            
            // Click to dismiss
            toast.querySelector('.notification-close').addEventListener('click', () => {
                clearTimeout(timeout);
                toast.classList.add('dismissing');
                setTimeout(() => toast.remove(), 300);
            });
            
            // Click notification to handle action
            toast.addEventListener('click', (e) => {
                if (e.target.closest('.notification-close')) return;
                
                if (options.data) {
                    this._handleNotificationClick(options.data);
                }
            });
            
            notifContainer.appendChild(toast);
            
            // Trigger sound and vibration
            this._playNotificationSound();
            this._vibrate();
            
        } catch (error) {
            console.error('[Firebase] Notification UI error:', error);
        }
    }
    
    /**
     * Handle notification click (deep linking)
     */
    _handleNotificationClick(data) {
        try {
            const { notification_type, sender_id, post_id, room_id } = data;
            
            let url = null;
            
            switch (notification_type) {
                case 'message':
                    url = room_id ? `/messages/room/${room_id}/` : `/messages/${sender_id}/`;
                    break;
                case 'like':
                case 'comment':
                case 'react':
                    url = `/post/${post_id}/`;
                    break;
                case 'follow':
                    url = `/profile/${sender_id}/`;
                    break;
                case 'story':
                    url = `/stories/`;
                    break;
                default:
                    url = '/';
            }
            
            if (url) {
                window.location.href = url;
            }
        } catch (error) {
            console.error('[Firebase] Notification click handler error:', error);
        }
    }
    
    /**
     * Play notification sound
     */
    _playNotificationSound() {
        try {
            // Check if sound is enabled in settings
            const soundEnabled = localStorage.getItem('aetheria_sound_enabled') !== 'false';
            if (!soundEnabled) return;
            
            if (window.aetheriaPlayNotificationSound) {
                window.aetheriaPlayNotificationSound();
                return;
            }

            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.5;
            audio.play().catch(error => console.warn('[Firebase] Could not play sound:', error));
            
        } catch (error) {
            console.warn('[Firebase] Sound playback error:', error);
        }
    }
    
    /**
     * Trigger device vibration
     */
    _vibrate() {
        try {
            if ('vibrate' in navigator) {
                // Vibrate for 200ms
                navigator.vibrate(200);
            }
        } catch (error) {
            console.warn('[Firebase] Vibration error:', error);
        }
    }
    
    /**
     * Get CSRF token from cookies
     */
    _getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * Escape HTML for safe display
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _safeAssetUrl(url) {
        if (!url) return '';
        try {
            const parsed = new URL(url, window.location.origin);
            if (!['http:', 'https:'].includes(parsed.protocol)) return '';
            if (parsed.origin !== window.location.origin && !parsed.hostname.endsWith('cloudinary.com')) return '';
            return parsed.href;
        } catch (error) {
            return '';
        }
    }
    
    /**
     * Notify error to user
     */
    _notifyError(message, error) {
        console.error(`[Firebase] ${message}:`, error);
        document.dispatchEvent(new CustomEvent('aetheria:firebase-error', {
            detail: { message, error: error.message }
        }));
    }
}

/**
 * Export for use in application
 */
window.AetheriaFirebase = AetheriaFirebaseNotifications;

/**
 * Initialize Firebase when ready (if config available)
 */
document.addEventListener('DOMContentLoaded', () => {
    // Firebase config should be set in template
    if (window.firebaseConfig) {
        const firebase = new AetheriaFirebaseNotifications(window.firebaseConfig);
        firebase.initialize();
        window.firebaseNotifications = firebase;
    } else {
        console.warn('[Firebase] No config available, skipping initialization');
    }
});
