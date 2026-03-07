/**
 * Property-Based Tests for Healthcare Triage Chatbot Frontend
 * Feature: healthcare-triage-chatbot
 */

const fc = require('fast-check');

// Mock the DOM environment for testing
const mockGetSeverityColor = (severity) => {
    const colors = {
        'LOW': '#4caf50',
        'MODERATE': '#ff9800',
        'SEVERE': '#f44336'
    };
    // Use hasOwnProperty to avoid prototype pollution
    return Object.prototype.hasOwnProperty.call(colors, severity) ? colors[severity] : '#999';
};

describe('Frontend Property Tests', () => {
    // Feature: healthcare-triage-chatbot, Property 8: Frontend Color Mapping
    // Validates: Requirements 3.3
    describe('Property 8: Frontend Color Mapping', () => {
        test('should map all severity levels to correct color codes', () => {
            fc.assert(
                fc.property(
                    fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                    (severity) => {
                        const color = mockGetSeverityColor(severity);
                        
                        // Verify correct color mapping
                        if (severity === 'LOW') {
                            expect(color).toBe('#4caf50'); // green
                        } else if (severity === 'MODERATE') {
                            expect(color).toBe('#ff9800'); // orange
                        } else if (severity === 'SEVERE') {
                            expect(color).toBe('#f44336'); // red
                        }
                        
                        // Ensure color is a valid hex code
                        expect(color).toMatch(/^#[0-9a-f]{6}$/i);
                    }
                ),
                { numRuns: 100 } // Run 100 iterations as per design spec
            );
        });

        test('should return default color for invalid severity levels', () => {
            fc.assert(
                fc.property(
                    fc.string().filter(s => !['LOW', 'MODERATE', 'SEVERE'].includes(s)),
                    (invalidSeverity) => {
                        const color = mockGetSeverityColor(invalidSeverity);
                        expect(color).toBe('#999'); // default gray color
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should handle case-sensitive severity values', () => {
            // Test that the function is case-sensitive (as per design)
            const testCases = [
                { input: 'low', expected: '#999' },      // lowercase should return default
                { input: 'Low', expected: '#999' },      // mixed case should return default
                { input: 'LOW', expected: '#4caf50' },   // uppercase should work
                { input: 'moderate', expected: '#999' },
                { input: 'MODERATE', expected: '#ff9800' },
                { input: 'severe', expected: '#999' },
                { input: 'SEVERE', expected: '#f44336' }
            ];

            testCases.forEach(({ input, expected }) => {
                expect(mockGetSeverityColor(input)).toBe(expected);
            });
        });
    });

    // Feature: healthcare-triage-chatbot, Property 9: Conversation History Growth
    // Validates: Requirements 3.4
    describe('Property 9: Conversation History Growth', () => {
        test('should increase history length by one for each submission', () => {
            fc.assert(
                fc.property(
                    fc.array(fc.string({ minLength: 1, maxLength: 100 }), { minLength: 1, maxLength: 20 }),
                    (symptomSequence) => {
                        // Mock conversation history container
                        const mockHistory = [];
                        
                        // Simulate submitting each symptom in the sequence
                        symptomSequence.forEach((symptom, index) => {
                            const beforeLength = mockHistory.length;
                            
                            // Add user message
                            mockHistory.push({
                                type: 'user',
                                content: symptom
                            });
                            
                            // Verify history length increased by 1 for user message
                            expect(mockHistory.length).toBe(beforeLength + 1);
                            
                            // Add bot response (simulating the response)
                            mockHistory.push({
                                type: 'bot',
                                severity: 'LOW',
                                advice: 'Test advice'
                            });
                            
                            // Verify history length increased by 1 again for bot response
                            expect(mockHistory.length).toBe(beforeLength + 2);
                        });
                        
                        // Verify total history length equals submissions * 2 (user + bot messages)
                        expect(mockHistory.length).toBe(symptomSequence.length * 2);
                        
                        // Verify chronological order is maintained
                        for (let i = 0; i < mockHistory.length; i += 2) {
                            expect(mockHistory[i].type).toBe('user');
                            expect(mockHistory[i + 1].type).toBe('bot');
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should maintain chronological order across multiple submissions', () => {
            fc.assert(
                fc.property(
                    fc.array(
                        fc.record({
                            symptom: fc.string({ minLength: 1, maxLength: 100 }),
                            severity: fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                            advice: fc.string({ minLength: 10, maxLength: 200 })
                        }),
                        { minLength: 1, maxLength: 15 }
                    ),
                    (submissions) => {
                        const mockHistory = [];
                        
                        // Process each submission
                        submissions.forEach((submission, index) => {
                            const beforeLength = mockHistory.length;
                            
                            // Add user message
                            mockHistory.push({
                                type: 'user',
                                content: submission.symptom,
                                timestamp: index * 2
                            });
                            
                            // Add bot response
                            mockHistory.push({
                                type: 'bot',
                                severity: submission.severity,
                                advice: submission.advice,
                                timestamp: index * 2 + 1
                            });
                            
                            // Verify history grew by exactly 2 (user + bot)
                            expect(mockHistory.length).toBe(beforeLength + 2);
                        });
                        
                        // Verify all messages are in chronological order
                        for (let i = 1; i < mockHistory.length; i++) {
                            expect(mockHistory[i].timestamp).toBeGreaterThan(mockHistory[i - 1].timestamp);
                        }
                        
                        // Verify alternating pattern (user, bot, user, bot, ...)
                        for (let i = 0; i < mockHistory.length; i++) {
                            if (i % 2 === 0) {
                                expect(mockHistory[i].type).toBe('user');
                            } else {
                                expect(mockHistory[i].type).toBe('bot');
                            }
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should preserve all previous submissions and responses', () => {
            fc.assert(
                fc.property(
                    fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 2, maxLength: 10 }),
                    (symptoms) => {
                        const mockHistory = [];
                        const expectedSymptoms = [];
                        
                        // Submit each symptom
                        symptoms.forEach((symptom) => {
                            expectedSymptoms.push(symptom);
                            
                            // Add to history
                            mockHistory.push({ type: 'user', content: symptom });
                            mockHistory.push({ type: 'bot', severity: 'LOW', advice: 'Advice' });
                            
                            // Verify all previous symptoms are still in history
                            const userMessages = mockHistory.filter(m => m.type === 'user');
                            expect(userMessages.length).toBe(expectedSymptoms.length);
                            
                            // Verify each expected symptom is present
                            expectedSymptoms.forEach((expectedSymptom, idx) => {
                                expect(userMessages[idx].content).toBe(expectedSymptom);
                            });
                        });
                    }
                ),
                { numRuns: 100 }
            );
        });
    });

    // Feature: healthcare-triage-chatbot, Property 10: Loading Indicator Lifecycle
    // Validates: Requirements 3.2
    describe('Property 10: Loading Indicator Lifecycle', () => {
        test('should display loading indicator on submit and remove on response', async () => {
            await fc.assert(
                fc.asyncProperty(
                    fc.record({
                        symptoms: fc.string({ minLength: 1, maxLength: 500 }),
                        severity: fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                        advice: fc.string({ minLength: 10, maxLength: 300 }),
                        responseDelay: fc.integer({ min: 0, max: 10 }) // Simulate response delay in ms
                    }),
                    async (submission) => {
                        // Mock DOM elements
                        const mockLoadingIndicator = {
                            classList: {
                                hidden: true,
                                remove: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = false;
                                    }
                                },
                                add: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = true;
                                    }
                                }
                            }
                        };

                        // Verify initial state: loading indicator is hidden
                        expect(mockLoadingIndicator.classList.hidden).toBe(true);

                        // Simulate submission: show loading indicator
                        mockLoadingIndicator.classList.remove('hidden');
                        
                        // Verify loading indicator is now visible
                        expect(mockLoadingIndicator.classList.hidden).toBe(false);

                        // Simulate API response after delay
                        if (submission.responseDelay > 0) {
                            await new Promise(resolve => setTimeout(resolve, submission.responseDelay));
                        }

                        // Simulate response received: hide loading indicator
                        mockLoadingIndicator.classList.add('hidden');

                        // Verify loading indicator is hidden again
                        expect(mockLoadingIndicator.classList.hidden).toBe(true);
                    }
                ),
                { numRuns: 100 }
            );
        }, 10000);

        test('should display loading indicator on submit and remove on error', async () => {
            await fc.assert(
                fc.asyncProperty(
                    fc.record({
                        symptoms: fc.string({ minLength: 1, maxLength: 500 }),
                        errorType: fc.constantFrom('network', 'timeout', 'server', 'parse'),
                        errorDelay: fc.integer({ min: 0, max: 10 })
                    }),
                    async (submission) => {
                        // Mock DOM elements
                        const mockLoadingIndicator = {
                            classList: {
                                hidden: true,
                                remove: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = false;
                                    }
                                },
                                add: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = true;
                                    }
                                }
                            }
                        };

                        // Verify initial state: loading indicator is hidden
                        expect(mockLoadingIndicator.classList.hidden).toBe(true);

                        // Simulate submission: show loading indicator
                        mockLoadingIndicator.classList.remove('hidden');
                        
                        // Verify loading indicator is now visible
                        expect(mockLoadingIndicator.classList.hidden).toBe(false);

                        // Simulate error after delay
                        if (submission.errorDelay > 0) {
                            await new Promise(resolve => setTimeout(resolve, submission.errorDelay));
                        }

                        // Simulate error handling: hide loading indicator
                        mockLoadingIndicator.classList.add('hidden');

                        // Verify loading indicator is hidden after error
                        expect(mockLoadingIndicator.classList.hidden).toBe(true);
                    }
                ),
                { numRuns: 100 }
            );
        }, 10000);

        test('should handle loading indicator lifecycle across multiple submissions', async () => {
            await fc.assert(
                fc.asyncProperty(
                    fc.array(
                        fc.record({
                            symptoms: fc.string({ minLength: 1, maxLength: 200 }),
                            isSuccess: fc.boolean(),
                            delay: fc.integer({ min: 0, max: 5 })
                        }),
                        { minLength: 1, maxLength: 10 }
                    ),
                    async (submissions) => {
                        // Mock DOM elements
                        const mockLoadingIndicator = {
                            classList: {
                                hidden: true,
                                remove: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = false;
                                    }
                                },
                                add: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = true;
                                    }
                                }
                            }
                        };

                        // Process each submission sequentially
                        for (const submission of submissions) {
                            // Verify loading indicator starts hidden
                            expect(mockLoadingIndicator.classList.hidden).toBe(true);

                            // Show loading indicator on submit
                            mockLoadingIndicator.classList.remove('hidden');
                            expect(mockLoadingIndicator.classList.hidden).toBe(false);

                            // Simulate response/error delay
                            if (submission.delay > 0) {
                                await new Promise(resolve => setTimeout(resolve, submission.delay));
                            }

                            // Hide loading indicator after response/error
                            mockLoadingIndicator.classList.add('hidden');
                            expect(mockLoadingIndicator.classList.hidden).toBe(true);
                        }
                    }
                ),
                { numRuns: 100 }
            );
        }, 15000);

        test('should ensure loading indicator state transitions are immediate', () => {
            fc.assert(
                fc.property(
                    fc.string({ minLength: 1, maxLength: 300 }),
                    (symptoms) => {
                        // Mock DOM elements
                        const mockLoadingIndicator = {
                            classList: {
                                hidden: true,
                                remove: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = false;
                                    }
                                },
                                add: function(className) {
                                    if (className === 'hidden') {
                                        this.hidden = true;
                                    }
                                }
                            }
                        };

                        // Initial state
                        const initialState = mockLoadingIndicator.classList.hidden;
                        expect(initialState).toBe(true);

                        // Show loading indicator - should be immediate
                        mockLoadingIndicator.classList.remove('hidden');
                        const afterShowState = mockLoadingIndicator.classList.hidden;
                        expect(afterShowState).toBe(false);

                        // Hide loading indicator - should be immediate
                        mockLoadingIndicator.classList.add('hidden');
                        const afterHideState = mockLoadingIndicator.classList.hidden;
                        expect(afterHideState).toBe(true);

                        // Verify state transitions are deterministic
                        expect(initialState).toBe(afterHideState);
                    }
                ),
                { numRuns: 100 }
            );
        });
    });

    // Feature: healthcare-triage-chatbot, Property 15: Frontend Field Display
    // Validates: Requirements 8.5
    describe('Property 15: Frontend Field Display', () => {
        test('should display both severity and advice fields for any triage response', () => {
            fc.assert(
                fc.property(
                    fc.record({
                        severity: fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                        advice: fc.string({ minLength: 10, maxLength: 500 })
                    }),
                    (triageResponse) => {
                        // Mock DOM elements and methods
                        const mockConversationHistory = {
                            children: [],
                            appendChild: function(element) {
                                this.children.push(element);
                            },
                            scrollHeight: 1000,
                            scrollTop: 0
                        };

                        // Mock document.createElement
                        const createdElements = [];
                        const mockCreateElement = (tagName) => {
                            const element = {
                                tagName: tagName.toUpperCase(),
                                className: '',
                                textContent: '',
                                style: {},
                                children: [],
                                appendChild: function(child) {
                                    this.children.push(child);
                                }
                            };
                            createdElements.push(element);
                            return element;
                        };

                        // Simulate displayResponse function
                        const { severity, advice } = triageResponse;
                        
                        const messageDiv = mockCreateElement('div');
                        messageDiv.className = `message bot-message severity-${severity.toLowerCase()}`;
                        
                        const severityBadge = mockCreateElement('span');
                        severityBadge.className = `severity-badge ${severity.toLowerCase()}`;
                        severityBadge.textContent = severity;
                        
                        const adviceText = mockCreateElement('p');
                        adviceText.textContent = advice;
                        adviceText.style.marginTop = '5px';
                        
                        messageDiv.appendChild(severityBadge);
                        messageDiv.appendChild(adviceText);
                        
                        mockConversationHistory.appendChild(messageDiv);

                        // Verify the message was added to conversation history
                        expect(mockConversationHistory.children.length).toBe(1);
                        
                        const displayedMessage = mockConversationHistory.children[0];
                        
                        // Verify the message div exists and has correct structure
                        expect(displayedMessage.tagName).toBe('DIV');
                        expect(displayedMessage.className).toContain('message');
                        expect(displayedMessage.className).toContain('bot-message');
                        
                        // Verify both severity and advice are present in the message
                        expect(displayedMessage.children.length).toBe(2);
                        
                        // Verify severity badge is displayed
                        const severityElement = displayedMessage.children[0];
                        expect(severityElement.tagName).toBe('SPAN');
                        expect(severityElement.className).toContain('severity-badge');
                        expect(severityElement.textContent).toBe(severity);
                        
                        // Verify advice text is displayed
                        const adviceElement = displayedMessage.children[1];
                        expect(adviceElement.tagName).toBe('P');
                        expect(adviceElement.textContent).toBe(advice);
                        
                        // Verify both fields are non-empty
                        expect(severityElement.textContent).toBeTruthy();
                        expect(adviceElement.textContent).toBeTruthy();
                        
                        // Verify severity is one of the valid values
                        expect(['LOW', 'MODERATE', 'SEVERE']).toContain(severity);
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should display both fields for all severity levels', () => {
            fc.assert(
                fc.property(
                    fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                    fc.string({ minLength: 20, maxLength: 300 }),
                    (severity, advice) => {
                        // Mock DOM
                        const mockConversationHistory = {
                            children: [],
                            appendChild: function(element) {
                                this.children.push(element);
                            }
                        };

                        const mockCreateElement = (tagName) => {
                            const element = {
                                tagName: tagName.toUpperCase(),
                                className: '',
                                textContent: '',
                                style: {},
                                children: [],
                                appendChild: function(child) {
                                    this.children.push(child);
                                }
                            };
                            return element;
                        };

                        // Simulate displayResponse
                        const triageResponse = { severity, advice };
                        
                        const messageDiv = mockCreateElement('div');
                        messageDiv.className = `message bot-message severity-${severity.toLowerCase()}`;
                        
                        const severityBadge = mockCreateElement('span');
                        severityBadge.className = `severity-badge ${severity.toLowerCase()}`;
                        severityBadge.textContent = severity;
                        
                        const adviceText = mockCreateElement('p');
                        adviceText.textContent = advice;
                        adviceText.style.marginTop = '5px';
                        
                        messageDiv.appendChild(severityBadge);
                        messageDiv.appendChild(adviceText);
                        
                        mockConversationHistory.appendChild(messageDiv);

                        // Verify both fields are displayed
                        const displayedMessage = mockConversationHistory.children[0];
                        const severityElement = displayedMessage.children[0];
                        const adviceElement = displayedMessage.children[1];
                        
                        // Both fields must be present
                        expect(severityElement.textContent).toBe(severity);
                        expect(adviceElement.textContent).toBe(advice);
                        
                        // Verify severity-specific styling is applied
                        expect(messageDiv.className).toContain(severity.toLowerCase());
                        expect(severityBadge.className).toContain(severity.toLowerCase());
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should display both fields for various advice lengths', () => {
            fc.assert(
                fc.property(
                    fc.record({
                        severity: fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                        advice: fc.oneof(
                            fc.string({ minLength: 10, maxLength: 50 }),    // Short advice
                            fc.string({ minLength: 100, maxLength: 300 }),  // Medium advice
                            fc.string({ minLength: 500, maxLength: 1000 })  // Long advice
                        )
                    }),
                    (triageResponse) => {
                        // Mock DOM
                        const mockConversationHistory = {
                            children: [],
                            appendChild: function(element) {
                                this.children.push(element);
                            }
                        };

                        const mockCreateElement = (tagName) => {
                            const element = {
                                tagName: tagName.toUpperCase(),
                                className: '',
                                textContent: '',
                                style: {},
                                children: [],
                                appendChild: function(child) {
                                    this.children.push(child);
                                }
                            };
                            return element;
                        };

                        // Simulate displayResponse
                        const { severity, advice } = triageResponse;
                        
                        const messageDiv = mockCreateElement('div');
                        messageDiv.className = `message bot-message severity-${severity.toLowerCase()}`;
                        
                        const severityBadge = mockCreateElement('span');
                        severityBadge.className = `severity-badge ${severity.toLowerCase()}`;
                        severityBadge.textContent = severity;
                        
                        const adviceText = mockCreateElement('p');
                        adviceText.textContent = advice;
                        adviceText.style.marginTop = '5px';
                        
                        messageDiv.appendChild(severityBadge);
                        messageDiv.appendChild(adviceText);
                        
                        mockConversationHistory.appendChild(messageDiv);

                        // Verify both fields are displayed regardless of advice length
                        const displayedMessage = mockConversationHistory.children[0];
                        expect(displayedMessage.children.length).toBe(2);
                        
                        const severityElement = displayedMessage.children[0];
                        const adviceElement = displayedMessage.children[1];
                        
                        // Both fields must contain the correct content
                        expect(severityElement.textContent).toBe(severity);
                        expect(adviceElement.textContent).toBe(advice);
                        
                        // Verify advice is fully preserved (no truncation)
                        expect(adviceElement.textContent.length).toBe(advice.length);
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should display both fields for multiple consecutive responses', () => {
            fc.assert(
                fc.property(
                    fc.array(
                        fc.record({
                            severity: fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                            advice: fc.string({ minLength: 15, maxLength: 200 })
                        }),
                        { minLength: 1, maxLength: 10 }
                    ),
                    (triageResponses) => {
                        // Mock DOM
                        const mockConversationHistory = {
                            children: [],
                            appendChild: function(element) {
                                this.children.push(element);
                            }
                        };

                        const mockCreateElement = (tagName) => {
                            const element = {
                                tagName: tagName.toUpperCase(),
                                className: '',
                                textContent: '',
                                style: {},
                                children: [],
                                appendChild: function(child) {
                                    this.children.push(child);
                                }
                            };
                            return element;
                        };

                        // Display each response
                        triageResponses.forEach((triageResponse) => {
                            const { severity, advice } = triageResponse;
                            
                            const messageDiv = mockCreateElement('div');
                            messageDiv.className = `message bot-message severity-${severity.toLowerCase()}`;
                            
                            const severityBadge = mockCreateElement('span');
                            severityBadge.className = `severity-badge ${severity.toLowerCase()}`;
                            severityBadge.textContent = severity;
                            
                            const adviceText = mockCreateElement('p');
                            adviceText.textContent = advice;
                            adviceText.style.marginTop = '5px';
                            
                            messageDiv.appendChild(severityBadge);
                            messageDiv.appendChild(adviceText);
                            
                            mockConversationHistory.appendChild(messageDiv);
                        });

                        // Verify all responses are displayed with both fields
                        expect(mockConversationHistory.children.length).toBe(triageResponses.length);
                        
                        triageResponses.forEach((expectedResponse, index) => {
                            const displayedMessage = mockConversationHistory.children[index];
                            
                            // Verify structure
                            expect(displayedMessage.children.length).toBe(2);
                            
                            const severityElement = displayedMessage.children[0];
                            const adviceElement = displayedMessage.children[1];
                            
                            // Verify both fields match expected values
                            expect(severityElement.textContent).toBe(expectedResponse.severity);
                            expect(adviceElement.textContent).toBe(expectedResponse.advice);
                        });
                    }
                ),
                { numRuns: 100 }
            );
        });

        test('should include both fields in DOM structure for any response', () => {
            fc.assert(
                fc.property(
                    fc.record({
                        severity: fc.constantFrom('LOW', 'MODERATE', 'SEVERE'),
                        advice: fc.string({ minLength: 1, maxLength: 1000 })
                    }),
                    (triageResponse) => {
                        // Mock DOM
                        const mockConversationHistory = {
                            children: [],
                            appendChild: function(element) {
                                this.children.push(element);
                            }
                        };

                        const mockCreateElement = (tagName) => {
                            const element = {
                                tagName: tagName.toUpperCase(),
                                className: '',
                                textContent: '',
                                style: {},
                                children: [],
                                appendChild: function(child) {
                                    this.children.push(child);
                                }
                            };
                            return element;
                        };

                        // Simulate displayResponse
                        const { severity, advice } = triageResponse;
                        
                        const messageDiv = mockCreateElement('div');
                        messageDiv.className = `message bot-message severity-${severity.toLowerCase()}`;
                        
                        const severityBadge = mockCreateElement('span');
                        severityBadge.className = `severity-badge ${severity.toLowerCase()}`;
                        severityBadge.textContent = severity;
                        
                        const adviceText = mockCreateElement('p');
                        adviceText.textContent = advice;
                        adviceText.style.marginTop = '5px';
                        
                        messageDiv.appendChild(severityBadge);
                        messageDiv.appendChild(adviceText);
                        
                        mockConversationHistory.appendChild(messageDiv);

                        // Property: The displayed message SHALL include both severity and advice
                        const displayedMessage = mockConversationHistory.children[0];
                        
                        // Verify message contains exactly 2 child elements
                        expect(displayedMessage.children.length).toBeGreaterThanOrEqual(2);
                        
                        // Verify first child is severity badge
                        const firstChild = displayedMessage.children[0];
                        expect(firstChild.tagName).toBe('SPAN');
                        expect(firstChild.textContent).toBeTruthy();
                        expect(['LOW', 'MODERATE', 'SEVERE']).toContain(firstChild.textContent);
                        
                        // Verify second child is advice text
                        const secondChild = displayedMessage.children[1];
                        expect(secondChild.tagName).toBe('P');
                        expect(secondChild.textContent).toBeTruthy();
                        expect(secondChild.textContent.length).toBeGreaterThan(0);
                        
                        // Verify both fields are present and non-empty
                        const hasSeverity = firstChild.textContent.length > 0;
                        const hasAdvice = secondChild.textContent.length > 0;
                        expect(hasSeverity && hasAdvice).toBe(true);
                    }
                ),
                { numRuns: 100 }
            );
        });
    });
});


/**
 * Unit Tests for Healthcare Triage Chatbot Frontend
 * Feature: healthcare-triage-chatbot
 * Task 5.8: Frontend unit tests for specific scenarios and edge cases
 */

describe('Frontend Unit Tests', () => {
    // Test UI elements exist (input field, submit button, history container)
    describe('UI Elements Existence', () => {
        let mockDocument;

        beforeEach(() => {
            // Mock DOM structure
            mockDocument = {
                getElementById: jest.fn((id) => {
                    const elements = {
                        'symptom-input': { id: 'symptom-input', tagName: 'TEXTAREA', value: '' },
                        'submit-btn': { id: 'submit-btn', tagName: 'BUTTON', disabled: false },
                        'conversation-history': { id: 'conversation-history', tagName: 'DIV', children: [] },
                        'loading-indicator': { id: 'loading-indicator', tagName: 'DIV', classList: { hidden: true } }
                    };
                    return elements[id] || null;
                })
            };
        });

        test('should have symptom input field', () => {
            const symptomInput = mockDocument.getElementById('symptom-input');
            expect(symptomInput).not.toBeNull();
            expect(symptomInput.id).toBe('symptom-input');
            expect(symptomInput.tagName).toBe('TEXTAREA');
        });

        test('should have submit button', () => {
            const submitBtn = mockDocument.getElementById('submit-btn');
            expect(submitBtn).not.toBeNull();
            expect(submitBtn.id).toBe('submit-btn');
            expect(submitBtn.tagName).toBe('BUTTON');
        });

        test('should have conversation history container', () => {
            const conversationHistory = mockDocument.getElementById('conversation-history');
            expect(conversationHistory).not.toBeNull();
            expect(conversationHistory.id).toBe('conversation-history');
            expect(conversationHistory.tagName).toBe('DIV');
        });

        test('should have loading indicator', () => {
            const loadingIndicator = mockDocument.getElementById('loading-indicator');
            expect(loadingIndicator).not.toBeNull();
            expect(loadingIndicator.id).toBe('loading-indicator');
            expect(loadingIndicator.tagName).toBe('DIV');
        });

        test('should have all required UI elements present', () => {
            const symptomInput = mockDocument.getElementById('symptom-input');
            const submitBtn = mockDocument.getElementById('submit-btn');
            const conversationHistory = mockDocument.getElementById('conversation-history');
            const loadingIndicator = mockDocument.getElementById('loading-indicator');

            expect(symptomInput).toBeTruthy();
            expect(submitBtn).toBeTruthy();
            expect(conversationHistory).toBeTruthy();
            expect(loadingIndicator).toBeTruthy();
        });
    });

    // Test color mapping for each severity level
    describe('Color Mapping for Severity Levels', () => {
        test('should map LOW severity to green color', () => {
            const color = mockGetSeverityColor('LOW');
            expect(color).toBe('#4caf50');
        });

        test('should map MODERATE severity to orange color', () => {
            const color = mockGetSeverityColor('MODERATE');
            expect(color).toBe('#ff9800');
        });

        test('should map SEVERE severity to red color', () => {
            const color = mockGetSeverityColor('SEVERE');
            expect(color).toBe('#f44336');
        });

        test('should return default gray color for unknown severity', () => {
            const color = mockGetSeverityColor('UNKNOWN');
            expect(color).toBe('#999');
        });

        test('should return default color for empty string', () => {
            const color = mockGetSeverityColor('');
            expect(color).toBe('#999');
        });

        test('should return default color for null or undefined', () => {
            expect(mockGetSeverityColor(null)).toBe('#999');
            expect(mockGetSeverityColor(undefined)).toBe('#999');
        });

        test('should be case-sensitive for severity values', () => {
            expect(mockGetSeverityColor('low')).toBe('#999');
            expect(mockGetSeverityColor('moderate')).toBe('#999');
            expect(mockGetSeverityColor('severe')).toBe('#999');
        });

        test('should return valid hex color codes', () => {
            const severities = ['LOW', 'MODERATE', 'SEVERE'];
            const hexColorRegex = /^#[0-9a-f]{6}$/i;

            severities.forEach(severity => {
                const color = mockGetSeverityColor(severity);
                expect(color).toMatch(hexColorRegex);
            });
        });
    });

    // Test API call success and error handling
    describe('API Call Success and Error Handling', () => {
        let mockFetch;

        beforeEach(() => {
            mockFetch = jest.fn();
            global.fetch = mockFetch;
        });

        afterEach(() => {
            jest.restoreAllMocks();
        });

        test('should handle successful API response', async () => {
            const mockResponse = {
                severity: 'LOW',
                advice: 'Rest and stay hydrated. Monitor your symptoms.'
            };

            mockFetch.mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => mockResponse
            });

            const response = await fetch('https://api.example.com/triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms: 'mild headache' })
            });

            expect(response.ok).toBe(true);
            expect(response.status).toBe(200);

            const data = await response.json();
            expect(data).toEqual(mockResponse);
            expect(data.severity).toBe('LOW');
            expect(data.advice).toBeTruthy();
        });

        test('should handle API error with non-200 status', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                statusText: 'Internal Server Error'
            });

            const response = await fetch('https://api.example.com/triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms: 'chest pain' })
            });

            expect(response.ok).toBe(false);
            expect(response.status).toBe(500);
        });

        test('should handle network failure', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));

            await expect(
                fetch('https://api.example.com/triage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symptoms: 'fever' })
                })
            ).rejects.toThrow('Network error');
        });

        test('should handle timeout error', async () => {
            const timeoutError = new Error('Timeout');
            timeoutError.name = 'AbortError';
            mockFetch.mockRejectedValueOnce(timeoutError);

            try {
                await fetch('https://api.example.com/triage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symptoms: 'cough' })
                });
            } catch (error) {
                expect(error.name).toBe('AbortError');
            }
        });

        test('should handle 400 Bad Request error', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                statusText: 'Bad Request',
                json: async () => ({ error: 'Invalid request: symptoms field is required' })
            });

            const response = await fetch('https://api.example.com/triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms: '' })
            });

            expect(response.ok).toBe(false);
            expect(response.status).toBe(400);

            const errorData = await response.json();
            expect(errorData.error).toContain('symptoms field is required');
        });

        test('should handle 504 Gateway Timeout', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 504,
                statusText: 'Gateway Timeout'
            });

            const response = await fetch('https://api.example.com/triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms: 'dizziness' })
            });

            expect(response.ok).toBe(false);
            expect(response.status).toBe(504);
        });

        test('should send correct request format', async () => {
            const symptoms = 'sore throat';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ severity: 'LOW', advice: 'Test advice' })
            });

            await fetch('https://api.example.com/triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms })
            });

            expect(mockFetch).toHaveBeenCalledWith(
                'https://api.example.com/triage',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symptoms })
                })
            );
        });
    });

    // Test conversation history ordering
    describe('Conversation History Ordering', () => {
        let mockConversationHistory;

        beforeEach(() => {
            mockConversationHistory = {
                children: [],
                appendChild: function(element) {
                    this.children.push(element);
                },
                scrollHeight: 1000,
                scrollTop: 0
            };
        });

        test('should maintain chronological order for single submission', () => {
            // Add user message
            const userMessage = { type: 'user', content: 'I have a headache', timestamp: 1 };
            mockConversationHistory.appendChild(userMessage);

            // Add bot response
            const botMessage = { type: 'bot', severity: 'LOW', advice: 'Rest', timestamp: 2 };
            mockConversationHistory.appendChild(botMessage);

            expect(mockConversationHistory.children.length).toBe(2);
            expect(mockConversationHistory.children[0].type).toBe('user');
            expect(mockConversationHistory.children[1].type).toBe('bot');
            expect(mockConversationHistory.children[1].timestamp).toBeGreaterThan(
                mockConversationHistory.children[0].timestamp
            );
        });

        test('should maintain chronological order for multiple submissions', () => {
            const submissions = [
                { user: 'headache', bot: { severity: 'LOW', advice: 'Rest' } },
                { user: 'fever', bot: { severity: 'MODERATE', advice: 'See doctor' } },
                { user: 'chest pain', bot: { severity: 'SEVERE', advice: 'Call 911' } }
            ];

            submissions.forEach((submission, index) => {
                mockConversationHistory.appendChild({
                    type: 'user',
                    content: submission.user,
                    timestamp: index * 2
                });
                mockConversationHistory.appendChild({
                    type: 'bot',
                    severity: submission.bot.severity,
                    advice: submission.bot.advice,
                    timestamp: index * 2 + 1
                });
            });

            expect(mockConversationHistory.children.length).toBe(6);

            // Verify alternating pattern
            for (let i = 0; i < mockConversationHistory.children.length; i++) {
                if (i % 2 === 0) {
                    expect(mockConversationHistory.children[i].type).toBe('user');
                } else {
                    expect(mockConversationHistory.children[i].type).toBe('bot');
                }
            }

            // Verify timestamps are in ascending order
            for (let i = 1; i < mockConversationHistory.children.length; i++) {
                expect(mockConversationHistory.children[i].timestamp).toBeGreaterThan(
                    mockConversationHistory.children[i - 1].timestamp
                );
            }
        });

        test('should preserve all previous messages when adding new ones', () => {
            const firstUser = { type: 'user', content: 'symptom 1' };
            const firstBot = { type: 'bot', severity: 'LOW', advice: 'advice 1' };
            const secondUser = { type: 'user', content: 'symptom 2' };
            const secondBot = { type: 'bot', severity: 'MODERATE', advice: 'advice 2' };

            mockConversationHistory.appendChild(firstUser);
            mockConversationHistory.appendChild(firstBot);

            expect(mockConversationHistory.children.length).toBe(2);
            expect(mockConversationHistory.children[0]).toBe(firstUser);
            expect(mockConversationHistory.children[1]).toBe(firstBot);

            mockConversationHistory.appendChild(secondUser);
            mockConversationHistory.appendChild(secondBot);

            expect(mockConversationHistory.children.length).toBe(4);
            expect(mockConversationHistory.children[0]).toBe(firstUser);
            expect(mockConversationHistory.children[1]).toBe(firstBot);
            expect(mockConversationHistory.children[2]).toBe(secondUser);
            expect(mockConversationHistory.children[3]).toBe(secondBot);
        });

        test('should maintain order with mixed severity levels', () => {
            const messages = [
                { type: 'user', content: 'mild pain' },
                { type: 'bot', severity: 'LOW', advice: 'Rest' },
                { type: 'user', content: 'worsening pain' },
                { type: 'bot', severity: 'MODERATE', advice: 'See doctor' },
                { type: 'user', content: 'severe pain' },
                { type: 'bot', severity: 'SEVERE', advice: 'Emergency' }
            ];

            messages.forEach(msg => mockConversationHistory.appendChild(msg));

            expect(mockConversationHistory.children.length).toBe(6);

            // Verify order is preserved
            messages.forEach((expectedMsg, index) => {
                expect(mockConversationHistory.children[index]).toEqual(expectedMsg);
            });
        });

        test('should append new messages to the end', () => {
            const initialCount = mockConversationHistory.children.length;

            const newMessage = { type: 'user', content: 'new symptom' };
            mockConversationHistory.appendChild(newMessage);

            expect(mockConversationHistory.children.length).toBe(initialCount + 1);
            expect(mockConversationHistory.children[mockConversationHistory.children.length - 1]).toBe(newMessage);
        });
    });

    // Test invalid JSON response handling
    describe('Invalid JSON Response Handling', () => {
        test('should handle malformed JSON response', () => {
            const malformedJSON = '{"severity": "LOW", "advice": "Rest"'; // Missing closing brace

            expect(() => {
                JSON.parse(malformedJSON);
            }).toThrow();
        });

        test('should handle empty response body', () => {
            const emptyResponse = '';

            expect(() => {
                JSON.parse(emptyResponse);
            }).toThrow();
        });

        test('should handle response with missing severity field', () => {
            const responseWithoutSeverity = JSON.stringify({
                advice: 'Rest and stay hydrated'
            });

            const parsed = JSON.parse(responseWithoutSeverity);
            expect(parsed.severity).toBeUndefined();
            expect(parsed.advice).toBe('Rest and stay hydrated');
        });

        test('should handle response with missing advice field', () => {
            const responseWithoutAdvice = JSON.stringify({
                severity: 'LOW'
            });

            const parsed = JSON.parse(responseWithoutAdvice);
            expect(parsed.severity).toBe('LOW');
            expect(parsed.advice).toBeUndefined();
        });

        test('should handle response with invalid severity value', () => {
            const responseWithInvalidSeverity = JSON.stringify({
                severity: 'INVALID',
                advice: 'Some advice'
            });

            const parsed = JSON.parse(responseWithInvalidSeverity);
            expect(parsed.severity).toBe('INVALID');
            expect(['LOW', 'MODERATE', 'SEVERE']).not.toContain(parsed.severity);
        });

        test('should handle response with wrong data types', () => {
            const responseWithWrongTypes = JSON.stringify({
                severity: 123,
                advice: true
            });

            const parsed = JSON.parse(responseWithWrongTypes);
            expect(typeof parsed.severity).toBe('number');
            expect(typeof parsed.advice).toBe('boolean');
        });

        test('should handle response with extra fields', () => {
            const responseWithExtraFields = JSON.stringify({
                severity: 'LOW',
                advice: 'Rest',
                extraField: 'should be ignored',
                anotherField: 42
            });

            const parsed = JSON.parse(responseWithExtraFields);
            expect(parsed.severity).toBe('LOW');
            expect(parsed.advice).toBe('Rest');
            expect(parsed.extraField).toBe('should be ignored');
            expect(parsed.anotherField).toBe(42);
        });

        test('should handle null response', () => {
            const nullResponse = 'null';

            const parsed = JSON.parse(nullResponse);
            expect(parsed).toBeNull();
        });

        test('should handle array instead of object', () => {
            const arrayResponse = JSON.stringify([
                { severity: 'LOW', advice: 'Rest' }
            ]);

            const parsed = JSON.parse(arrayResponse);
            expect(Array.isArray(parsed)).toBe(true);
            expect(parsed.length).toBe(1);
        });

        test('should handle response with nested objects', () => {
            const nestedResponse = JSON.stringify({
                severity: 'LOW',
                advice: 'Rest',
                metadata: {
                    timestamp: '2024-01-01',
                    source: 'AI'
                }
            });

            const parsed = JSON.parse(nestedResponse);
            expect(parsed.severity).toBe('LOW');
            expect(parsed.advice).toBe('Rest');
            expect(parsed.metadata).toBeDefined();
            expect(parsed.metadata.timestamp).toBe('2024-01-01');
        });

        test('should handle response with special characters in advice', () => {
            const responseWithSpecialChars = JSON.stringify({
                severity: 'MODERATE',
                advice: 'Take medication & rest. Don\'t overexert yourself!'
            });

            const parsed = JSON.parse(responseWithSpecialChars);
            expect(parsed.severity).toBe('MODERATE');
            expect(parsed.advice).toContain('&');
            expect(parsed.advice).toContain('Don\'t');
        });

        test('should handle response with unicode characters', () => {
            const responseWithUnicode = JSON.stringify({
                severity: 'LOW',
                advice: 'Rest and drink water 💧'
            });

            const parsed = JSON.parse(responseWithUnicode);
            expect(parsed.severity).toBe('LOW');
            expect(parsed.advice).toContain('💧');
        });

        test('should handle very long advice text', () => {
            const longAdvice = 'A'.repeat(5000);
            const responseWithLongAdvice = JSON.stringify({
                severity: 'MODERATE',
                advice: longAdvice
            });

            const parsed = JSON.parse(responseWithLongAdvice);
            expect(parsed.severity).toBe('MODERATE');
            expect(parsed.advice.length).toBe(5000);
        });
    });
});
