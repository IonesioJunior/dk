/**
 * LLM Dropdowns Component
 * Manages provider and model selection dropdowns with API integration
 */

class LLMDropdowns {
    constructor() {
        // State management
        this.state = {
            selectedProvider: 'anthropic',
            selectedModel: 'claude-3-sonnet',
            models: [],
            providerModels: null,
            apiTokens: {
                anthropic: '',
                openai: '',
                openrouter: ''
            },
            pendingProviderChange: null
        };

        // DOM elements
        this.elements = {
            providerContainer: null,
            modelContainer: null,
            providerDropdown: null,
            modelDropdown: null,
            selectedProviderText: null,
            selectedModelText: null,
            apiTokenModal: null
        };

        // Request manager for API calls
        this.activeRequests = new Map();
    }

    /**
     * Initialize the LLM dropdowns
     */
    async init() {
        console.log('Initializing LLM dropdowns...');

        // Get container elements
        this.elements.providerContainer = document.getElementById('header-provider-dropdown');
        this.elements.modelContainer = document.getElementById('header-model-dropdown');

        if (!this.elements.providerContainer || !this.elements.modelContainer) {
            console.warn('LLM dropdown containers not found');
            return;
        }

        // Create dropdown HTML
        this.createDropdownHTML();

        // Create API token modal
        this.createApiTokenModal();

        // Set up event listeners
        this.setupEventListeners();

        // Load initial configuration
        await this.loadProviderConfig();

        console.log('LLM dropdowns initialized');
    }

    /**
     * Create dropdown HTML structure
     */
    createDropdownHTML() {
        // Provider dropdown using consistent structure matching chat.html style
        this.elements.providerContainer.innerHTML = `
            <div class="uk-inline dropdown-component" id="provider-dropdown-container">
                <button id="provider-dropdown-toggle"
                        class="flex items-center justify-between gap-2 px-3.5 py-1.5 text-sm font-medium theme-text-primary bg-transparent hover:theme-bg-surface border-0 rounded-xl transition-all duration-200 ease-in-out cursor-pointer"
                        style="height: 36px; min-width: 150px;"
                        type="button">
                    <div class="flex items-center gap-2">
                        <i data-lucide="server" class="w-4 h-4"></i>
                        <span id="selected-provider" class="truncate dropdown-toggle-text">Loading...</span>
                    </div>
                    <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-200 ease-in-out dropdown-arrow"></i>
                </button>

                <div id="provider-dropdown-content"
                     uk-dropdown="mode: click; pos: bottom-left; animation: uk-animation-slide-top-small; duration: 200"
                     class="theme-bg-surface border theme-border rounded-xl shadow-lg min-w-40 max-h-60 overflow-y-auto p-2 dropdown-menu w-48">
                    <ul class="uk-nav uk-dropdown-nav pl-0" id="provider-dropdown">
                        <!-- Providers will be dynamically populated -->
                    </ul>
                </div>
            </div>
        `;

        // Model dropdown using consistent structure matching chat.html style
        this.elements.modelContainer.innerHTML = `
            <div class="uk-inline dropdown-component" id="model-dropdown-container">
                <button id="model-dropdown-toggle"
                        class="flex items-center justify-between gap-2 px-3.5 py-1.5 text-sm font-medium theme-text-primary bg-transparent hover:theme-bg-surface border-0 rounded-xl transition-all duration-200 ease-in-out cursor-pointer"
                        style="height: 36px; min-width: 200px;"
                        type="button">
                    <div class="flex items-center gap-2">
                        <i data-lucide="cpu" class="w-4 h-4"></i>
                        <span id="selected-model" class="truncate dropdown-toggle-text">Loading...</span>
                    </div>
                    <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-200 ease-in-out dropdown-arrow"></i>
                </button>

                <div id="model-dropdown-content"
                     uk-dropdown="mode: click; pos: bottom-left; animation: uk-animation-slide-top-small; duration: 200"
                     class="theme-bg-surface border theme-border rounded-xl shadow-lg min-w-40 max-h-60 overflow-y-auto p-2 dropdown-menu w-64">
                    <ul class="uk-nav uk-dropdown-nav pl-0" id="model-dropdown">
                        <!-- Models will be dynamically populated -->
                    </ul>
                </div>
            </div>
        `;

        // Get references to created elements
        this.elements.providerDropdown = document.getElementById('provider-dropdown');
        this.elements.modelDropdown = document.getElementById('model-dropdown');
        this.elements.selectedProviderText = document.getElementById('selected-provider');
        this.elements.selectedModelText = document.getElementById('selected-model');
        this.elements.providerDropdownContent = document.getElementById('provider-dropdown-content');
        this.elements.modelDropdownContent = document.getElementById('model-dropdown-content');

        // Initialize icons
        if (window.lucide) {
            lucide.createIcons();
        }

        // Setup dropdown arrow rotation on UIKit events
        this.setupDropdownArrowRotation();
    }

    /**
     * Setup dropdown arrow rotation based on UIKit state
     */
    setupDropdownArrowRotation() {
        // Provider dropdown
        const providerContainer = document.getElementById('provider-dropdown-container');
        const providerContent = this.elements.providerDropdownContent;

        if (providerContainer && providerContent && UIkit) {
            UIkit.util.on(providerContent, 'show', () => {
                providerContainer.classList.add('uk-open');
            });

            UIkit.util.on(providerContent, 'hide', () => {
                providerContainer.classList.remove('uk-open');
            });
        }

        // Model dropdown
        const modelContainer = document.getElementById('model-dropdown-container');
        const modelContent = this.elements.modelDropdownContent;

        if (modelContainer && modelContent && UIkit) {
            UIkit.util.on(modelContent, 'show', () => {
                modelContainer.classList.add('uk-open');
            });

            UIkit.util.on(modelContent, 'hide', () => {
                modelContainer.classList.remove('uk-open');
            });
        }
    }

    /**
     * Create API token modal
     */
    createApiTokenModal() {
        const modalHTML = `
            <div class="modal-overlay uk-modal" id="api-token-modal" uk-modal>
                <div class="uk-modal-dialog uk-modal-body">
                    <button class="uk-modal-close-default" type="button" uk-close></button>
                    <h3 class="uk-modal-title">API Token Required</h3>
                    <p class="uk-text-muted">Please enter your API token for <span id="modal-provider-name"></span>:</p>
                    <div class="uk-margin">
                        <input type="password" class="uk-input" id="api-token-input"
                               placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx">
                    </div>
                    <p class="uk-text-small uk-text-muted" id="modal-help-text"></p>
                    <div class="uk-text-right">
                        <button class="uk-button uk-button-default uk-modal-close" type="button">Cancel</button>
                        <button class="uk-button uk-button-primary" id="modal-save" type="button">Save</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.elements.apiTokenModal = UIkit.modal('#api-token-modal');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Modal save button
        const modalSaveBtn = document.getElementById('modal-save');
        modalSaveBtn.addEventListener('click', () => this.saveApiToken());

        // Enter key in token input
        const tokenInput = document.getElementById('api-token-input');
        tokenInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.saveApiToken();
            }
        });
    }

    /**
     * Load provider configuration from API
     */
    async loadProviderConfig() {
        try {
            const response = await this.fetch('provider-config', '/api/config/provider', {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const config = await response.json();
                this.applyProviderConfig(config);
            }
        } catch (error) {
            console.error('Error loading provider config:', error);
            // Apply fallback configuration
            this.applyFallbackConfig();
        }
    }

    /**
     * Apply provider configuration
     */
    applyProviderConfig(config) {
        if (!config || !config.current_config) return;

        const currentConfig = config.current_config;

        // Update available providers and models
        if (config.providers) {
            this.state.providerModels = config.providers;
            this.renderProviderDropdown();
        }

        // Update provider selection
        if (currentConfig.provider) {
            this.state.selectedProvider = currentConfig.provider;
            this.elements.selectedProviderText.textContent = this.formatProviderName(currentConfig.provider);
        }

        // Update models for current provider
        if (currentConfig.provider && config.providers && config.providers[currentConfig.provider]) {
            const models = config.providers[currentConfig.provider];
            this.state.models = models.map(modelId => ({
                id: modelId,
                name: this.formatModelName(modelId),
                description: ''
            }));

            this.renderModelDropdown();

            // Set current model
            if (currentConfig.model && models.includes(currentConfig.model)) {
                this.state.selectedModel = currentConfig.model;
                this.elements.selectedModelText.textContent = this.formatModelName(currentConfig.model);
            }
        }
    }

    /**
     * Apply fallback configuration when API fails
     */
    applyFallbackConfig() {
        // Default provider models
        this.state.providerModels = {
            anthropic: ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229', 'claude-3-5-sonnet-20241022'],
            openai: ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
            ollama: ['llama-3.1-70b', 'mixtral-8x7b', 'llama-2-7b', 'codellama-34b'],
            openrouter: ['claude-3-sonnet', 'gpt-4', 'llama-3.1-70b', 'mistral-medium']
        };

        this.renderProviderDropdown();
        this.state.models = this.getModelsForProvider(this.state.selectedProvider);
        this.renderModelDropdown();

        // Update UI
        this.elements.selectedProviderText.textContent = this.formatProviderName(this.state.selectedProvider);
        this.elements.selectedModelText.textContent = this.formatModelName(this.state.selectedModel);
    }

    /**
     * Render provider dropdown
     */
    renderProviderDropdown() {
        if (!this.state.providerModels) return;

        let html = '';

        Object.keys(this.state.providerModels).forEach(provider => {
            const isSelected = provider === this.state.selectedProvider;
            const icon = this.getProviderIcon(provider);
            html += `
                <li>
                    <a href="#"
                       data-dropdown-item
                       data-provider="${provider}"
                       class="uk-flex items-center py-1 pl-6 pr-4 rounded-md hover:theme-bg-surface theme-text-primary transition-colors duration-150 ${isSelected ? 'font-semibold theme-bg-primary text-white' : ''}"
                       style="text-decoration: none;">
                        <span>${this.formatProviderName(provider)}</span>
                    </a>
                </li>
            `;
        });

        this.elements.providerDropdown.innerHTML = html;

        // Re-initialize icons
        if (window.lucide) {
            lucide.createIcons({ container: this.elements.providerDropdown });
        }

        // Add click handlers
        this.elements.providerDropdown.querySelectorAll('[data-dropdown-item]').forEach(item => {
            item.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.selectProvider(item.dataset.provider);
            });
        });
    }

    /**
     * Render model dropdown
     */
    renderModelDropdown() {
        let html = '';

        this.state.models.forEach(model => {
            const isSelected = model.id === this.state.selectedModel;
            html += `
                <li>
                    <a href="#"
                       data-dropdown-item
                       data-model="${model.id}"
                       class="uk-flex items-center py-1 pl-6 pr-4 rounded-md hover:theme-bg-surface theme-text-primary transition-colors duration-150 ${isSelected ? 'font-semibold theme-bg-primary text-white' : ''}"
                       style="text-decoration: none;">
                        <span>${model.name}</span>
                    </a>
                </li>
            `;
        });

        this.elements.modelDropdown.innerHTML = html;

        // Add click handlers
        this.elements.modelDropdown.querySelectorAll('[data-dropdown-item]').forEach(item => {
            item.addEventListener('click', async (e) => {
                e.preventDefault();
                const model = this.state.models.find(m => m.id === item.dataset.model);
                if (model) {
                    await this.selectModel(model.id, model.name);
                }
            });
        });
    }

    /**
     * Select a provider
     */
    async selectProvider(provider) {
        // Close the dropdown
        UIkit.dropdown(this.elements.providerDropdownContent).hide();

        if (provider === 'ollama') {
            // For Ollama, patch config immediately (no token needed)
            await this.patchProviderConfiguration(provider);
        } else if (this.state.apiTokens[provider]) {
            // If we already have a token, proceed
            this.confirmProviderChange(provider);
        } else {
            // Show modal to ask for API token
            this.state.pendingProviderChange = provider;
            this.showApiTokenModal(provider);
        }
    }

    /**
     * Confirm provider change
     */
    confirmProviderChange(provider) {
        this.state.selectedProvider = provider;
        this.elements.selectedProviderText.textContent = this.formatProviderName(provider);

        // Re-render the dropdown to update selected state
        this.renderProviderDropdown();

        // Update available models
        this.state.models = this.getModelsForProvider(provider);
        this.renderModelDropdown();

        // Reset model selection
        this.resetModelSelection();
    }

    /**
     * Select a model
     */
    async selectModel(modelId, modelName) {
        const previousModel = this.state.selectedModel;
        this.state.selectedModel = modelId;
        this.elements.selectedModelText.textContent = modelName;

        // Re-render the dropdown to update selected state
        this.renderModelDropdown();

        // Close dropdown
        UIkit.dropdown(this.elements.modelDropdownContent).hide();

        // If model changed, patch configuration
        if (previousModel !== modelId) {
            const apiToken = this.state.apiTokens[this.state.selectedProvider] || null;
            await this.patchProviderConfiguration(this.state.selectedProvider, apiToken);
        }
    }

    /**
     * Reset model selection
     */
    resetModelSelection() {
        // Try to keep current model if available
        const currentModelAvailable = this.state.models.find(m => m.id === this.state.selectedModel);
        if (currentModelAvailable) {
            this.selectModel(currentModelAvailable.id, currentModelAvailable.name);
            return;
        }

        // Otherwise set default model
        const defaultModels = {
            'anthropic': 'claude-3-5-sonnet-20241022',
            'openai': 'gpt-4',
            'ollama': 'llama-3.1-70b',
            'openrouter': 'claude-3-5-sonnet-20241022'
        };

        const defaultModelId = defaultModels[this.state.selectedProvider];
        const availableModel = this.state.models.find(m => m.id === defaultModelId);

        if (availableModel) {
            this.selectModel(availableModel.id, availableModel.name);
        } else if (this.state.models.length > 0) {
            const firstModel = this.state.models[0];
            this.selectModel(firstModel.id, firstModel.name);
        }
    }

    /**
     * Show API token modal
     */
    showApiTokenModal(provider) {
        const modalProviderName = document.getElementById('modal-provider-name');
        const apiTokenInput = document.getElementById('api-token-input');
        const modalHelpText = document.getElementById('modal-help-text');

        modalProviderName.textContent = this.formatProviderName(provider);
        apiTokenInput.value = this.state.apiTokens[provider] || '';

        // Set help text
        const helpText = {
            anthropic: 'Get your API key from console.anthropic.com/api-keys',
            openai: 'Get your API key from platform.openai.com/api-keys',
            openrouter: 'Get your API key from openrouter.ai/keys'
        };

        modalHelpText.textContent = helpText[provider] || 'Enter your API key for authentication.';

        // Show modal
        this.elements.apiTokenModal.show();
        apiTokenInput.focus();
    }

    /**
     * Save API token
     */
    async saveApiToken() {
        const provider = this.state.pendingProviderChange;
        const token = document.getElementById('api-token-input').value.trim();

        if (!token) {
            if (window.Toaster) {
                window.Toaster.error('Please enter a valid API token');
            } else {
                UIkit.notification('Please enter a valid API token', {status: 'danger', pos: 'bottom-right'});
            }
            return;
        }

        // Save token to state
        this.state.apiTokens[provider] = token;

        // Hide modal
        this.elements.apiTokenModal.hide();

        // Patch configuration
        await this.patchProviderConfiguration(provider, token);
    }

    /**
     * Patch provider configuration
     */
    async patchProviderConfiguration(provider, apiToken = null) {
        try {
            // Get appropriate model
            let model = '';

            if (provider !== this.state.selectedProvider) {
                // Switching providers - get first available model
                if (this.state.providerModels && this.state.providerModels[provider] && this.state.providerModels[provider].length > 0) {
                    model = this.state.providerModels[provider][0];
                } else {
                    // Fallback defaults
                    const defaultModels = {
                        'anthropic': 'claude-3-sonnet-20240229',
                        'openai': 'gpt-4',
                        'ollama': 'llama3.2:3b-instruct-fp16',
                        'openrouter': 'claude-3-sonnet'
                    };
                    model = defaultModels[provider] || '';
                }
            } else {
                // Use currently selected model
                model = this.state.selectedModel;
            }

            // Build configuration
            const config = {
                provider: provider,
                model: model,
                parameters: {
                    temperature: 0.7
                }
            };

            if (apiToken) {
                config.api_key = apiToken;
            }

            // Make PATCH request
            const response = await this.fetch('patch-config', '/api/config/provider', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                // Configuration saved successfully
                this.confirmProviderChange(provider);

                // Reload provider configuration
                const updatedConfig = await this.fetchProviderConfig();
                if (updatedConfig) {
                    this.applyProviderConfig(updatedConfig);
                }

                if (window.Toaster) {
                    window.Toaster.success('Configuration updated successfully');
                } else {
                    UIkit.notification('Configuration updated successfully', {status: 'success', pos: 'bottom-right'});
                }
            } else {
                if (window.Toaster) {
                    window.Toaster.error('Failed to save configuration: ' + (result.message || 'Unknown error'));
                } else {
                    UIkit.notification('Failed to save configuration: ' + (result.message || 'Unknown error'), {status: 'danger', pos: 'bottom-right'});
                }
            }
        } catch (error) {
            console.error('Error patching provider configuration:', error);
            if (window.Toaster) {
                window.Toaster.error('Failed to save configuration');
            } else {
                UIkit.notification('Failed to save configuration', {status: 'danger', pos: 'bottom-right'});
            }
        }
    }

    /**
     * Fetch with cancellation support
     */
    async fetch(id, url, options = {}) {
        // Cancel any existing request with same ID
        if (this.activeRequests.has(id)) {
            this.activeRequests.get(id).abort();
        }

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
            if (error.name === 'AbortError') {
                throw error;
            }
            throw error;
        }
    }

    /**
     * Fetch provider configuration
     */
    async fetchProviderConfig() {
        try {
            const response = await this.fetch('provider-config', '/api/config/provider', {
                credentials: 'same-origin'
            });

            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error fetching provider config:', error);
            }
        }
        return null;
    }

    /**
     * Get models for a provider
     */
    getModelsForProvider(provider) {
        if (this.state.providerModels && this.state.providerModels[provider]) {
            return this.state.providerModels[provider].map(modelId => ({
                id: modelId,
                name: this.formatModelName(modelId),
                description: ''
            }));
        }

        // Fallback models
        const fallbackModels = {
            anthropic: [
                { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', description: 'Most balanced' },
                { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', description: 'Most powerful' },
                { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', description: 'Fastest' }
            ],
            openai: [
                { id: 'gpt-4', name: 'GPT-4', description: 'Most capable' },
                { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast and capable' }
            ],
            ollama: [
                { id: 'llama-3.1-70b', name: 'Llama 3.1 70B', description: 'Large model' },
                { id: 'mixtral-8x7b', name: 'Mixtral 8x7B', description: 'MoE architecture' }
            ],
            openrouter: [
                { id: 'claude-3-sonnet', name: 'Claude 3.5 Sonnet', description: 'Via OpenRouter' },
                { id: 'gpt-4', name: 'GPT-4', description: 'Via OpenRouter' }
            ]
        };

        return fallbackModels[provider] || [];
    }

    /**
     * Get provider icon
     */
    getProviderIcon(provider) {
        const icons = {
            anthropic: 'brain',
            openai: 'sparkles',
            ollama: 'server',
            openrouter: 'globe'
        };
        return icons[provider] || 'cpu';
    }

    /**
     * Format provider name for display
     */
    formatProviderName(provider) {
        return provider.charAt(0).toUpperCase() + provider.slice(1);
    }

    /**
     * Format model name for display
     */
    formatModelName(modelId) {
        const modelNames = {
            'claude-3-haiku-20240307': 'Claude 3 Haiku',
            'claude-3-sonnet-20240229': 'Claude 3 Sonnet',
            'claude-3-opus-20240229': 'Claude 3 Opus',
            'claude-3-5-sonnet-20241022': 'Claude 3.5 Sonnet',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo',
            'gpt-4': 'GPT-4',
            'gpt-4-turbo': 'GPT-4 Turbo',
            'llama-3.1-70b': 'Llama 3.1 70B',
            'mixtral-8x7b': 'Mixtral 8x7B',
            'llama-2-7b': 'Llama 2 7B',
            'codellama-34b': 'Code Llama 34B'
        };

        return modelNames[modelId] || modelId;
    }

    /**
     * Get current configuration
     */
    getConfig() {
        return {
            provider: this.state.selectedProvider,
            model: this.state.selectedModel,
            apiToken: this.state.apiTokens[this.state.selectedProvider] || ''
        };
    }

    /**
     * Destroy the component
     */
    destroy() {
        // Cancel all active requests
        this.activeRequests.forEach(controller => controller.abort());
        this.activeRequests.clear();
    }
}

// Export as global
window.LLMDropdowns = LLMDropdowns;
