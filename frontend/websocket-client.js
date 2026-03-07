/**
 * WebSocket Client for Healthcare Triage Chatbot
 * Manages WebSocket connections, reconnection logic, and message handling
 */

class WebSocketClient {
  constructor(wsUrl, onMessage, onConnectionChange) {
    this.wsUrl = wsUrl;
    this.onMessage = onMessage;
    this.onConnectionChange = onConnectionChange;
    this.ws = null;
    this.sessionId = null;
    this.connectionState = 'DISCONNECTED';
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000; // Start with 1 second
    this.maxReconnectDelay = 30000; // Max 30 seconds
  }

  /**
   * Connect to WebSocket server
   * @param {string} existingSessionId - Optional existing session ID to restore
   */
  connect(existingSessionId = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this._updateConnectionState('CONNECTING');

    // Build WebSocket URL with session ID if provided
    let url = this.wsUrl;
    if (existingSessionId) {
      url += `?sessionId=${existingSessionId}`;
      this.sessionId = existingSessionId;
    }

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this._updateConnectionState('CONNECTED');
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle connection response with session ID
          if (message.type === 'connection') {
            this.sessionId = message.sessionId;
            this._saveSessionId(message.sessionId);
            
            // If message history is included, pass it to callback
            if (message.messageHistory && this.onMessage) {
              this.onMessage({
                type: 'restore',
                messageHistory: message.messageHistory
              });
            }
          }
          
          // Pass message to callback
          if (this.onMessage) {
            this.onMessage(message);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this._updateConnectionState('DISCONNECTED');
        this._attemptReconnect();
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      this._updateConnectionState('DISCONNECTED');
      this._attemptReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._updateConnectionState('DISCONNECTED');
  }

  /**
   * Send a message through WebSocket
   * @param {string} message - The message to send
   */
  sendMessage(message) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return false;
    }

    if (!this.sessionId) {
      console.error('No session ID available');
      return false;
    }

    try {
      const payload = {
        action: 'sendMessage',
        sessionId: this.sessionId,
        message: message
      };

      this.ws.send(JSON.stringify(payload));
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      return false;
    }
  }

  /**
   * Get current session ID
   * @returns {string|null} Session ID or null
   */
  getSessionId() {
    return this.sessionId;
  }

  /**
   * Check if WebSocket is connected
   * @returns {boolean} True if connected
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Update connection state and notify callback
   * @private
   */
  _updateConnectionState(newState) {
    this.connectionState = newState;
    if (this.onConnectionChange) {
      this.onConnectionChange(newState);
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   * @private
   */
  _attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this._updateConnectionState('DISCONNECTED');
      return;
    }

    this.reconnectAttempts++;
    this._updateConnectionState('RECONNECTING');

    console.log(`Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      this.connect(this.sessionId);
    }, this.reconnectDelay);

    // Exponential backoff: double the delay, up to max
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
  }

  /**
   * Save session ID to sessionStorage
   * @private
   */
  _saveSessionId(sessionId) {
    try {
      sessionStorage.setItem('chatbot_session_id', sessionId);
    } catch (error) {
      console.error('Error saving session ID:', error);
    }
  }

  /**
   * Load session ID from sessionStorage
   * @returns {string|null} Session ID or null
   */
  static loadSessionId() {
    try {
      return sessionStorage.getItem('chatbot_session_id');
    } catch (error) {
      console.error('Error loading session ID:', error);
      return null;
    }
  }

  /**
   * Clear session ID from sessionStorage
   */
  static clearSessionId() {
    try {
      sessionStorage.removeItem('chatbot_session_id');
    } catch (error) {
      console.error('Error clearing session ID:', error);
    }
  }
}

export default WebSocketClient;
