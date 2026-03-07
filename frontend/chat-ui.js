/**
 * Chat UI Component
 * Handles rendering of chat messages, typing indicators, and connection status
 */

class ChatUI {
  constructor(containerElement) {
    this.container = containerElement;
    this.messagesContainer = null;
    this.typingIndicator = null;
    this.connectionStatus = null;
    this._initializeUI();
  }

  /**
   * Initialize UI elements
   * @private
   */
  _initializeUI() {
    // Create messages container if it doesn't exist
    this.messagesContainer = this.container.querySelector('.messages-container');
    if (!this.messagesContainer) {
      this.messagesContainer = document.createElement('div');
      this.messagesContainer.className = 'messages-container';
      this.container.appendChild(this.messagesContainer);
    }

    // Create typing indicator
    this.typingIndicator = document.createElement('div');
    this.typingIndicator.className = 'typing-indicator hidden';
    this.typingIndicator.innerHTML = `
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    `;
    this.messagesContainer.appendChild(this.typingIndicator);

    // Create connection status indicator
    this.connectionStatus = this.container.querySelector('.connection-status');
    if (!this.connectionStatus) {
      this.connectionStatus = document.createElement('div');
      this.connectionStatus.className = 'connection-status';
      this.container.insertBefore(this.connectionStatus, this.container.firstChild);
    }
  }

  /**
   * Display a user message
   * @param {string} message - The message text
   */
  displayUserMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message user-message';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = message;
    
    messageElement.appendChild(bubble);
    
    // Insert before typing indicator
    this.messagesContainer.insertBefore(messageElement, this.typingIndicator);
    this.autoScrollToBottom();
  }

  /**
   * Display a bot message
   * @param {string} message - The message text
   * @param {string} severity - Optional severity level (LOW, MODERATE, SEVERE)
   */
  displayBotMessage(message, severity = null) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message bot-message';
    
    if (severity) {
      messageElement.classList.add(`severity-${severity.toLowerCase()}`);
    }
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = message;
    
    messageElement.appendChild(bubble);
    
    // Insert before typing indicator
    this.messagesContainer.insertBefore(messageElement, this.typingIndicator);
    this.autoScrollToBottom();
  }

  /**
   * Show typing indicator
   */
  showTypingIndicator() {
    this.typingIndicator.classList.remove('hidden');
    this.autoScrollToBottom();
  }

  /**
   * Hide typing indicator
   */
  hideTypingIndicator() {
    this.typingIndicator.classList.add('hidden');
  }

  /**
   * Show connection status
   * @param {string} status - Connection status (CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING)
   */
  showConnectionStatus(status) {
    const statusMessages = {
      'CONNECTING': 'Connecting...',
      'CONNECTED': 'Connected',
      'DISCONNECTED': 'Disconnected',
      'RECONNECTING': 'Reconnecting...'
    };

    const statusClasses = {
      'CONNECTING': 'status-connecting',
      'CONNECTED': 'status-connected',
      'DISCONNECTED': 'status-disconnected',
      'RECONNECTING': 'status-reconnecting'
    };

    this.connectionStatus.textContent = statusMessages[status] || status;
    this.connectionStatus.className = 'connection-status ' + (statusClasses[status] || '');

    // Hide "Connected" status after 2 seconds
    if (status === 'CONNECTED') {
      setTimeout(() => {
        this.connectionStatus.classList.add('hidden');
      }, 2000);
    } else {
      this.connectionStatus.classList.remove('hidden');
    }
  }

  /**
   * Auto-scroll to bottom of messages
   */
  autoScrollToBottom() {
    setTimeout(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }, 100);
  }

  /**
   * Render message history (for session restoration)
   * @param {Array} messageHistory - Array of message objects
   */
  renderMessageHistory(messageHistory) {
    // Clear existing messages (except typing indicator)
    const messages = this.messagesContainer.querySelectorAll('.message');
    messages.forEach(msg => msg.remove());

    // Render each message
    messageHistory.forEach(msg => {
      if (msg.role === 'user') {
        this.displayUserMessage(msg.content);
      } else if (msg.role === 'assistant') {
        this.displayBotMessage(msg.content);
      }
    });

    // Show restoration indicator
    this.showRestorationIndicator();
  }

  /**
   * Show conversation restored indicator
   * @private
   */
  showRestorationIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'restoration-indicator';
    indicator.textContent = 'Conversation restored';
    
    this.messagesContainer.insertBefore(indicator, this.messagesContainer.firstChild);
    
    // Remove after 3 seconds
    setTimeout(() => {
      indicator.remove();
    }, 3000);
  }

  /**
   * Clear all messages
   */
  clearMessages() {
    const messages = this.messagesContainer.querySelectorAll('.message, .restoration-indicator');
    messages.forEach(msg => msg.remove());
  }
}

export default ChatUI;
