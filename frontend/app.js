// API endpoint - will be replaced with actual API Gateway URL after deployment
const API_ENDPOINT = 'https://z6tufnwdj4.execute-api.us-east-1.amazonaws.com/prod/triage';

// DOM elements
const symptomInput = document.getElementById('symptom-input');
const submitBtn = document.getElementById('submit-btn');
const conversationHistory = document.getElementById('conversation-history');
const loadingIndicator = document.getElementById('loading-indicator');

// Event listeners
submitBtn.addEventListener('click', handleSubmit);
symptomInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
    }
});

/**
 * Handle symptom submission
 */
async function handleSubmit() {
    const symptoms = symptomInput.value.trim();
    
    if (!symptoms) {
        alert('Please enter your symptoms');
        return;
    }
    
    // Disable input during processing
    submitBtn.disabled = true;
    symptomInput.disabled = true;
    
    // Display user message
    displayUserMessage(symptoms);
    
    // Clear input
    symptomInput.value = '';
    
    // Show loading indicator
    showLoading();
    
    try {
        // Call triage API
        const response = await submitSymptoms(symptoms);
        
        // Display bot response
        displayBotResponse(response);
    } catch (error) {
        displayError(error.message);
    } finally {
        // Hide loading and re-enable input
        hideLoading();
        submitBtn.disabled = false;
        symptomInput.disabled = false;
        symptomInput.focus();
    }
}

/**
 * Submit symptoms to the API
 * @param {string} symptoms - User's symptom description
 * @returns {Promise<Object>} Triage response
 */
async function submitSymptoms(symptoms) {
    // Create abort controller for 30-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    
    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symptoms }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate response structure
        if (!data.severity || !data.advice) {
            throw new Error('Invalid response format from server');
        }
        
        return data;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please check your connection and try again.');
        }
        if (error instanceof TypeError && error.message.includes('fetch')) {
            throw new Error('Network error. Please check your internet connection.');
        }
        throw error;
    }
}

/**
 * Display user message in conversation history
 * @param {string} message - User's message
 */
function displayUserMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.textContent = message;
    conversationHistory.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display bot response in conversation history
 * @param {Object} response - Triage response object
 */
function displayBotResponse(response) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    
    // Create severity badge
    const severityBadge = document.createElement('div');
    severityBadge.className = `severity-badge severity-${response.severity.toLowerCase()}`;
    severityBadge.textContent = response.severity;
    
    // Create advice text
    const adviceText = document.createElement('div');
    adviceText.className = 'advice-text';
    adviceText.textContent = response.advice;
    
    messageDiv.appendChild(severityBadge);
    messageDiv.appendChild(adviceText);
    conversationHistory.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display error message
 * @param {string} errorMessage - Error message to display
 */
function displayError(errorMessage) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = `Error: ${errorMessage}. Please try again or seek in-person medical care.`;
    conversationHistory.appendChild(errorDiv);
    scrollToBottom();
}

/**
 * Show loading indicator
 */
function showLoading() {
    loadingIndicator.classList.remove('hidden');
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

/**
 * Scroll conversation to bottom
 */
function scrollToBottom() {
    conversationHistory.parentElement.scrollTop = conversationHistory.parentElement.scrollHeight;
}

/**
 * Get color for severity level
 * @param {string} severity - Severity level (LOW, MODERATE, SEVERE)
 * @returns {string} CSS color code
 */
function getSeverityColor(severity) {
    const colors = {
        'LOW': '#4caf50',      // green
        'MODERATE': '#ff9800',  // orange
        'SEVERE': '#f44336'     // red
    };
    return colors[severity] || '#9e9e9e';
}

// Display welcome message on load
window.addEventListener('DOMContentLoaded', () => {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'message bot-message';
    welcomeDiv.innerHTML = `
        <div class="advice-text">
            <strong>Welcome to the Healthcare Triage Chatbot!</strong><br><br>
            I can help assess your symptoms and provide preliminary guidance. 
            Please describe your symptoms in detail.<br><br>
            <em>Remember: This is not a substitute for professional medical advice. 
            If you're experiencing a medical emergency, call 911 immediately.</em>
        </div>
    `;
    conversationHistory.appendChild(welcomeDiv);
});

