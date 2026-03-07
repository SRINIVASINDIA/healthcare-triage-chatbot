/**
 * Frontend Configuration
 * WebSocket endpoints, feature flags, and reconnection parameters
 */

const config = {
  // WebSocket API endpoint
  websocketUrl: '',
  
  // Feature flags
  useWebSocket: true, // Toggle between WebSocket and REST mode
  
  // Reconnection parameters
  reconnection: {
    initialDelay: 1000, // 1 second
    maxDelay: 30000, // 30 seconds
    maxAttempts: 10,
    backoffMultiplier: 2
  },
  
  // REST API fallback
  restApiUrl: '/triage'
};

export default config;
