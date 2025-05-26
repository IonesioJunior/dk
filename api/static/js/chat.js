'use strict';

// Prevent multiple script executions
if (window.chatScriptLoaded) {
    console.log('Chat script already loaded, skipping re-execution...');
} else {
    window.chatScriptLoaded = true;

// Configuration constants - prevent redeclaration
window.CONFIG = window.CONFIG || {
    MESSAGE_CHUNK_DELAY: 0,
    DEBOUNCE_DELAY: 150,
    AUTO_SCROLL_THRESHOLD: 100,
    MAX_INPUT_HEIGHT: 120,
    RESPONSE_WAIT_TIME: 5000,
    MAX_MESSAGE_LENGTH: 4000,
    REQUEST_TIMEOUT: 30000,
    POPUP_OFFSET: 8,
    POLL_INITIAL_DELAY: 1000,
    POLL_MAX_DELAY: 5000,
    POLL_MAX_ATTEMPTS: 10
};

// State Machine Implementation
class ChatStateMachine {
    constructor() {
        this.states = {
            IDLE: 'idle',
            TYPING: 'typing',
            SENDING: 'sending',
            RECEIVING: 'receiving',
            ERROR: 'error',
            MENTION_ACTIVE: 'mention_active',
            SLASH_ACTIVE: 'slash_active'
        };

        this.currentState = this.states.IDLE;
        this.stateData = {};
        this.listeners = {};
    }

    transition(newState, data = {}) {
        const oldState = this.currentState;
        this.currentState = newState;
        this.stateData = { ...this.stateData, ...data };

        if (this.listeners[newState]) {
            this.listeners[newState].forEach(callback => callback(oldState, data));
        }
    }

    onStateChange(state, callback) {
        if (!this.listeners[state]) {
            this.listeners[state] = [];
        }
        this.listeners[state].push(callback);
    }

    getState() {
        return this.currentState;
    }

    getData() {
        return this.stateData;
    }
}

// Request Manager with cancellation support
class RequestManager {
    constructor() {
        this.activeRequests = new Map();
    }

    async fetch(id, url, options = {}) {
        // Cancel any existing request with the same ID
        this.cancel(id);

        const controller = new AbortController();
        this.activeRequests.set(id, controller);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });

            this.activeRequests.delete(id);
            return response;
        } catch (error) {
            this.activeRequests.delete(id);
            // Silently handle abort errors (they're expected during navigation)
            if (error.name === 'AbortError') {
                throw error;
            }
            throw error;
        }
    }

    cancel(id) {
        const controller = this.activeRequests.get(id);
        if (controller) {
            controller.abort();
            this.activeRequests.delete(id);
        }
    }

    cancelAll() {
        this.activeRequests.forEach(controller => controller.abort());
        this.activeRequests.clear();
    }
}

// Event Manager for cleanup
class EventManager {
    constructor() {
        this.listeners = [];
    }

    addEventListener(target, event, handler, options) {
        target.addEventListener(event, handler, options);
        this.listeners.push({ target, event, handler, options });
    }

    removeAllListeners() {
        this.listeners.forEach(({ target, event, handler, options }) => {
            target.removeEventListener(event, handler, options);
        });
        this.listeners = [];
    }
}

// Chat Application
class ChatApplication {
    constructor() {
        // Core components
        this.stateMachine = new ChatStateMachine();
        this.requestManager = new RequestManager();
        this.eventManager = new EventManager();

        // DOM elements
        this.elements = this.initializeDOMElements();

        // State
        this.state = {
            users: [],
            currentUserId: null,
            mentionContext: {
                active: false,
                startPosition: -1,
                selectedIndex: 0,
                filteredItems: []
            },
            slashContext: {
                active: false,
                startPosition: -1,
                selectedIndex: 0,
                filteredItems: []
            },
            commands: this.getSlashCommands(),
            promptResponses: {},  // Store peer responses by prompt ID
            pendingMessages: new Map(),  // Track messages with pending peer responses
            messageHistory: [],  // Track message history
            mapInitialized: false,  // Track if map has been initialized
            mapObserver: null,  // Store observer for cleanup
            mapResizeTimeout: null  // Store resize timeout for cleanup
        };

        // Initialize
        this.initialize();
    }

    initializeDOMElements() {
        console.log('Initializing DOM elements');
        const elements = {
            chatMessages: document.getElementById('chat-messages'),
            chatPlaceholder: document.getElementById('chat-placeholder'),
            chatScrollContainer: document.getElementById('chat-scroll-container'),
            chatInput: document.getElementById('chat-input'),
            sendButton: document.getElementById('send-message'),
            errorMessage: document.getElementById('error-message'),
            mentionPopup: document.getElementById('mention-popup'),
            slashPopup: document.getElementById('slash-popup')
        };

        // Debug: Check if critical elements were found
        const criticalElements = [
            'chatMessages',
            'chatPlaceholder',
            'chatScrollContainer',
            'chatInput',
            'sendButton'
        ];

        const optionalElements = [
            'errorMessage',
            'mentionPopup',
            'slashPopup'
        ];

        for (const [key, element] of Object.entries(elements)) {
            if (!element) {
                if (criticalElements.includes(key)) {
                    console.error(`Critical element not found: ${key}`);
                } else if (optionalElements.includes(key)) {
                    console.warn(`Optional element not found: ${key} (this may be normal)`);
                }
            }
        }

        return elements;
    }

    initialize() {
        // Setup state machine listeners
        this.setupStateMachineListeners();

        // Setup event listeners
        this.setupEventListeners();

        // Initialize UI
        this.updateSendButton();
        this.autoResize();
        this.checkMessageVisibility();

    }

    setupStateMachineListeners() {
        this.stateMachine.onStateChange(this.stateMachine.states.SENDING, () => {
            this.elements.chatInput.disabled = true;
            this.elements.sendButton.disabled = true;
            this.hideError();
        });

        this.stateMachine.onStateChange(this.stateMachine.states.IDLE, () => {
            this.elements.chatInput.disabled = false;
            this.updateSendButton();
        });

        this.stateMachine.onStateChange(this.stateMachine.states.ERROR, (oldState, data) => {
            this.showError(data.message);
            this.elements.chatInput.disabled = false;
            this.updateSendButton();
        });

        this.stateMachine.onStateChange(this.stateMachine.states.MENTION_ACTIVE, () => {
            if (this.elements.mentionPopup) {
                this.elements.mentionPopup.classList.remove('hidden');
            }
        });

        this.stateMachine.onStateChange(this.stateMachine.states.SLASH_ACTIVE, () => {
            if (this.elements.slashPopup) {
                this.elements.slashPopup.classList.remove('hidden');
            }
        });
    }

    setupEventListeners() {
        console.log('Setting up event listeners');

        if (!this.elements.chatInput) {
            console.error('Chat input element not found - chat functionality will be limited');
            return;
        }

        if (!this.elements.sendButton) {
            console.error('Send button element not found - chat functionality will be limited');
            return;
        }

        // Input events
        console.log('Adding input event listener');
        this.eventManager.addEventListener(this.elements.chatInput, 'input',
            this.handleInput.bind(this));

        // Send events
        console.log('Adding click event listener to send button');
        this.eventManager.addEventListener(this.elements.sendButton, 'click',
            this.handleSend.bind(this));

        console.log('Adding keydown event listener to chat input');
        this.eventManager.addEventListener(this.elements.chatInput, 'keydown',
            this.handleKeyDown.bind(this));

        // Add direct event listeners as a backup
        console.log('Adding direct event listeners as backup');
        this.elements.sendButton.onclick = () => {
            console.log('Direct click on send button');
            this.handleSend();
        };

        this.elements.chatInput.onkeydown = (event) => {
            console.log('Direct keydown on chat input', event.key);
            if (event.key === 'Enter' && !event.shiftKey) {
                console.log('Enter key pressed directly');
                event.preventDefault();
                this.handleSend();
            }
        };

        // Track input cursor position for proper popup positioning
        this.eventManager.addEventListener(this.elements.chatInput, 'click',
            this.handleInputClick.bind(this));

        // Popup item click listeners
        this.setupPopupItemListeners('mention');
        this.setupPopupItemListeners('slash');

        // Document click to close popups
        this.eventManager.addEventListener(document, 'click', (event) => {
            const mentionPopup = this.elements.mentionPopup;
            const slashPopup = this.elements.slashPopup;
            const chatInput = this.elements.chatInput;

            if (!chatInput.contains(event.target)) {
                if (!mentionPopup.contains(event.target)) {
                    this.hidePopup('mention');
                }
                if (!slashPopup.contains(event.target)) {
                    this.hidePopup('slash');
                }
            }

            // Close response dropdowns if clicking outside
            const responseCounters = document.querySelectorAll('.response-counter');
            responseCounters.forEach(counter => {
                const dropdown = counter.querySelector('.response-dropdown');
                if (dropdown && !dropdown.classList.contains('hidden') && !counter.contains(event.target)) {
                    dropdown.classList.add('hidden');
                }
            });
        });
    }


    handleInput() {
        this.autoResize();
        this.updateSendButton();
        this.checkForTriggers();
    }

    handleKeyDown(event) {
        console.log('Key down event:', event.key);
        const currentState = this.stateMachine.getState();
        const mentionActive = currentState === this.stateMachine.states.MENTION_ACTIVE;
        const slashActive = currentState === this.stateMachine.states.SLASH_ACTIVE;

        if (mentionActive || slashActive) {
            const context = mentionActive ? this.state.mentionContext : this.state.slashContext;
            const popupType = mentionActive ? 'mention' : 'slash';

            switch(event.key) {
                case 'Tab':
                case 'Enter':
                    event.preventDefault();
                    if (context.filteredItems.length > 0) {
                        this.selectPopupItem(popupType, context.filteredItems[context.selectedIndex]);
                    }
                    break;
                case 'ArrowDown':
                    event.preventDefault();
                    this.navigatePopup(popupType, 1);
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    this.navigatePopup(popupType, -1);
                    break;
                case 'Escape':
                    event.preventDefault();
                    this.hidePopup(popupType);
                    break;
            }
        } else if (event.key === 'Enter' && !event.shiftKey) {
            console.log('Enter key pressed, handling send');
            event.preventDefault();
            this.handleSend();
        }
    }

    async handleSend() {
        console.log('handleSend called');
        const message = this.elements.chatInput.value.trim();
        console.log('Message content:', message);

        if (!message || this.stateMachine.getState() === this.stateMachine.states.SENDING) {
            console.log('Message empty or already sending, returning');
            return;
        }

        // Handle slash commands
        if (message.startsWith('/')) {
            const command = message.split(' ')[0].toLowerCase();

            if (command === '/clear') {
                this.elements.chatInput.value = '';
                await this.handleClearConversation();
                return;
            }
            // Future slash commands can be handled here
        }

        if (message.length > window.CONFIG.MAX_MESSAGE_LENGTH) {
            this.showError(`Message too long. Maximum ${window.CONFIG.MAX_MESSAGE_LENGTH} characters.`);
            return;
        }

        this.stateMachine.transition(this.stateMachine.states.SENDING);

        // Clear input
        this.elements.chatInput.value = '';
        this.autoResize();

        // Add user message
        this.addMessage(message, true);

        // Show typing indicator by adding a temporary AI message with dot animation
        const typingIndicator = this.createTypingIndicator();

        try {
            // Get LLM configuration from header component or local elements
            let provider, model, apiToken;

            if (window.parent && window.parent.getLLMConfig) {
                // Get config from parent window (header component)
                const config = window.parent.getLLMConfig();
                if (config) {
                    provider = config.provider;
                    model = config.model;
                    apiToken = config.apiToken;
                }
            }

            // Fallback to local elements if not available from parent
            if (!provider || !model) {
                provider = this.elements.selectedProvider?.value || 'anthropic';
                model = this.elements.selectedModel?.value || 'claude-3-sonnet';
            }

            // Extract mentions
            const mentions = this.extractMentions(message);

            const requestBody = {
                message,
                provider: provider,
                model: model
            };

            // Include API token if available
            if (apiToken) {
                requestBody.api_token = apiToken;
            }

            // Include mentions if present
            if (mentions.length > 0) {
                requestBody.peers = mentions;
                console.log('Mentions detected:', mentions);
            }

            console.log('Sending request to API:', {
                url: mentions.length > 0 ? '/api/query_peers' : '/api/query',
                method: 'POST',
                body: requestBody,
                headers: { 'Content-Type': 'application/json' }
            });

            try {
                const endpoint = mentions.length > 0 ? '/api/query_peers' : '/api/query';
                const response = await this.requestManager.fetch('message', endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify(requestBody)
                });

                console.log('API response received:', {
                    status: response.status,
                    statusText: response.statusText
                });

                if (!response.ok) {
                    console.error('API returned error status:', response.status);
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                // Remove typing indicator
                if (typingIndicator && typingIndicator.parentNode) {
                    console.log('Removing typing indicator');
                    typingIndicator.parentNode.removeChild(typingIndicator);
                }

                if (mentions.length > 0) {
                    console.log('Processing peer response for mentions:', mentions);
                    await this.handlePeerResponse(response, mentions);
                } else {
                    console.log('Starting to handle streaming response');
                    await this.handleStreamingResponse(response);
                    console.log('Finished handling streaming response');
                }

                this.stateMachine.transition(this.stateMachine.states.IDLE);
                console.log('Transitioned to IDLE state');
            } catch (error) {
                console.error('Error in handleSend try-catch:', error);

                // Remove typing indicator
                if (typingIndicator && typingIndicator.parentNode) {
                    typingIndicator.parentNode.removeChild(typingIndicator);
                }

                this.stateMachine.transition(this.stateMachine.states.ERROR, {
                    message: 'Failed to send message. Please try again.'
                });

                this.addMessage('Sorry, I couldn\'t connect to the server. Please try again.', false);
            }
        } catch (error) {
            console.error('Outer error in handleSend:', error);

            // Remove typing indicator
            if (typingIndicator && typingIndicator.parentNode) {
                typingIndicator.parentNode.removeChild(typingIndicator);
            }

            this.stateMachine.transition(this.stateMachine.states.ERROR, {
                message: 'Failed to send message. Please try again.'
            });

            this.addMessage('Sorry, I couldn\'t process your request. Please try again.', false);
        }
    }

    async handleStreamingResponse(response, existingMessageRefs = null) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let content = '';
        let aiMessageElement = existingMessageRefs ? existingMessageRefs.messageElement : null;

        try {
            console.log('Started reading streaming response');
            while (true) {
                console.log('Reading next chunk...');
                const { done, value } = await reader.read();
                if (done) {
                    console.log('Stream ended');
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                console.log('Received chunk:', chunk);
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                console.log('Processing', lines.length, 'lines');
                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            console.log('Processing line:', line);
                            const data = JSON.parse(line);
                            console.log('Parsed JSON data:', data);

                            if (data.type === 'start' && data.status === 'success') {
                                console.log('Received start signal');
                                // Create AI message container on first chunk
                                if (!aiMessageElement) {
                                    console.log('Creating empty AI message');
                                    aiMessageElement = this.createEmptyAIMessage();
                                }
                            } else if (data.type === 'chunk' && data.content) {
                                console.log('Received content chunk:', data.content);
                                // Append content
                                content += data.content;

                                // Update message
                                if (aiMessageElement) {
                                    console.log('Updating AI message with content');
                                    aiMessageElement.innerHTML = this.formatMessageContent(content);
                                    this.scrollToBottom();
                                } else {
                                    console.log('No aiMessageElement to update');
                                }
                            } else if (data.status === 'error') {
                                console.error('Received error in stream:', data.message);
                                this.addMessage('Sorry, I encountered an error: ' + data.message, false);
                                return;
                            }
                        } catch (e) {
                            console.error('Error parsing JSON:', e);
                        }
                    }
                }
            }

            // Handle any remaining buffer
            if (buffer.trim()) {
                try {
                    const data = JSON.parse(buffer);
                    if (data.type === 'chunk' && data.content) {
                        content += data.content;
                        if (aiMessageElement) {
                            aiMessageElement.innerHTML = this.formatMessageContent(content);
                        }
                    }
                } catch (e) {
                    console.error('Error parsing JSON:', e);
                }
            }

            this.scrollToBottom();
        } finally {
            reader.releaseLock();
        }
    }

    async handlePeerResponse(response, mentions) {
        try {
            const data = await response.json();

            if (data.status === 'success' && data.prompt_id) {
                console.log('Received peer response with prompt_id:', data.prompt_id);

                // Create AI message with response counter
                const messageRefs = this.createAIMessageWithCounter(mentions.length, data.prompt_id);

                // Store mentions for refresh functionality
                this.state.pendingMessages.set(data.prompt_id, {
                    mentions: mentions,
                    messageRefs: messageRefs
                });

                // Start polling for responses
                console.log('Starting to poll for responses');
                const responses = await this.pollForResponses(data.prompt_id, messageRefs, mentions);

                // Store responses for dropdown functionality
                this.state.promptResponses[data.prompt_id] = responses;

                if (responses && responses.length > 0) {
                    const actualResponses = responses.filter(r => r.type === 'response');
                    console.log(`Received ${actualResponses.length} actual responses`);

                    this.updateResponseCounter(messageRefs, actualResponses.length, mentions.length);
                    this.updateAIMessageContent(messageRefs, `Received ${actualResponses.length} responses. Summarizing...`);

                    // Call summarize endpoint
                    console.log('Calling summarize endpoint');
                    const summarizeResponse = await this.requestManager.fetch('summarize', '/api/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify({ responses: actualResponses })
                    });

                    if (summarizeResponse.ok) {
                        console.log('Streaming summarized response');
                        await this.handleStreamingResponse(summarizeResponse, messageRefs);
                    } else {
                        console.error('Failed to get summary');
                        this.updateAIMessageContent(messageRefs, 'Failed to summarize responses.');
                    }
                } else {
                    console.log('No responses received from peers');
                    this.updateAIMessageContent(messageRefs, 'No responses received from peers.');
                }
            } else {
                console.error('Invalid peer response:', data);
                this.addMessage('Sorry, failed to send query to peers.', false);
            }
        } catch (error) {
            console.error('Error handling peer response:', error);
            this.addMessage('Sorry, failed to process peer responses.', false);
        }
    }

    async pollForResponses(promptId, messageRefs, mentions) {
        let attempts = 0;
        let delay = window.CONFIG.POLL_INITIAL_DELAY;

        console.log('Starting polling for responses');
        this.updateAIMessageContent(messageRefs, 'Gathering responses from peers...');

        while (attempts < window.CONFIG.POLL_MAX_ATTEMPTS) {
            try {
                console.log(`Polling attempt ${attempts + 1}/${window.CONFIG.POLL_MAX_ATTEMPTS}`);
                const response = await this.requestManager.fetch(
                    `responses-${promptId}`,
                    `/api/prompt-responses/${promptId}`,
                    { credentials: 'same-origin' }
                );

                if (response.ok) {
                    const data = await response.json();
                    let responseData = data.responses || [];

                    console.log('Received response data:', responseData);

                    if (responseData.length > 0) {
                        // Get list of peers who have responded
                        const respondedPeers = responseData.map(r => r.from_peer);

                        // Add pending status for peers that haven't responded yet
                        mentions.forEach(peer => {
                            if (!respondedPeers.includes(peer)) {
                                responseData.push({
                                    type: 'pending',
                                    from_peer: peer
                                });
                            }
                        });

                        // Update counter
                        const actualResponses = responseData.filter(r => r.type === 'response');
                        this.updateResponseCounter(messageRefs, actualResponses.length, mentions.length);

                        return responseData;
                    }
                }

                attempts++;
                console.log(`No responses yet, waiting ${delay}ms before next attempt`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay = Math.min(delay * 1.5, window.CONFIG.POLL_MAX_DELAY);
            } catch (error) {
                console.error('Error polling for responses:', error);
                attempts++;
            }
        }

        console.log('Max polling attempts reached, creating empty responses');
        // If we reached max attempts with no responses, create empty responses for all peers
        const emptyResponses = mentions.map(peer => ({
            type: 'pending',
            from_peer: peer
        }));

        return emptyResponses;
    }

    async handleRefreshResponses(promptId, mentionCount, messageWrapper) {
        console.log('Refreshing responses for prompt:', promptId);

        // Get stored data
        const storedData = this.state.pendingMessages.get(promptId);
        if (!storedData) {
            console.error('No stored data found for prompt:', promptId);
            return;
        }

        const { mentions, messageRefs } = storedData;

        // Show loading state in refresh button
        const refreshButton = messageWrapper.querySelector('.refresh-responses');
        if (refreshButton) {
            const icon = refreshButton.querySelector('i');
            if (icon) {
                icon.classList.add('animate-spin');
            }
            refreshButton.disabled = true;
            refreshButton.style.opacity = '1'; // Keep visible while loading
        }

        try {
            // Update message content to show refreshing
            this.updateAIMessageContent(messageRefs, 'Refreshing responses from peers...');

            // Poll for responses again
            const responses = await this.pollForResponses(promptId, messageRefs, mentions);

            // Update stored responses
            this.state.promptResponses[promptId] = responses;

            if (responses && responses.length > 0) {
                const actualResponses = responses.filter(r => r.type === 'response');
                console.log(`Refresh: Received ${actualResponses.length} actual responses`);

                this.updateResponseCounter(messageRefs, actualResponses.length, mentions.length);

                if (actualResponses.length > 0) {
                    this.updateAIMessageContent(messageRefs, `Received ${actualResponses.length} responses. Summarizing...`);

                    // Call summarize endpoint
                    console.log('Calling summarize endpoint after refresh');
                    const summarizeResponse = await this.requestManager.fetch('summarize', '/api/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify({ responses: actualResponses })
                    });

                    if (summarizeResponse.ok) {
                        console.log('Streaming summarized response after refresh');
                        await this.handleStreamingResponse(summarizeResponse, messageRefs);
                    } else {
                        console.error('Failed to get summary after refresh');
                        this.updateAIMessageContent(messageRefs, 'Failed to summarize responses after refresh.');
                    }
                } else {
                    this.updateAIMessageContent(messageRefs, 'No new responses received from peers.');
                }
            } else {
                console.log('No responses received from peers after refresh');
                this.updateAIMessageContent(messageRefs, 'No responses received from peers.');
            }
        } catch (error) {
            console.error('Error refreshing responses:', error);
            this.updateAIMessageContent(messageRefs, 'Error refreshing responses. Please try again.');
        } finally {
            // Reset refresh button state
            if (refreshButton) {
                const icon = refreshButton.querySelector('i');
                if (icon) {
                    icon.classList.remove('animate-spin');
                }
                refreshButton.disabled = false;
            }
        }
    }

    addMessage(content, isUser = false) {
        // Create message container
        const messageWrapper = document.createElement('div');
        messageWrapper.className = isUser ? 'flex items-start justify-end max-w-3xl mx-auto w-full py-2 px-2 rounded-lg transition-colors duration-200 hover:theme-bg-surface' : 'flex items-start max-w-3xl mx-auto w-full py-2 px-2 rounded-lg transition-colors duration-200 hover:theme-bg-surface';

        const time = new Date();
        const formattedTime = this.formatTime(time);

        // User message has different structure than AI message
        if (isUser) {
            // Get user ID from the hidden input field
            const userId = document.getElementById('current-user-id')?.value || 'User';

            messageWrapper.innerHTML = `
                <div class="max-w-[85%] text-right">
                    <div class="font-medium text-sm mb-1 text-gray-600 dark:text-gray-400 flex items-center justify-end">
                        <span class="text-xs text-gray-500">${formattedTime}</span>
                        <span class="mx-2">•</span>
                        <span class="theme-primary">${userId}</span>
                    </div>
                    <p>${this.formatMessageContent(content)}</p>
                </div>
                <div class="w-8 h-8 rounded-full flex items-center justify-center ml-3 mt-1" style="background: linear-gradient(120deg, #4a90e2, #8e44ad);">
                    <span class="text-sm font-semibold text-white">${userId.substring(0, 2).toUpperCase()}</span>
                </div>
            `;
        } else {
            messageWrapper.innerHTML = `
                <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 mt-1" style="background: linear-gradient(120deg, #4a90e2, #8e44ad);">
                    <i data-lucide="bot" class="h-4 w-4 text-white"></i>
                </div>
                <div class="max-w-[85%]">
                    <div class="font-medium text-sm mb-1 text-gray-600 dark:text-gray-400 flex items-center">
                        <span class="theme-primary">AI Assistant</span>
                        <span class="mx-2">•</span>
                        <span class="text-xs text-gray-500">${formattedTime}</span>
                    </div>
                    <p>${this.formatMessageContent(content)}</p>
                </div>
            `;
        }

        this.elements.chatMessages.appendChild(messageWrapper);
        this.scrollToBottom();

        // Initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons({ container: messageWrapper });
        }

        // Check if we need to show/hide placeholder
        this.checkMessageVisibility();

        return messageWrapper;
    }

    createEmptyAIMessage() {
        // Create the empty message that will be filled with streaming content
        const messageWrapper = document.createElement('div');
        messageWrapper.className = 'flex items-start max-w-3xl mx-auto w-full py-2 px-2 rounded-lg transition-colors duration-200 hover:theme-bg-surface';

        const formattedTime = this.formatTime(new Date());

        messageWrapper.innerHTML = `
            <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 mt-1" style="background: linear-gradient(120deg, #4a90e2, #8e44ad);">
                <i data-lucide="bot" class="h-4 w-4 text-white"></i>
            </div>
            <div class="max-w-[85%]">
                <div class="font-medium text-sm mb-1 text-gray-600 dark:text-gray-400 flex items-center">
                    <span class="theme-primary">AI Assistant</span>
                    <span class="mx-2">•</span>
                    <span class="text-xs text-gray-500">${formattedTime}</span>
                </div>
                <div class="message-content"></div>
            </div>
        `;

        this.elements.chatMessages.appendChild(messageWrapper);

        // Initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons({ container: messageWrapper });
        }

        // Check if we need to show/hide placeholder
        this.checkMessageVisibility();

        this.scrollToBottom();

        // Return the content div so we can update it
        return messageWrapper.querySelector('.message-content');
    }

    createTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'flex items-start max-w-3xl mx-auto w-full typing-indicator py-2 px-2 rounded-lg transition-colors duration-200 hover:theme-bg-surface';

        typingIndicator.innerHTML = `
            <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 mt-1" style="background: linear-gradient(120deg, #4a90e2, #8e44ad);">
                <i data-lucide="bot" class="h-4 w-4 text-white"></i>
            </div>
            <div class="max-w-[85%]">
                <div class="font-medium text-sm mb-1 text-gray-600 dark:text-gray-400 flex items-center">
                    <span class="theme-primary">AI Assistant</span>
                    <span class="mx-2">•</span>
                    <span class="text-xs text-gray-500">${this.formatTime(new Date())}</span>
                </div>
                <div class="flex items-center space-x-1 mt-2 ml-1">
                    <div uk-spinner="ratio: 0.5"></div>
                    <span class="text-sm text-gray-500">Thinking...</span>
                </div>
            </div>
        `;

        this.elements.chatMessages.appendChild(typingIndicator);

        // Initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons({ container: typingIndicator });
        }

        // Check if we need to show/hide placeholder
        this.checkMessageVisibility();

        this.scrollToBottom();

        return typingIndicator;
    }

    createAIMessageWithCounter(mentionCount, promptId) {
        // Create AI message with response counter
        const messageWrapper = document.createElement('div');
        messageWrapper.className = 'message-wrapper-hover flex items-start max-w-3xl mx-auto w-full py-2 px-2 rounded-lg transition-colors duration-200 hover:theme-bg-surface';

        const formattedTime = this.formatTime(new Date());

        const responseCounterHTML = mentionCount > 0 ? `
            <div class="response-counter flex items-center gap-1 ml-2 px-2 py-1 theme-bg-surface rounded-md cursor-pointer hover:theme-bg-surface transition-colors"
                 id="response-counter-${promptId}"
                 data-prompt-id="${promptId}"
                 title="Click to see individual responses">
                <i data-lucide="users" class="h-3 w-3"></i>
                <span class="text-xs font-medium">0/${mentionCount}</span>
                <div class="response-dropdown hidden absolute z-50 theme-bg-surface border theme-border rounded-lg shadow-lg mt-8 w-80 max-h-60 overflow-y-auto">
                    <div class="response-dropdown-content p-3">
                        <div class="response-dropdown-loading text-sm theme-text-secondary">Loading responses...</div>
                    </div>
                </div>
            </div>
        ` : '';

        const refreshButtonHTML = mentionCount > 0 ? `
            <button class="refresh-responses flex items-center justify-center p-1.5 bg-transparent text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 rounded-md transition-all duration-200 opacity-0"
                    id="refresh-responses-${promptId}"
                    data-prompt-id="${promptId}"
                    data-mention-count="${mentionCount}"
                    title="Refresh responses">
                <i data-lucide="refresh-cw" class="h-4 w-4"></i>
            </button>
        ` : '';

        console.log('Creating AI message with counter, mentionCount:', mentionCount);
        console.log('Response counter HTML:', responseCounterHTML);

        messageWrapper.innerHTML = `
            <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 mt-1" style="background: linear-gradient(120deg, #4a90e2, #8e44ad);">
                <i data-lucide="bot" class="h-4 w-4 text-white"></i>
            </div>
            <div class="flex-1">
                <div class="font-medium text-sm mb-1 text-gray-600 dark:text-gray-400 flex items-center justify-between">
                    <div class="flex items-center">
                        <span class="theme-primary">AI Assistant</span>
                        <span class="mx-2">•</span>
                        <span class="text-xs text-gray-500">${formattedTime}</span>
                        ${responseCounterHTML}
                    </div>
                    ${refreshButtonHTML}
                </div>
                <div class="message-content">
                    <div class="flex items-center space-x-1 mt-2 ml-1">
                        <div uk-spinner="ratio: 0.5"></div>
                        <span class="text-sm text-gray-500">Thinking...</span>
                    </div>
                </div>
            </div>
        `;

        this.elements.chatMessages.appendChild(messageWrapper);

        // Initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons({ container: messageWrapper });
        }

        // Check if we need to show/hide placeholder
        this.checkMessageVisibility();

        this.scrollToBottom();

        // Add click handler for response counter if it exists
        const responseCounter = messageWrapper.querySelector('.response-counter');
        if (responseCounter) {
            responseCounter.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleResponseDropdown(promptId);
            });
        }

        // Add click handler for refresh button if it exists
        const refreshButton = messageWrapper.querySelector('.refresh-responses');
        if (refreshButton) {
            console.log('Refresh button found and adding click handler');

            // Add hover listeners to show/hide refresh button
            messageWrapper.addEventListener('mouseenter', () => {
                if (!refreshButton.disabled) {
                    refreshButton.style.opacity = '1';
                }
            });

            messageWrapper.addEventListener('mouseleave', () => {
                if (!refreshButton.disabled) {
                    refreshButton.style.opacity = '0';
                }
            });

            refreshButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleRefreshResponses(promptId, mentionCount, messageWrapper);
            });
        } else {
            console.log('Refresh button NOT found in message wrapper');
        }

        return {
            messageElement: messageWrapper.querySelector('.message-content'),
            responseCounter: responseCounter,
            refreshButton: refreshButton,
            wrapper: messageWrapper,
            promptId: promptId
        };
    }

    updateAIMessageContent(messageRefs, content) {
        if (messageRefs && messageRefs.messageElement) {
            messageRefs.messageElement.innerHTML = this.formatMessageContent(content);
            this.scrollToBottom();
        }
    }

    updateResponseCounter(messageRefs, responseCount, totalMentions) {
        if (messageRefs && messageRefs.responseCounter) {
            const counterSpan = messageRefs.responseCounter.querySelector('span');
            if (counterSpan) {
                counterSpan.textContent = `${responseCount}/${totalMentions}`;
            }
        }
    }

    async toggleResponseDropdown(promptId) {
        const responseCounter = document.getElementById(`response-counter-${promptId}`);
        if (!responseCounter) return;

        const dropdown = responseCounter.querySelector('.response-dropdown');
        if (!dropdown) return;

        const isVisible = !dropdown.classList.contains('hidden');

        if (!isVisible) {
            // Hide any other open dropdowns
            document.querySelectorAll('.response-dropdown').forEach(d => {
                if (d !== dropdown) d.classList.add('hidden');
            });

            // Show this dropdown
            dropdown.classList.remove('hidden');

            // Load responses
            const dropdownContent = dropdown.querySelector('.response-dropdown-content');
            dropdownContent.innerHTML = '<div class="response-dropdown-loading text-sm theme-text-secondary">Loading responses...</div>';

            try {
                const responses = this.state.promptResponses[promptId];
                if (responses && responses.length > 0) {
                    this.renderResponseDropdown(dropdownContent, responses);
                } else {
                    dropdownContent.innerHTML = '<div class="response-dropdown-loading text-sm theme-text-secondary">No responses available</div>';
                }
            } catch (error) {
                console.error('Error loading responses:', error);
                dropdownContent.innerHTML = '<div class="response-dropdown-loading text-sm theme-text-primary">Error loading responses</div>';
            }
        } else {
            // Hide dropdown
            dropdown.classList.add('hidden');
        }
    }

    renderResponseDropdown(container, responses) {
        if (!container || !responses) return;

        let html = '';

        responses.forEach(resp => {
            const peerName = this.escapeHtml(resp.from_peer || 'Unknown');

            if (resp.type === 'response') {
                // Response received
                html += `
                    <div class="response-item border-b theme-border pb-2 mb-2 last:border-0 last:mb-0">
                        <div class="flex items-center justify-between mb-1">
                            <span class="font-medium text-sm theme-text-primary">${peerName}</span>
                            <span class="text-xs text-green-600 theme-bg-success px-2 py-0.5 rounded-full">Responded</span>
                        </div>
                        <div class="text-sm theme-text-secondary">${this.escapeHtml(resp.response)}</div>
                    </div>
                `;
            } else if (resp.type === 'error') {
                // Error response
                html += `
                    <div class="response-item border-b theme-border pb-2 mb-2 last:border-0 last:mb-0">
                        <div class="flex items-center justify-between mb-1">
                            <span class="font-medium text-sm theme-text-primary">${peerName}</span>
                            <span class="text-xs text-red-600 theme-bg-danger px-2 py-0.5 rounded-full">Error</span>
                        </div>
                        <div class="text-sm text-red-600">${this.escapeHtml(resp.error)}</div>
                    </div>
                `;
            } else if (resp.type === 'pending') {
                // Pending response
                html += `
                    <div class="response-item border-b theme-border pb-2 mb-2 last:border-0 last:mb-0">
                        <div class="flex items-center justify-between mb-1">
                            <span class="font-medium text-sm theme-text-primary">${peerName}</span>
                            <span class="text-xs text-yellow-600 theme-bg-warning px-2 py-0.5 rounded-full">Pending</span>
                        </div>
                        <div class="text-sm theme-text-secondary">Waiting for response...</div>
                    </div>
                `;
            }
        });

        if (html === '') {
            html = '<div class="response-dropdown-loading text-sm theme-text-secondary">No responses available</div>';
        }

        container.innerHTML = html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatTime(date) {
        // Format the time into human-readable form
        const hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const displayHours = hours % 12 || 12;
        const paddedMinutes = minutes.toString().padStart(2, '0');

        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = months[date.getMonth()];
        const day = date.getDate();

        return `${month} ${day}, ${displayHours}:${paddedMinutes} ${ampm}`;
    }

    formatMessageContent(content) {
        // This would be expanded to handle Markdown and other formatting
        // For now, just convert newlines to <br> and handle basic links
        return content
            .replace(/\n/g, '<br>')
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-blue-500 hover:underline">$1</a>');
    }

    // UI Helper Methods
    autoResize() {
        const input = this.elements.chatInput;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, window.CONFIG.MAX_INPUT_HEIGHT) + 'px';
    }

    updateSendButton() {
        const hasText = this.elements.chatInput.value.trim().length > 0;
        this.elements.sendButton.disabled = !hasText;

        // Toggle active state
        if (hasText) {
            this.elements.sendButton.classList.add('bg-blue-500', 'text-white');
            this.elements.sendButton.classList.remove('bg-transparent', 'text-gray-400', 'opacity-50', 'cursor-not-allowed', 'hover:bg-gray-100', 'dark:hover:bg-gray-700');
        } else {
            this.elements.sendButton.classList.remove('bg-blue-500', 'text-white');
            this.elements.sendButton.classList.add('bg-transparent', 'text-gray-400', 'opacity-50', 'cursor-not-allowed', 'hover:bg-gray-100', 'dark:hover:bg-gray-700');
        }
    }

    scrollToBottom() {
        // Use the reference from elements if available
        const container = this.elements.chatScrollContainer;
        if (container) {
            // Scroll the container to the bottom
            container.scrollTop = container.scrollHeight;
            console.log('Scrolling container to bottom, height:', container.scrollHeight);
        } else {
            // Fallback to the messages div if container not found
            const messages = this.elements.chatMessages;
            messages.scrollTop = messages.scrollHeight;
            console.log('Fallback: Scrolling messages to bottom, height:', messages.scrollHeight);
        }
    }

    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorMessage.classList.remove('hidden');
        setTimeout(() => this.hideError(), 5000);
    }

    hideError() {
        this.elements.errorMessage.classList.add('hidden');
    }

    checkMessageVisibility() {
        const messageCount = this.elements.chatMessages.children.length;

        if (messageCount === 0) {
            // Show placeholder, hide messages
            this.elements.chatPlaceholder.classList.remove('hidden');
            this.elements.chatMessages.classList.add('hidden');
            // Initialize map when placeholder is shown
            this.initializeMapPlaceholder();
        } else {
            // Show messages, hide placeholder
            this.elements.chatPlaceholder.classList.add('hidden');
            this.elements.chatMessages.classList.remove('hidden');
        }

        // Initialize Lucide icons in placeholder if needed
        if (messageCount === 0 && window.lucide) {
            lucide.createIcons({ container: this.elements.chatPlaceholder });
        }
    }

    // Mention and Slash Command methods
    checkForTriggers() {
        const cursorPosition = this.elements.chatInput.selectionStart;
        const text = this.elements.chatInput.value;
        const char = text[cursorPosition - 1];
        const currentState = this.stateMachine.getState();

        console.log('Checking for triggers at cursor position', cursorPosition, 'character:', char);

        if (currentState === this.stateMachine.states.IDLE ||
            currentState === this.stateMachine.states.TYPING) {
            if (char === '@' && this.isValidTriggerPosition(text, cursorPosition)) {
                console.log('@ trigger detected at position', cursorPosition - 1);
                this.showMentionPopup(cursorPosition - 1);
            } else if (char === '/' && this.isValidTriggerPosition(text, cursorPosition)) {
                console.log('/ trigger detected at position', cursorPosition - 1);
                this.showSlashPopup(cursorPosition - 1);
            }
        } else if (currentState === this.stateMachine.states.MENTION_ACTIVE ||
                  currentState === this.stateMachine.states.SLASH_ACTIVE) {
            this.updateActivePopup(cursorPosition);
        }
    }

    isValidTriggerPosition(text, position) {
        // A trigger is valid at the start of input or after whitespace
        return position === 1 ||
               text[position - 2] === ' ' ||
               text[position - 2] === '\n';
    }

    // Handle cursor position on manual clicks in input field
    handleInputClick() {
        // Update popup position if active
        const currentState = this.stateMachine.getState();
        if (currentState === this.stateMachine.states.MENTION_ACTIVE) {
            this.positionPopup('mention');
        } else if (currentState === this.stateMachine.states.SLASH_ACTIVE) {
            this.positionPopup('slash');
        }

        // Check if cursor moved outside of current mention context
        if (currentState === this.stateMachine.states.MENTION_ACTIVE) {
            const cursorPosition = this.elements.chatInput.selectionStart;
            const context = this.state.mentionContext;
            if (cursorPosition <= context.startPosition) {
                this.hidePopup('mention');
            } else {
                this.updateMentionPopup(cursorPosition);
            }
        }
    }

    // Position popup relative to cursor or input field
    positionPopup(type) {
        const popup = type === 'mention' ? this.elements.mentionPopup : this.elements.slashPopup;
        const inputRect = this.elements.chatInput.getBoundingClientRect();
        const cursorPosition = this.elements.chatInput.selectionStart;
        const context = type === 'mention' ? this.state.mentionContext : this.state.slashContext;

        // Get approximate cursor position
        // This is a basic approach - for accurate cursor positioning, we'd need more complex calculations
        let cursorOffset = 0;
        if (cursorPosition > 0) {
            // Estimate cursor position based on character count
            // This is a simplified approach, doesn't account for variable-width fonts
            const textBeforeCursor = this.elements.chatInput.value.substring(0, cursorPosition);
            const tempElement = document.createElement('span');
            tempElement.style.font = window.getComputedStyle(this.elements.chatInput).font;
            tempElement.style.visibility = 'hidden';
            tempElement.style.position = 'absolute';
            tempElement.textContent = textBeforeCursor;
            document.body.appendChild(tempElement);
            cursorOffset = tempElement.offsetWidth;
            document.body.removeChild(tempElement);
        }

        // Position popup near cursor position
        popup.style.left = (cursorOffset > 0 ? Math.min(cursorOffset, inputRect.width - popup.offsetWidth) : 0) + 'px';
        popup.style.bottom = '100%';
        popup.style.marginBottom = '8px';
    }

    async showMentionPopup(startPosition) {
        console.log('Showing mention popup at position', startPosition);
        // Fetch users from API
        const users = await this.fetchActiveUsers();

        this.state.users = users;
        this.state.mentionContext = {
            active: true,
            startPosition,
            selectedIndex: 0,
            filteredItems: users
        };

        // First transition state, then render popup
        this.stateMachine.transition(this.stateMachine.states.MENTION_ACTIVE);
        this.renderMentionPopup();

        // Position the popup relative to cursor
        this.positionPopup('mention');
    }

    async fetchActiveUsers() {
        try {
            console.log('Fetching active users from API');
            const response = await this.requestManager.fetch('users', '/api/active-users', {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                const users = [];
                const currentUserId = data.current_user_id;

                console.log('Received user data:', data);

                // Process online users
                if (data.online && Array.isArray(data.online)) {
                    data.online.forEach((username, index) => {
                        if (username !== currentUserId) {
                            users.push({
                                id: index + 1,
                                name: username,
                                avatar: username.substring(0, 2).toUpperCase(),
                                online: true
                            });
                        }
                    });
                }

                // Process offline users
                if (data.offline && Array.isArray(data.offline)) {
                    data.offline.forEach((username, index) => {
                        if (username !== currentUserId) {
                            users.push({
                                id: data.online.length + index + 1,
                                name: username,
                                avatar: username.substring(0, 2).toUpperCase(),
                                online: false
                            });
                        }
                    });
                }

                console.log('Processed users:', users);
                return users;
            }
        } catch (error) {
            console.error('Error fetching active users:', error);
        }

        // Fallback to mock data if API call fails
        console.log('Using fallback user data');
        return [
            { id: 1, name: 'alice', avatar: 'AL', online: true },
            { id: 2, name: 'bob', avatar: 'BO', online: true },
            { id: 3, name: 'charlie', avatar: 'CH', online: false },
            { id: 4, name: 'david', avatar: 'DA', online: true },
            { id: 5, name: 'emma', avatar: 'EM', online: false }
        ];
    }

    showSlashPopup(startPosition) {
        this.state.slashContext = {
            active: true,
            startPosition,
            selectedIndex: 0,
            filteredItems: this.state.commands
        };

        this.renderSlashPopup();
        this.stateMachine.transition(this.stateMachine.states.SLASH_ACTIVE);
    }

    updateActivePopup(cursorPosition) {
        const currentState = this.stateMachine.getState();

        if (currentState === this.stateMachine.states.MENTION_ACTIVE) {
            this.updateMentionPopup(cursorPosition);
        } else if (currentState === this.stateMachine.states.SLASH_ACTIVE) {
            this.updateSlashPopup(cursorPosition);
        }
    }

    updateMentionPopup(cursorPosition) {
        const context = this.state.mentionContext;
        const text = this.elements.chatInput.value;

        // Check if cursor is still in the trigger context
        if (text[context.startPosition] !== '@' ||
            (cursorPosition && cursorPosition <= context.startPosition)) {
            this.hidePopup('mention');
            return;
        }

        const filter = text.substring(
            context.startPosition + 1,
            cursorPosition || this.elements.chatInput.selectionStart
        );

        // If a space is typed, it means the mention is complete
        if (filter.includes(' ')) {
            this.hidePopup('mention');
            return;
        }

        // Filter users by the typed text
        context.filteredItems = this.state.users.filter(user =>
            user.name.toLowerCase().includes(filter.toLowerCase())
        );
        context.selectedIndex = 0;

        this.renderMentionPopup();
    }

    updateSlashPopup(cursorPosition) {
        const context = this.state.slashContext;
        const text = this.elements.chatInput.value;

        // Check if cursor is still in the trigger context
        if (text[context.startPosition] !== '/' ||
            (cursorPosition && cursorPosition <= context.startPosition)) {
            this.hidePopup('slash');
            return;
        }

        const filter = text.substring(
            context.startPosition + 1,
            cursorPosition || this.elements.chatInput.selectionStart
        );

        // If a space is typed, it means the command is complete
        if (filter.includes(' ')) {
            this.hidePopup('slash');
            return;
        }

        // Filter commands by the typed text
        context.filteredItems = this.state.commands.filter(cmd =>
            cmd.command.toLowerCase().includes(filter.toLowerCase())
        );
        context.selectedIndex = 0;

        this.renderSlashPopup();
    }

    renderMentionPopup() {
        const context = this.state.mentionContext;
        const popup = this.elements.mentionPopup;

        console.log('Rendering mention popup with items:', context.filteredItems);

        // If no filtered items, hide the popup
        if (!context.filteredItems || context.filteredItems.length === 0) {
            this.hidePopup('mention');
            return;
        }

        // Create DOM elements for each filtered user
        popup.innerHTML = '';

        context.filteredItems.forEach((user, index) => {
            const item = document.createElement('div');
            item.className = `mention-item flex items-center gap-3 p-2.5 cursor-pointer transition-colors duration-150 hover:theme-bg-surface ${index === context.selectedIndex ? 'theme-bg-surface' : ''}`;
            item.dataset.index = index;
            item.dataset.id = user.id;

            item.innerHTML = `
                <div class="mention-avatar relative w-7 h-7 rounded-full theme-bg-primary flex items-center justify-center font-semibold text-white text-sm">
                    ${user.avatar || user.name.substring(0, 2).toUpperCase()}
                    ${user.online ? '<div class="online-indicator absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full theme-bg-success border-2 theme-border"></div>' : ''}
                </div>
                <span class="mention-name theme-text-primary ${user.online ? '' : 'opacity-70'}">${user.name}</span>
            `;

            item.addEventListener('click', () => {
                this.selectPopupItem('mention', user);
            });

            popup.appendChild(item);
        });

        // Make sure popup is visible
        popup.classList.remove('hidden');
    }

    renderSlashPopup() {
        const context = this.state.slashContext;
        const popup = this.elements.slashPopup;

        // If no filtered items, hide the popup
        if (!context.filteredItems || context.filteredItems.length === 0) {
            this.hidePopup('slash');
            return;
        }

        // Create DOM elements for each filtered command
        popup.innerHTML = '';

        context.filteredItems.forEach((cmd, index) => {
            const item = document.createElement('div');
            item.className = `slash-item flex justify-between items-center p-3 cursor-pointer transition-colors duration-150 hover:theme-bg-surface ${index === context.selectedIndex ? 'theme-bg-surface' : ''} border-b theme-border last:border-0`;
            item.dataset.index = index;
            item.dataset.command = cmd.command;

            item.innerHTML = `
                <span class="slash-command font-semibold theme-text-primary text-sm">${cmd.command}</span>
                <span class="slash-description theme-text-secondary text-xs ml-2 text-right">${cmd.description}</span>
            `;

            item.addEventListener('click', () => {
                this.selectPopupItem('slash', cmd);
            });

            popup.appendChild(item);
        });
    }

    setupPopupItemListeners(type) {
        const popup = type === 'mention' ? this.elements.mentionPopup : this.elements.slashPopup;

        popup.addEventListener('click', (e) => {
            const item = e.target.closest(`.${type}-item`);
            if (!item) return;

            const index = parseInt(item.dataset.index, 10);
            const context = type === 'mention' ? this.state.mentionContext : this.state.slashContext;

            if (context.filteredItems[index]) {
                this.selectPopupItem(type, context.filteredItems[index]);
            }
        });
    }

    selectPopupItem(type, item) {
        if (type === 'mention') {
            this.insertMention(item);
        } else {
            this.insertSlashCommand(item);
        }
    }

    insertMention(user) {
        const context = this.state.mentionContext;
        const text = this.elements.chatInput.value;
        const beforeMention = text.substring(0, context.startPosition);
        const afterMention = text.substring(this.elements.chatInput.selectionStart);

        this.elements.chatInput.value = beforeMention + '@' + user.name + ' ' + afterMention;
        const cursorPosition = beforeMention.length + user.name.length + 2; // +2 for @ and space
        this.elements.chatInput.setSelectionRange(cursorPosition, cursorPosition);

        this.hidePopup('mention');
        this.elements.chatInput.focus();
        this.autoResize();
        this.updateSendButton();
    }

    insertSlashCommand(cmd) {
        const context = this.state.slashContext;
        const text = this.elements.chatInput.value;
        const beforeCommand = text.substring(0, context.startPosition);
        const afterCommand = text.substring(this.elements.chatInput.selectionStart);

        // For commands that execute immediately, run them directly
        if (cmd.command === '/clear') {
            this.elements.chatInput.value = beforeCommand + afterCommand;
            this.hidePopup('slash');
            this.handleClearConversation();
            this.autoResize();
            this.updateSendButton();
            this.elements.chatInput.focus();
        } else {
            // For other commands, add them to the input
            this.elements.chatInput.value = beforeCommand + cmd.command + ' ' + afterCommand;
            const cursorPosition = beforeCommand.length + cmd.command.length + 1; // +1 for space
            this.elements.chatInput.setSelectionRange(cursorPosition, cursorPosition);

            this.hidePopup('slash');
            this.elements.chatInput.focus();
            this.autoResize();
            this.updateSendButton();
        }
    }

    navigatePopup(type, direction) {
        const context = type === 'mention' ? this.state.mentionContext : this.state.slashContext;
        const newIndex = context.selectedIndex + direction;

        if (newIndex >= 0 && newIndex < context.filteredItems.length) {
            context.selectedIndex = newIndex;
            if (type === 'mention') {
                this.renderMentionPopup();
            } else {
                this.renderSlashPopup();
            }
        }
    }

    hidePopup(type) {
        // Only log if debug mode is enabled
        if (window.DEBUG_CHAT) {
            console.log(`Hiding ${type} popup`);
        }
        if (type === 'mention') {
            if (this.elements.mentionPopup) {
                this.elements.mentionPopup.classList.add('hidden');
            }
            this.state.mentionContext.active = false;
        } else {
            if (this.elements.slashPopup) {
                this.elements.slashPopup.classList.add('hidden');
            }
            this.state.slashContext.active = false;
        }

        const currentState = this.stateMachine.getState();
        if (currentState === this.stateMachine.states.MENTION_ACTIVE ||
            currentState === this.stateMachine.states.SLASH_ACTIVE) {
            this.stateMachine.transition(this.stateMachine.states.IDLE);
        }
    }

    extractMentions(message) {
        const mentionPattern = /@([a-zA-Z0-9_-]+)(?=\s|$|[.,!?])/g;
        const mentions = [];
        let match;

        while ((match = mentionPattern.exec(message)) !== null) {
            const mention = match[1].trim();
            if (mention && !mentions.includes(mention)) {
                mentions.push(mention);
            }
        }

        return mentions;
    }

    getSlashCommands() {
        return [
            { command: '/clear', description: 'Clear the conversation history' },
            { command: '/help', description: 'Show available commands' },
            { command: '/model', description: 'Change the AI model' },
            { command: '/settings', description: 'Open settings' },
            { command: '/theme', description: 'Toggle light/dark theme' },
            { command: '/map', description: 'Open map view' }
        ];
    }

    // Clear conversation
    async handleClearConversation() {
        try {
            const response = await this.requestManager.fetch('clear', '/api/clear-conversation', {
                method: 'POST',
                credentials: 'same-origin'
            });

            if (response.ok) {
                // Clear chat messages
                this.elements.chatMessages.innerHTML = '';

                // Check visibility to show placeholder
                this.checkMessageVisibility();

                // Add a system message indicating conversation was cleared
                this.addMessage('Conversation has been cleared.', false);

                console.log('Conversation cleared successfully');
            } else {
                console.error('Failed to clear conversation:', response.status);
                this.showError('Failed to clear conversation');
            }
        } catch (error) {
            console.error('Error clearing conversation:', error);
            this.showError('Failed to clear conversation');
        }
    }

    // Map placeholder methods
    initializeMapPlaceholder() {
        if (this.state.mapInitialized) return;

        const worldMapImg = document.getElementById('world-map-placeholder');
        if (!worldMapImg) return;

        // Apply theme and place dots when image loads
        if (worldMapImg.complete) {
            this.applyMapTheme();
            this.placeMapUserDots();
        } else {
            worldMapImg.onload = () => {
                this.applyMapTheme();
                this.placeMapUserDots();
            };
        }

        // Also apply theme immediately in case image is cached
        this.applyMapTheme();

        // Handle resize
        this.eventManager.addEventListener(window, 'resize', () => {
            clearTimeout(this.state.mapResizeTimeout);
            this.state.mapResizeTimeout = setTimeout(() => this.placeMapUserDots(), 100);
        });

        // Listen for theme changes
        this.eventManager.addEventListener(window, 'themechange', () => {
            this.applyMapTheme();
        });

        // Observe attribute changes for theme detection
        this.state.mapObserver = new MutationObserver(() => {
            this.applyMapTheme();
        });

        this.state.mapObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme', 'class']
        });

        this.state.mapObserver.observe(document.body, {
            attributes: true,
            attributeFilter: ['class']
        });

        this.state.mapInitialized = true;
    }

    applyMapTheme() {
        const worldMapImg = document.getElementById('world-map-placeholder');
        if (!worldMapImg) return;

        // Check multiple ways to detect dark mode
        const isDarkMode =
            document.documentElement.getAttribute('data-theme') === 'dark' ||
            document.body.classList.contains('uk-dark') ||
            document.body.classList.contains('dark') ||
            (window.appTheme && window.appTheme.currentMode === 'dark');

        // Debug logging
        console.log('Map theme detection:', {
            dataTheme: document.documentElement.getAttribute('data-theme'),
            bodyClasses: document.body.className,
            ukDark: document.body.classList.contains('uk-dark'),
            appTheme: window.appTheme?.currentMode,
            isDarkMode: isDarkMode
        });

        if (isDarkMode) {
            // Dark mode: blue/purple tinted
            worldMapImg.style.filter = 'grayscale(0%) brightness(0.8) contrast(1) saturate(1) hue-rotate(250deg)';
            worldMapImg.style.opacity = '0.6';
        } else {
            // Light mode: red/sepia
            worldMapImg.style.filter = 'brightness(0.8) contrast(1.4) saturate(1.5) hue-rotate(0deg) sepia(1)';
            worldMapImg.style.opacity = '0.8';
        }
    }

    geoToPixel(lng, lat, mapWidth, mapHeight) {
        // Simple equirectangular projection
        // This matches better with the Wikimedia world map SVG

        // Convert longitude (-180 to 180) to x coordinate (0 to mapWidth)
        const x = (lng + 180) * (mapWidth / 360);

        // Convert latitude (90 to -90) to y coordinate (0 to mapHeight)
        // Note: y increases downward in screen coordinates
        const y = (90 - lat) * (mapHeight / 180);

        // Apply small adjustments for the clipped map (12% clipped from bottom)
        // Adjust y coordinate to account for the clipping
        const adjustedY = y * 0.88; // Since 12% is clipped from bottom

        return { x, y: adjustedY };
    }

    placeMapUserDots() {
        const mapContainer = document.getElementById('map-container-placeholder');
        const worldMap = document.getElementById('world-map-placeholder');

        if (!mapContainer || !worldMap) return;

        const mapWidth = worldMap.clientWidth;
        const mapHeight = worldMap.clientHeight;

        // Sample user data
        const users = [
            { id: 'alice', name: 'Alice', lat: 37.7749, lon: -122.4194 }, // San Francisco
            { id: 'bob', name: 'Bob', lat: 51.5074, lon: -0.1278 }, // London
            { id: 'charlie', name: 'Charlie', lat: 35.6762, lon: 139.6503 }, // Tokyo
            { id: 'david', name: 'David', lat: -33.8688, lon: 151.2093 }, // Sydney
            { id: 'emma', name: 'Emma', lat: 52.5200, lon: 13.4050 }, // Berlin
            { id: 'frank', name: 'Frank', lat: 40.7128, lon: -74.0060 }, // New York
            { id: 'grace', name: 'Grace', lat: 1.3521, lon: 103.8198 }, // Singapore
            { id: 'henry', name: 'Henry', lat: -23.5505, lon: -46.6333 }, // São Paulo
            { id: 'iris', name: 'Iris', lat: 19.4326, lon: -99.1332 }, // Mexico City
            { id: 'jack', name: 'Jack', lat: 55.7558, lon: 37.6173 }, // Moscow
        ];

        // Remove existing dots
        mapContainer.querySelectorAll('.user-dot-placeholder, .user-tooltip-placeholder').forEach(el => el.remove());

        // Add dots for each user
        users.forEach((user, index) => {
            const position = this.geoToPixel(user.lon, user.lat, mapWidth, mapHeight);

            // Skip if position is invalid
            if (position.x < 0 || position.y < 0) return;

            const dot = document.createElement('div');
            dot.className = 'user-dot-placeholder';
            dot.style.left = `${position.x}px`;
            dot.style.top = `${position.y}px`;

            // Staggered entrance animation
            dot.style.opacity = '0';
            dot.style.transform = 'translate(-50%, -50%) scale(0)';
            setTimeout(() => {
                dot.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                dot.style.opacity = '1';
                dot.style.transform = 'translate(-50%, -50%) scale(1)';
                // Add pulse animation after entrance
                setTimeout(() => {
                    dot.style.animation = `pulse-dot 3s infinite`;
                    dot.style.animationDelay = `${Math.random() * 3}s`;
                }, 500);
            }, index * 100); // Stagger by 100ms per dot

            const tooltip = document.createElement('div');
            tooltip.className = 'user-tooltip-placeholder';
            tooltip.textContent = `${user.name}`;
            tooltip.style.left = `${position.x}px`;
            tooltip.style.top = `${position.y + 15}px`;

            mapContainer.appendChild(dot);
            mapContainer.appendChild(tooltip);
        });

        // Update stats with animation
        const activeUsersEl = document.getElementById('active-users-placeholder');

        if (activeUsersEl) {
            const currentValue = parseInt(activeUsersEl.textContent) || 0;
            const newValue = users.length;
            if (currentValue !== newValue) {
                activeUsersEl.style.transition = 'transform 0.3s ease';
                activeUsersEl.style.transform = 'scale(1.2)';
                activeUsersEl.textContent = newValue;
                setTimeout(() => {
                    activeUsersEl.style.transform = 'scale(1)';
                }, 300);
            }
        }
    }

    // Cleanup
    destroy() {
        this.requestManager.cancelAll();
        this.eventManager.removeAllListeners();

        // Clean up map observer
        if (this.state.mapObserver) {
            this.state.mapObserver.disconnect();
            this.state.mapObserver = null;
        }

        // Clear map resize timeout
        if (this.state.mapResizeTimeout) {
            clearTimeout(this.state.mapResizeTimeout);
        }
    }
}

// Initialize the chat application
window.initializeChatApp = function initializeChatApp() {
    // Clean up existing instance if it exists
    if (window.chatApp) {
        console.log('Cleaning up existing chat application...');
        window.chatApp.destroy();
        window.chatApp = null;
    }

    // Create the global chat instance
    console.log('Initializing chat application...');
    try {
        window.chatApp = new ChatApplication();
        console.log('Chat application initialized successfully');
        // Log DOM elements for debugging
        console.log('Chat input element:', document.getElementById('chat-input'));
        console.log('Send button element:', document.getElementById('send-message'));
    } catch (error) {
        console.error('Error initializing chat application:', error);
    }

    // Setup cleanup on page unload (only once)
    if (!window.chatAppCleanupAdded) {
        window.addEventListener('beforeunload', () => {
            if (window.chatApp) {
                window.chatApp.destroy();
            }
        });
        window.chatAppCleanupAdded = true;
    }
}

// Initialize immediately when the script loads, but only if not already done
if (!window.chatAppInitialized) {
    initializeChatApp();
    window.chatAppInitialized = true;
}

} // End of script loading protection
