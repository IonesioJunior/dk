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
        // Get container elements
        this.elements.providerContainer = document.getElementById('header-provider-dropdown');
        this.elements.modelContainer = document.getElementById('header-model-dropdown');

        if (!this.elements.providerContainer || !this.elements.modelContainer) {
            console.warn('LLM dropdown containers not found');
            return;
        }

        // Remove any existing modal before creating new one
        const existingModal = document.getElementById('api-token-modal-overlay');
        if (existingModal) {
            existingModal.remove();
        }

        // Create dropdown HTML
        this.createDropdownHTML();

        // Create API token modal
        this.createApiTokenModal();

        // Set up event listeners
        this.setupEventListeners();

        // Load initial configuration
        await this.loadProviderConfig();
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
            <!-- Custom Modal Overlay -->
            <div id="api-token-modal-overlay" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center p-4 transition-opacity duration-300" style="backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);">
                <!-- Modal Container matching upload modal style -->
                <div id="api-token-modal" class="theme-bg-surface rounded-xl border-0 max-w-2xl w-full max-h-[90vh] overflow-hidden transform transition-all duration-300 scale-95 opacity-0" style="box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); border-radius: 0.75rem !important;">
                    <!-- Modal Body -->
                    <div class="p-8 relative" style="padding: 2rem;">
                        <!-- Close Button -->
                        <button type="button"
                                id="modal-close-btn"
                                class="absolute top-6 right-6 p-2 rounded-lg hover:theme-bg-background transition-colors duration-200">
                            <i data-lucide="x" class="h-5 w-5 theme-text-secondary"></i>
                        </button>

                        <!-- Modal Header -->
                        <div class="mb-6">
                            <h2 class="text-2xl font-semibold theme-text-primary">API Token Required</h2>
                        </div>

                        <form class="space-y-6">
                            <!-- Provider Info Section -->
                            <div>
                                <label class="block text-sm font-medium theme-text-primary mb-3">Provider Configuration</label>
                                <div class="theme-bg-background rounded-xl p-6">
                                    <div class="flex items-start space-x-4">
                                        <div class="p-3 rounded-full transition-all duration-200" style="background-color: rgba(var(--color-primary-rgb, 30, 136, 229), 0.1);">
                                            <i data-lucide="key" class="h-8 w-8 theme-primary"></i>
                                        </div>
                                        <div class="flex-1">
                                            <h3 class="text-lg font-medium theme-text-primary mb-2">Configure <span id="modal-provider-name" class="font-semibold"></span></h3>
                                            <p class="text-sm theme-text-secondary mb-1">Enter your API token to enable this provider.</p>
                                            <p class="text-xs theme-text-muted">Your token will be stored securely and used only for API authentication.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Token Input Section -->
                            <div>
                                <label for="api-token-input" class="block text-sm font-medium theme-text-primary mb-3">API Token</label>
                                <div class="relative">
                                    <input type="password"
                                           class="w-full px-4 py-3 pr-12 theme-bg-background theme-text-primary border theme-border rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           id="api-token-input"
                                           placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                                           style="font-family: 'Monaco', 'Consolas', 'Courier New', monospace;">
                                    <button type="button"
                                            class="absolute right-3 top-1/2 transform -translate-y-1/2 p-2 rounded hover:theme-bg-surface transition-colors duration-200"
                                            id="toggle-token-visibility"
                                            title="Toggle visibility">
                                        <i data-lucide="eye" class="h-4 w-4 theme-text-secondary"></i>
                                    </button>
                                </div>
                            </div>

                            <!-- Help Text Section -->
                            <div class="theme-bg-background rounded-xl p-4">
                                <div class="flex items-start space-x-3">
                                    <i data-lucide="info" class="h-4 w-4 theme-text-secondary mt-0.5"></i>
                                    <div class="flex-1">
                                        <p class="text-sm theme-text-secondary" id="modal-help-text"></p>
                                    </div>
                                </div>
                            </div>

                            <!-- Form Actions -->
                            <div class="flex items-center justify-end space-x-3 pt-6 theme-border border-t">
                                <button type="button"
                                        class="px-4 py-2 text-sm font-medium theme-text-primary theme-bg-surface theme-border border rounded-lg hover:theme-bg-background transition-colors duration-200"
                                        style="border-radius: 0.5rem !important;"
                                        id="modal-cancel-btn">
                                    Cancel
                                </button>
                                <button type="button"
                                        class="px-6 py-2 text-sm font-medium text-white theme-bg-primary hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all duration-200 flex items-center space-x-2"
                                        style="box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); border-radius: 0.5rem !important; background-color: var(--color-primary) !important;"
                                        id="modal-save"
                                        disabled>
                                    <span class="save-text">Save Token</span>
                                    <div class="saving-text hidden">
                                        <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    </div>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Store modal reference with custom methods
        this.elements.apiTokenModal = {
            overlay: document.getElementById('api-token-modal-overlay'),
            modal: document.getElementById('api-token-modal'),
            isOpen: false,
            show: () => this.showModal(),
            hide: () => this.hideModal(),
            $el: document.getElementById('api-token-modal-overlay')
        };

        // Initialize Lucide icons for the modal
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    /**
     * Show modal with animation
     */
    showModal() {
        const { overlay, modal } = this.elements.apiTokenModal;

        // Show overlay
        overlay.classList.remove('hidden');

        // Trigger animation
        requestAnimationFrame(() => {
            overlay.classList.add('opacity-100');
            modal.classList.remove('scale-95', 'opacity-0');
            modal.classList.add('scale-100', 'opacity-100');
        });

        this.elements.apiTokenModal.isOpen = true;

        // Dispatch custom event
        const event = new CustomEvent('shown');
        this.elements.apiTokenModal.$el.dispatchEvent(event);
    }

    /**
     * Hide modal with animation
     */
    hideModal() {
        const { overlay, modal } = this.elements.apiTokenModal;

        // Trigger hide animation
        overlay.classList.remove('opacity-100');
        modal.classList.remove('scale-100', 'opacity-100');
        modal.classList.add('scale-95', 'opacity-0');

        // Hide after animation
        setTimeout(() => {
            overlay.classList.add('hidden');
            this.elements.apiTokenModal.isOpen = false;
        }, 300);
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Modal save button
        const modalSaveBtn = document.getElementById('modal-save');
        if (modalSaveBtn) {
            modalSaveBtn.addEventListener('click', () => this.saveApiToken());
        }

        // Modal cancel button
        const modalCancelBtn = document.getElementById('modal-cancel-btn');
        if (modalCancelBtn) {
            modalCancelBtn.addEventListener('click', () => this.hideModal());
        }

        // Modal close button
        const modalCloseBtn = document.getElementById('modal-close-btn');
        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', () => this.hideModal());
        }

        // Click outside to close
        const modalOverlay = document.getElementById('api-token-modal-overlay');
        if (modalOverlay) {
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    this.hideModal();
                }
            });
        }

        // Token input field
        const tokenInput = document.getElementById('api-token-input');
        if (tokenInput) {
            // Enable/disable save button based on input
            tokenInput.addEventListener('input', (e) => {
                const hasValue = e.target.value.trim().length > 0;
                const saveBtn = document.getElementById('modal-save');
                if (saveBtn) {
                    saveBtn.disabled = !hasValue;
                }
            });

            // Enter key in token input
            tokenInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.target.value.trim()) {
                    this.saveApiToken();
                }
            });
        }

        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.elements.apiTokenModal && this.elements.apiTokenModal.isOpen) {
                this.hideModal();
            }
        });

        // Toggle password visibility
        const toggleBtn = document.getElementById('toggle-token-visibility');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const input = document.getElementById('api-token-input');
                if (input) {
                    const isPassword = input.type === 'password';
                    input.type = isPassword ? 'text' : 'password';

                    // Update icon
                    const icon = toggleBtn.querySelector('i');
                    if (icon) {
                        icon.setAttribute('data-lucide', isPassword ? 'eye-off' : 'eye');
                        if (window.lucide) {
                            window.lucide.createIcons({ container: toggleBtn });
                        }
                    }
                }
            });
        }

        // Modal show event - focus input
        if (this.elements.apiTokenModal && this.elements.apiTokenModal.$el) {
            this.elements.apiTokenModal.$el.addEventListener('shown', () => {
                const input = document.getElementById('api-token-input');
                if (input) {
                    input.focus();
                    input.select();
                }
            });
        }
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
        // Ensure modal exists
        if (!this.elements.apiTokenModal) {
            console.error('API Token modal not initialized');
            return;
        }

        const modalProviderName = document.getElementById('modal-provider-name');
        const apiTokenInput = document.getElementById('api-token-input');
        const modalHelpText = document.getElementById('modal-help-text');
        const saveBtn = document.getElementById('modal-save');
        const toggleBtn = document.getElementById('toggle-token-visibility');

        if (!modalProviderName || !apiTokenInput || !modalHelpText || !saveBtn || !toggleBtn) {
            console.error('Modal elements not found');
            return;
        }

        const saveText = saveBtn.querySelector('.save-text');
        const savingText = saveBtn.querySelector('.saving-text');

        // Reset modal state
        modalProviderName.textContent = this.formatProviderName(provider);
        apiTokenInput.value = this.state.apiTokens[provider] || '';
        apiTokenInput.type = 'password';
        saveBtn.disabled = !apiTokenInput.value.trim();

        if (saveText && savingText) {
            saveText.style.display = 'inline';
            savingText.style.display = 'none';
        }

        // Reset visibility toggle icon
        const icon = toggleBtn.querySelector('i');
        if (icon) {
            icon.setAttribute('data-lucide', 'eye');
            if (window.lucide) {
                window.lucide.createIcons({ container: toggleBtn });
            }
        }

        // Set help text with better formatting
        const helpText = {
            anthropic: 'Get your API key from <a href="https://console.anthropic.com/api-keys" target="_blank" class="theme-primary hover:underline">console.anthropic.com/api-keys</a>',
            openai: 'Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" class="theme-primary hover:underline">platform.openai.com/api-keys</a>',
            openrouter: 'Get your API key from <a href="https://openrouter.ai/keys" target="_blank" class="theme-primary hover:underline">openrouter.ai/keys</a>'
        };

        modalHelpText.innerHTML = helpText[provider] || 'Enter your API key for authentication.';

        // Show modal
        this.elements.apiTokenModal.show();
    }

    /**
     * Save API token
     */
    async saveApiToken() {
        const provider = this.state.pendingProviderChange;
        const tokenInput = document.getElementById('api-token-input');
        const saveBtn = document.getElementById('modal-save');

        if (!tokenInput || !saveBtn) {
            console.error('Required elements not found');
            return;
        }

        const token = tokenInput.value.trim();
        const saveText = saveBtn.querySelector('.save-text');
        const savingText = saveBtn.querySelector('.saving-text');

        if (!token) {
            if (window.Toaster) {
                window.Toaster.error('Please enter a valid API token');
            } else {
                UIkit.notification('Please enter a valid API token', {status: 'danger', pos: 'bottom-right'});
            }
            return;
        }

        // Show loading state
        saveBtn.disabled = true;
        if (saveText && savingText) {
            saveText.style.display = 'none';
            savingText.style.display = 'flex';
        }

        try {
            // Save token to state
            this.state.apiTokens[provider] = token;

            // Patch configuration
            await this.patchProviderConfiguration(provider, token);

            // Hide modal on success
            this.elements.apiTokenModal.hide();
        } catch (error) {
            // Show error message
            if (window.Toaster) {
                window.Toaster.error('Failed to save API token. Please try again.');
            } else {
                UIkit.notification('Failed to save API token. Please try again.', {status: 'danger', pos: 'bottom-right'});
            }

            // Reset button state
            saveBtn.disabled = false;
            if (saveText && savingText) {
                saveText.style.display = 'inline';
                savingText.style.display = 'none';
            }
        }
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
