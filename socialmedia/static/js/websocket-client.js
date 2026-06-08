// ──────────────────────────────────────────────────────────────
// AETHERIA WebSocket Client with Reconnection & Error Handling
// Production-Ready Real-Time Communication Layer
// ──────────────────────────────────────────────────────────────

class AetheriaWebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.ws = null;
        this.isConnected = false;
        this.isConnecting = false;
        this.shouldReconnect = true;
        
        // Reconnection configuration
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 50;
        this.reconnectDelay = options.reconnectDelay || 1000; // Start at 1 second
        this.maxReconnectDelay = options.maxReconnectDelay || 30000; // Max 30 seconds
        this.reconnectMultiplier = options.reconnectMultiplier || 1.5; // Exponential backoff
        
        // Message queue for offline mode
        this.messageQueue = [];
        this.maxQueueSize = options.maxQueueSize || 100;
        
        // Handlers
        this.handlers = {
            message: options.onMessage || (() => {}),
            open: options.onOpen || (() => {}),
            close: options.onClose || (() => {}),
            error: options.onError || (() => {}),
            reconnect: options.onReconnect || (() => {}),
            reconnectFailed: options.onReconnectFailed || (() => {}),
        };
        
        // Heartbeat/ping configuration
        this.heartbeatInterval = options.heartbeatInterval || 30000; // 30 seconds
        this.heartbeatTimer = null;
        this.pongReceived = false;
    }
    
    /**
     * Connect to WebSocket server
     */
    async connect() {
        if (this.isConnecting || this.isConnected) {
            console.warn('[WebSocket] Already connecting or connected');
            return;
        }
        
        this.isConnecting = true;
        
        try {
            console.log(`[WebSocket] Connecting to ${this.url}...`);
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = this._onOpen.bind(this);
            this.ws.onmessage = this._onMessage.bind(this);
            this.ws.onclose = this._onClose.bind(this);
            this.ws.onerror = this._onError.bind(this);
            
        } catch (error) {
            console.error('[WebSocket] Connection error:', error);
            this.isConnecting = false;
            this._scheduleReconnect();
        }
    }
    
    /**
     * WebSocket opened successfully
     */
    _onOpen(event) {
        console.log('[WebSocket] Connected!');
        this.isConnected = true;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Reset delay
        
        // Start heartbeat
        this._startHeartbeat();
        
        // Flush queued messages
        this._flushMessageQueue();
        
        // Call user handler
        this.handlers.open(event);
        
        // Update UI
        this._updateConnectionStatus(true);
    }
    
    /**
     * WebSocket message received
     */
    _onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Handle heartbeat/pong
            if (data.type === 'pong') {
                this.pongReceived = true;
                return;
            }
            
            // Call user handler
            this.handlers.message(data);
            
        } catch (error) {
            console.error('[WebSocket] Message parse error:', error, event.data);
            this.handlers.error(error);
        }
    }
    
    /**
     * WebSocket closed
     */
    _onClose(event) {
        console.log('[WebSocket] Disconnected', event.code, event.reason);
        this.isConnected = false;
        this.isConnecting = false;
        
        // Stop heartbeat
        this._stopHeartbeat();
        
        // Call user handler
        this.handlers.close(event);
        
        // Update UI
        this._updateConnectionStatus(false);
        
        // Attempt reconnection
        if (this.shouldReconnect) {
            this._scheduleReconnect();
        }
    }
    
    /**
     * WebSocket error occurred
     */
    _onError(event) {
        console.error('[WebSocket] Error:', event);
        this.handlers.error(event);
    }
    
    /**
     * Schedule reconnection with exponential backoff
     */
    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WebSocket] Max reconnection attempts exceeded');
            this.handlers.reconnectFailed();
            this._updateConnectionStatus(false, 'offline');
            return;
        }
        
        this.reconnectAttempts++;
        
        // Calculate delay with exponential backoff
        const delay = Math.min(
            this.reconnectDelay * Math.pow(this.reconnectMultiplier, this.reconnectAttempts - 1),
            this.maxReconnectDelay
        );
        
        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.handlers.reconnect(this.reconnectAttempts, delay);
        
        setTimeout(() => {
            if (this.shouldReconnect && !this.isConnected && !this.isConnecting) {
                this.connect();
            }
        }, delay);
    }
    
    /**
     * Send message through WebSocket
     */
    send(data) {
        if (!data || typeof data !== 'object') {
            console.error('[WebSocket] Invalid data to send:', data);
            return;
        }
        
        if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
                console.log('[WebSocket] Message sent:', data);
            } catch (error) {
                console.error('[WebSocket] Send error:', error);
                this._queueMessage(data);
            }
        } else {
            console.warn('[WebSocket] Not connected, queueing message:', data);
            this._queueMessage(data);
        }
    }
    
    /**
     * Queue message for sending when connection is restored
     */
    _queueMessage(data) {
        if (this.messageQueue.length < this.maxQueueSize) {
            this.messageQueue.push(data);
            console.log(`[WebSocket] Message queued (${this.messageQueue.length}/${this.maxQueueSize})`);
        } else {
            console.warn('[WebSocket] Message queue full, dropping message');
        }
    }
    
    /**
     * Send all queued messages
     */
    _flushMessageQueue() {
        if (this.messageQueue.length === 0) return;
        
        console.log(`[WebSocket] Flushing ${this.messageQueue.length} queued messages...`);
        const queue = this.messageQueue.splice(0); // Get and clear queue
        
        queue.forEach(data => {
            this.send(data);
        });
    }
    
    /**
     * Start heartbeat/ping mechanism
     */
    _startHeartbeat() {
        this._stopHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            if (!this.isConnected) {
                this._stopHeartbeat();
                return;
            }
            
            // Send ping
            try {
                this.ws.send(JSON.stringify({ type: 'ping' }));
                this.pongReceived = false;
                
                // Check if pong was received within timeout
                setTimeout(() => {
                    if (!this.pongReceived && this.isConnected) {
                        console.warn('[WebSocket] Heartbeat timeout - no pong received');
                        this.ws.close();
                    }
                }, 5000);
                
            } catch (error) {
                console.error('[WebSocket] Heartbeat error:', error);
            }
        }, this.heartbeatInterval);
    }
    
    /**
     * Stop heartbeat timer
     */
    _stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Update connection status UI
     */
    _updateConnectionStatus(isConnected, status = null) {
        // Update status indicator
        const statusEl = document.querySelector('[data-ws-status]');
        if (statusEl) {
            if (isConnected) {
                statusEl.setAttribute('data-ws-status', 'connected');
                statusEl.title = 'Connected';
            } else if (this.reconnectAttempts > 0) {
                statusEl.setAttribute('data-ws-status', 'reconnecting');
                statusEl.title = `Reconnecting... (attempt ${this.reconnectAttempts})`;
            } else {
                statusEl.setAttribute('data-ws-status', status || 'disconnected');
                statusEl.title = 'Disconnected';
            }
        }
    }
    
    /**
     * Disconnect and stop reconnection attempts
     */
    disconnect() {
        console.log('[WebSocket] Disconnecting...');
        this.shouldReconnect = false;
        this._stopHeartbeat();
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.isConnected = false;
        this.isConnecting = false;
        this._updateConnectionStatus(false);
    }
    
    /**
     * Get current connection status
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            isConnecting: this.isConnecting,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length,
            url: this.url
        };
    }
}

/**
 * Global WebSocket instances for Aetheria
 */
window.AetheriaWebSockets = {
    chat: null,
    notifications: null,
    
    /**
     * Initialize WebSocket connections
     */
    initializeChatConnection(userId) {
        if (this.chat) {
            console.warn('Chat WebSocket already initialized');
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const chatUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.chat = new AetheriaWebSocketClient(chatUrl, {
            onOpen: () => {
                console.log('[Chat WS] Connected');
                document.dispatchEvent(new CustomEvent('aetheria:chat-connected'));
            },
            onMessage: (data) => {
                document.dispatchEvent(new CustomEvent('aetheria:chat-message', { detail: data }));
            },
            onClose: () => {
                console.log('[Chat WS] Closed');
                document.dispatchEvent(new CustomEvent('aetheria:chat-disconnected'));
            },
            onError: (error) => {
                console.error('[Chat WS] Error:', error);
                document.dispatchEvent(new CustomEvent('aetheria:chat-error', { detail: error }));
            },
            onReconnect: (attempt, delay) => {
                console.log(`[Chat WS] Reconnecting ${attempt}...`);
                document.dispatchEvent(new CustomEvent('aetheria:chat-reconnecting', { 
                    detail: { attempt, delay } 
                }));
            }
        });
        
        this.chat.connect();
    },
    
    /**
     * Initialize notification connection
     */
    initializeNotificationConnection() {
        if (this.notifications) {
            console.warn('Notification WebSocket already initialized');
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const notifUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.notifications = new AetheriaWebSocketClient(notifUrl, {
            onOpen: () => {
                console.log('[Notif WS] Connected');
                document.dispatchEvent(new CustomEvent('aetheria:notification-connected'));
            },
            onMessage: (data) => {
                document.dispatchEvent(new CustomEvent('aetheria:notification-message', { detail: data }));
            },
            onClose: () => {
                console.log('[Notif WS] Closed');
                document.dispatchEvent(new CustomEvent('aetheria:notification-disconnected'));
            },
            onError: (error) => {
                console.error('[Notif WS] Error:', error);
            }
        });
        
        this.notifications.connect();
    },
    
    /**
     * Disconnect all connections
     */
    disconnectAll() {
        if (this.chat) {
            this.chat.disconnect();
            this.chat = null;
        }
        if (this.notifications) {
            this.notifications.disconnect();
            this.notifications = null;
        }
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if user is authenticated
    const userElement = document.querySelector('[data-user-id]');
    if (userElement) {
        console.log('[Aetheria] Initializing WebSocket connections...');
        window.AetheriaWebSockets.initializeNotificationConnection();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    window.AetheriaWebSockets.disconnectAll();
});
