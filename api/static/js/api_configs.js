// Advanced API Configuration Manager - Based on another_example.html patterns
(function() {
    'use strict';

    // Constants
    const API_BASE = '/api/api_configs';
    const DOCUMENTS_API = '/api/documents-collection';
    const USERS_API = '/api/active-users';
    const POLICIES_API = '/api/policies';

    // State management
    const state = {
        configs: [],
        policies: [],
        currentTab: 'configs',
        searchQuery: '',
        policySearchQuery: '',
        userAutocomplete: {
            active: false,
            selectedIndex: 0,
            filteredUsers: [],
            selectedUsers: [],
            allUsers: []
        },
        datasetAutocomplete: {
            active: false,
            selectedIndex: 0,
            filteredDatasets: [],
            selectedDatasets: [],
            allDatasets: []
        },
        usageMetrics: {
            totalRequests: 0,
            totalInput: 0,
            totalOutput: 0,
            activeConfigs: 0
        },
        policyRules: []
    };

    // Initialize when DOM is ready OR when dynamically loaded
    function initializeApiConfigs() {
        console.log('Initializing API Configs Manager...');
        init();
    }

    // Try to initialize immediately if DOM is already loaded, or wait for DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeApiConfigs);
    } else {
        // DOM is already loaded, initialize immediately
        initializeApiConfigs();
    }

    // Main initialization function
    async function init() {
        console.log('Starting API Configs initialization...');

        // Wait a bit for DOM to be fully ready
        await new Promise(resolve => setTimeout(resolve, 50));

        // Reset any existing state to prevent issues with re-initialization
        if (window.configModal) {
            window.configModal = null;
        }
        if (window.statsModal) {
            window.statsModal = null;
        }

        // Check if essential DOM elements exist
        const configsList = document.getElementById('configs-list');
        const configsTab = document.getElementById('configs-tab');

        console.log('DOM check - configs-list:', configsList ? 'found' : 'NOT FOUND');
        console.log('DOM check - configs-tab:', configsTab ? 'found' : 'NOT FOUND');

        setupEventListeners();
        setupSidebarNavigation();
        setupModals();
        setupAutocomplete();
        setupSearch();

        // Load initial data
        await loadConfigurations();

        console.log('API Configs Manager initialized successfully');
    }

    // Event Listeners Setup
    function setupEventListeners() {
        console.log('Setting up event listeners...');

        // Sidebar navigation - remove existing listeners first
        document.querySelectorAll('.sidebar-nav-item').forEach(nav => {
            // Clone element to remove all event listeners
            const newNav = nav.cloneNode(true);
            nav.parentNode.replaceChild(newNav, nav);
            newNav.addEventListener('click', () => switchTab(newNav.id.replace('-tab', '')));
        });

        // Action buttons - remove existing listeners by cloning
        const buttonsToSetup = [
            { id: 'create-config-btn', handler: openCreateConfigModal },
            { id: 'refresh-configs-btn', handler: loadConfigurations },
            { id: 'retry-configs-btn', handler: loadConfigurations },
            { id: 'empty-create-btn', handler: openCreateConfigModal },
            { id: 'create-policy-btn', handler: openCreatePolicyModal },
            { id: 'refresh-policies-btn', handler: loadPolicies },
            { id: 'retry-policies-btn', handler: loadPolicies },
            { id: 'empty-create-policy-btn', handler: openCreatePolicyModal }
            // Don't add add-rule-btn here - it will be handled in modal setup
        ];

        buttonsToSetup.forEach(({ id, handler }) => {
            const btn = document.getElementById(id);
            if (btn) {
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                newBtn.addEventListener('click', handler);
            }
        });

        // Form submission
        const form = document.getElementById('config-form');
        if (form) {
            const newForm = form.cloneNode(true);
            form.parentNode.replaceChild(newForm, form);
            newForm.addEventListener('submit', handleFormSubmit);
        }

        const policyForm = document.getElementById('policy-form');
        if (policyForm) {
            const newPolicyForm = policyForm.cloneNode(true);
            policyForm.parentNode.replaceChild(newPolicyForm, policyForm);
            newPolicyForm.addEventListener('submit', handlePolicyFormSubmit);
        }

        console.log('Event listeners set up successfully');
    }

    // Sidebar Navigation
    function setupSidebarNavigation() {
        // Already handled in setupEventListeners
    }

    function switchTab(tabName) {
        state.currentTab = tabName;

        // Update sidebar nav items
        document.querySelectorAll('.sidebar-nav-item').forEach(nav => {
            nav.classList.toggle('active', nav.id === `${tabName}-tab`);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('hidden', content.id !== `${tabName}-section`);
        });

        // Load data for active tab
        switch(tabName) {
            case 'configs':
                loadConfigurations();
                break;
            case 'policies':
                loadPolicies();
                break;
            case 'usage':
                loadUsageMetrics();
                break;
            case 'users':
                loadTopUsers();
                break;
        }
    }

    // Modal Setup
    function setupModals() {
        try {
            // Wait a bit for UIkit to be available and DOM to settle
            setTimeout(() => {
                // Check if modal elements exist before initializing
                const configModalEl = document.getElementById('config-modal');
                const statsModalEl = document.getElementById('config-stats-modal');
                const policyModalEl = document.getElementById('policy-modal');
                const policyStatsModalEl = document.getElementById('policy-stats-modal');

                if (configModalEl && window.UIkit) {
                    const configModal = UIkit.modal(configModalEl);
                    window.configModal = configModal;
                }

                if (statsModalEl && window.UIkit) {
                    const statsModal = UIkit.modal(statsModalEl);
                    window.statsModal = statsModal;
                }

                if (policyModalEl && window.UIkit) {
                    const policyModal = UIkit.modal(policyModalEl);
                    window.policyModal = policyModal;

                    // Add modal close handler to clean up
                    policyModalEl.addEventListener('hidden', function() {
                        // Clear state when modal is closed
                        state.policyRules = [];
                        const form = document.getElementById('policy-form');
                        if (form) form.reset();
                    });
                }

                if (policyStatsModalEl && window.UIkit) {
                    const policyStatsModal = UIkit.modal(policyStatsModalEl);
                    window.policyStatsModal = policyStatsModal;
                }

                console.log('Modals initialized successfully');
            }, 100);
        } catch (error) {
            console.error('Error setting up modals:', error);
        }
    }

    // Search Setup
    function setupSearch() {
        const searchInput = document.getElementById('config-search');
        if (searchInput) {
            searchInput.addEventListener('input', debounce(handleSearch, 300));
        }

        const policySearchInput = document.getElementById('policy-search');
        if (policySearchInput) {
            policySearchInput.addEventListener('input', debounce(handlePolicySearch, 300));
        }
    }

    function handleSearch(e) {
        state.searchQuery = e.target.value.toLowerCase();
        filterAndRenderConfigs();
    }

    function handlePolicySearch(e) {
        state.policySearchQuery = e.target.value.toLowerCase();
        filterAndRenderPolicies();
    }

    // Autocomplete Setup
    function setupAutocomplete() {
        setupUserAutocomplete();
        setupDatasetAutocomplete();
    }

    function setupUserAutocomplete() {
        const input = document.getElementById('users-autocomplete-input');
        if (!input) return;

        input.addEventListener('input', debounce(handleUserInput, 300));
        input.addEventListener('focus', () => {
            if (state.userAutocomplete.allUsers.length === 0) {
                fetchUsers();
            }
        });
        input.addEventListener('keydown', handleUserKeyNavigation);

        // Close popup when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.parentElement.contains(e.target)) {
                hideUserAutocomplete();
            }
        });
    }

    function setupDatasetAutocomplete() {
        const input = document.getElementById('datasets-autocomplete-input');
        if (!input) return;

        input.addEventListener('input', debounce(handleDatasetInput, 300));
        input.addEventListener('focus', () => {
            if (state.datasetAutocomplete.allDatasets.length === 0) {
                fetchDatasets();
            }
        });
        input.addEventListener('keydown', handleDatasetKeyNavigation);

        // Close popup when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.parentElement.contains(e.target)) {
                hideDatasetAutocomplete();
            }
        });
    }

    // User Autocomplete Functions
    async function fetchUsers() {
        try {
            const response = await fetch(USERS_API, {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                const users = [];

                // Process online users
                if (data.online && Array.isArray(data.online)) {
                    data.online.forEach(username => {
                        users.push({
                            id: username,
                            name: username,
                            avatar: username.substring(0, 2).toUpperCase(),
                            online: true
                        });
                    });
                }

                // Process offline users
                if (data.offline && Array.isArray(data.offline)) {
                    data.offline.forEach(username => {
                        users.push({
                            id: username,
                            name: username,
                            avatar: username.substring(0, 2).toUpperCase(),
                            online: false
                        });
                    });
                }

                state.userAutocomplete.allUsers = users;
                return users;
            }
        } catch (error) {
            console.error('Error fetching users:', error);
        }
        return [];
    }

    function handleUserInput(e) {
        const filter = e.target.value.toLowerCase();

        state.userAutocomplete.filteredUsers = state.userAutocomplete.allUsers.filter(user => {
            // Don't show already selected users
            if (state.userAutocomplete.selectedUsers.some(selected => selected.id === user.id)) {
                return false;
            }
            return user.name.toLowerCase().includes(filter);
        });

        if (state.userAutocomplete.filteredUsers.length > 0) {
            showUserAutocomplete();
        } else {
            hideUserAutocomplete();
        }

        state.userAutocomplete.selectedIndex = 0;
        renderUserAutocomplete();
    }

    function showUserAutocomplete() {
        const popup = document.getElementById('users-autocomplete-popup');
        if (popup) {
            popup.classList.remove('hidden');
            state.userAutocomplete.active = true;
        }
    }

    function hideUserAutocomplete() {
        const popup = document.getElementById('users-autocomplete-popup');
        if (popup) {
            popup.classList.add('hidden');
            state.userAutocomplete.active = false;
        }
    }

    function renderUserAutocomplete() {
        const popup = document.getElementById('users-autocomplete-popup');
        if (!popup) return;

        popup.innerHTML = state.userAutocomplete.filteredUsers.map((user, index) => {
            const selected = index === state.userAutocomplete.selectedIndex ? 'selected' : '';
            const statusColor = user.online ? 'bg-green-500' : 'bg-gray-400';
            const statusText = user.online ? 'Online' : 'Offline';

            return `
                <div class="autocomplete-item ${selected}" data-index="${index}">
                    <div class="flex items-center space-x-3">
                        <div class="relative">
                            <div class="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
                                ${escapeHtml(user.avatar)}
                            </div>
                            <div class="absolute -bottom-1 -right-1 w-3 h-3 ${statusColor} rounded-full border-2 border-white"></div>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium theme-text-primary">${escapeHtml(user.name)}</div>
                            <div class="text-sm theme-text-secondary">${statusText}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Attach click listeners
        popup.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                selectUser(state.userAutocomplete.filteredUsers[index]);
            });
        });
    }

    function handleUserKeyNavigation(e) {
        if (!state.userAutocomplete.active) return;

        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                state.userAutocomplete.selectedIndex = Math.min(
                    state.userAutocomplete.selectedIndex + 1,
                    state.userAutocomplete.filteredUsers.length - 1
                );
                renderUserAutocomplete();
                break;
            case 'ArrowUp':
                e.preventDefault();
                state.userAutocomplete.selectedIndex = Math.max(
                    state.userAutocomplete.selectedIndex - 1,
                    0
                );
                renderUserAutocomplete();
                break;
            case 'Enter':
                e.preventDefault();
                if (state.userAutocomplete.filteredUsers.length > 0) {
                    selectUser(state.userAutocomplete.filteredUsers[state.userAutocomplete.selectedIndex]);
                }
                break;
            case 'Tab':
                if (state.userAutocomplete.filteredUsers.length > 0) {
                    e.preventDefault();
                    selectUser(state.userAutocomplete.filteredUsers[state.userAutocomplete.selectedIndex]);
                }
                break;
            case 'Escape':
                hideUserAutocomplete();
                break;
        }
    }

    function selectUser(user) {
        // Check if already selected
        if (!state.userAutocomplete.selectedUsers.some(u => u.id === user.id)) {
            state.userAutocomplete.selectedUsers.push(user);
            renderSelectedUsers();
            updateHiddenUsersInput();
        }

        // Clear input
        const input = document.getElementById('users-autocomplete-input');
        if (input) input.value = '';

        hideUserAutocomplete();
    }

    function removeUser(userId) {
        state.userAutocomplete.selectedUsers = state.userAutocomplete.selectedUsers.filter(
            user => user.id !== userId
        );
        renderSelectedUsers();
        updateHiddenUsersInput();
    }

    function renderSelectedUsers() {
        const container = document.getElementById('selected-users-container');
        const listDiv = document.getElementById('selected-users-list');
        const summarySpan = document.querySelector('.users-summary');

        if (!container || !listDiv || !summarySpan) return;

        if (state.userAutocomplete.selectedUsers.length === 0) {
            container.classList.add('hidden');
            listDiv.innerHTML = '';
            return;
        }

        // Show container
        container.classList.remove('hidden');

        // Update summary
        summarySpan.textContent = `${state.userAutocomplete.selectedUsers.length} user${state.userAutocomplete.selectedUsers.length > 1 ? 's' : ''} selected`;

        // Update users list with new design
        listDiv.innerHTML = state.userAutocomplete.selectedUsers.map((user, index) => {
            const statusColor = user.online ? 'bg-green-500' : 'bg-gray-400';

            return `
                <div class="flex items-center space-x-3 p-3 theme-bg-surface theme-border border rounded-lg group hover:theme-bg-background transition-colors duration-200">
                    <div class="flex-shrink-0 relative">
                        <div class="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
                            ${escapeHtml(user.avatar)}
                        </div>
                        <div class="absolute -bottom-1 -right-1 w-3 h-3 ${statusColor} rounded-full border-2 border-white"></div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="font-medium theme-text-primary truncate">${escapeHtml(user.name)}</p>
                        <p class="text-sm theme-text-secondary">${user.online ? 'Online' : 'Offline'}</p>
                    </div>
                    <button type="button" onclick="removeUser('${user.id}')" class="flex-shrink-0 p-1.5 rounded-lg theme-text-muted hover:theme-danger transition-colors duration-200 opacity-0 group-hover:opacity-100">
                        <i data-lucide="x" class="h-4 w-4"></i>
                    </button>
                </div>
            `;
        }).join('');

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons({ container: listDiv });
    }

    function updateHiddenUsersInput() {
        const hiddenInput = document.getElementById('config-users');
        if (hiddenInput) {
            hiddenInput.value = state.userAutocomplete.selectedUsers.map(user => user.id).join(',');
        }
    }

    // Dataset Autocomplete Functions
    async function fetchDatasets() {
        try {
            const response = await fetch(`${DOCUMENTS_API}/list`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    limit: 100,
                    include_embeddings: false
                })
            });

            if (response.ok) {
                const data = await response.json();
                const datasets = data.documents ? data.documents.map(doc => {
                    const fileName = doc.metadata?.file_name || doc.id || 'Unknown';
                    return {
                        id: doc.id,
                        name: fileName,
                        size: doc.content ? doc.content.length : 0,
                        type: getFileExtension(fileName),
                        createdAt: doc.metadata?.created_at || new Date().toISOString()
                    };
                }) : [];

                state.datasetAutocomplete.allDatasets = datasets;
                return datasets;
            }
        } catch (error) {
            console.error('Error fetching datasets:', error);
        }
        return [];
    }

    function handleDatasetInput(e) {
        const filter = e.target.value.toLowerCase();

        state.datasetAutocomplete.filteredDatasets = state.datasetAutocomplete.allDatasets.filter(dataset => {
            // Don't show already selected datasets
            if (state.datasetAutocomplete.selectedDatasets.some(selected => selected.id === dataset.id)) {
                return false;
            }
            return dataset.name.toLowerCase().includes(filter);
        });

        if (state.datasetAutocomplete.filteredDatasets.length > 0) {
            showDatasetAutocomplete();
        } else {
            hideDatasetAutocomplete();
        }

        state.datasetAutocomplete.selectedIndex = 0;
        renderDatasetAutocomplete();
    }

    function showDatasetAutocomplete() {
        const popup = document.getElementById('datasets-autocomplete-popup');
        if (popup) {
            popup.classList.remove('hidden');
            state.datasetAutocomplete.active = true;
        }
    }

    function hideDatasetAutocomplete() {
        const popup = document.getElementById('datasets-autocomplete-popup');
        if (popup) {
            popup.classList.add('hidden');
            state.datasetAutocomplete.active = false;
        }
    }

    function renderDatasetAutocomplete() {
        const popup = document.getElementById('datasets-autocomplete-popup');
        if (!popup) return;

        popup.innerHTML = state.datasetAutocomplete.filteredDatasets.map((dataset, index) => {
            const selected = index === state.datasetAutocomplete.selectedIndex ? 'selected' : '';
            const typeIcon = getFileTypeIcon(dataset.type);
            const formattedSize = formatBytes(dataset.size);

            return `
                <div class="autocomplete-item ${selected}" data-index="${index}">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 rounded theme-bg-background flex items-center justify-center">
                            <i data-lucide="${typeIcon}" class="h-4 w-4 theme-text-secondary"></i>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium theme-text-primary">${escapeHtml(dataset.name)}</div>
                            <div class="text-sm theme-text-secondary">${formattedSize} • ${dataset.type.toUpperCase()}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Attach click listeners
        popup.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                selectDataset(state.datasetAutocomplete.filteredDatasets[index]);
            });
        });

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons({ container: popup });
    }

    function handleDatasetKeyNavigation(e) {
        if (!state.datasetAutocomplete.active) return;

        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                state.datasetAutocomplete.selectedIndex = Math.min(
                    state.datasetAutocomplete.selectedIndex + 1,
                    state.datasetAutocomplete.filteredDatasets.length - 1
                );
                renderDatasetAutocomplete();
                break;
            case 'ArrowUp':
                e.preventDefault();
                state.datasetAutocomplete.selectedIndex = Math.max(
                    state.datasetAutocomplete.selectedIndex - 1,
                    0
                );
                renderDatasetAutocomplete();
                break;
            case 'Enter':
                e.preventDefault();
                if (state.datasetAutocomplete.filteredDatasets.length > 0) {
                    selectDataset(state.datasetAutocomplete.filteredDatasets[state.datasetAutocomplete.selectedIndex]);
                }
                break;
            case 'Tab':
                if (state.datasetAutocomplete.filteredDatasets.length > 0) {
                    e.preventDefault();
                    selectDataset(state.datasetAutocomplete.filteredDatasets[state.datasetAutocomplete.selectedIndex]);
                }
                break;
            case 'Escape':
                hideDatasetAutocomplete();
                break;
        }
    }

    function selectDataset(dataset) {
        // Check if already selected
        if (!state.datasetAutocomplete.selectedDatasets.some(d => d.id === dataset.id)) {
            state.datasetAutocomplete.selectedDatasets.push(dataset);
            renderSelectedDatasets();
            updateHiddenDatasetsInput();
        }

        // Clear input
        const input = document.getElementById('datasets-autocomplete-input');
        if (input) input.value = '';

        hideDatasetAutocomplete();
    }

    function removeDataset(datasetId) {
        state.datasetAutocomplete.selectedDatasets = state.datasetAutocomplete.selectedDatasets.filter(
            dataset => dataset.id !== datasetId
        );
        renderSelectedDatasets();
        updateHiddenDatasetsInput();
    }

    function renderSelectedDatasets() {
        const container = document.getElementById('selected-datasets-container');
        const listDiv = document.getElementById('selected-datasets-list');
        const summarySpan = document.querySelector('.datasets-summary');

        if (!container || !listDiv || !summarySpan) return;

        if (state.datasetAutocomplete.selectedDatasets.length === 0) {
            container.classList.add('hidden');
            listDiv.innerHTML = '';
            return;
        }

        // Show container
        container.classList.remove('hidden');

        // Update summary
        const totalSize = state.datasetAutocomplete.selectedDatasets.reduce((sum, dataset) => sum + dataset.size, 0);
        summarySpan.textContent = `${state.datasetAutocomplete.selectedDatasets.length} dataset${state.datasetAutocomplete.selectedDatasets.length > 1 ? 's' : ''} selected (${formatBytes(totalSize)})`;

        // Update datasets list with new design
        listDiv.innerHTML = state.datasetAutocomplete.selectedDatasets.map((dataset, index) => {
            const typeIcon = getFileTypeIcon(dataset.type);
            const formattedSize = formatBytes(dataset.size);

            return `
                <div class="flex items-center space-x-3 p-3 theme-bg-surface theme-border border rounded-lg group hover:theme-bg-background transition-colors duration-200">
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 rounded theme-bg-background flex items-center justify-center">
                            <i data-lucide="${typeIcon}" class="h-4 w-4 theme-text-muted"></i>
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="font-medium theme-text-primary truncate">${escapeHtml(dataset.name)}</p>
                        <p class="text-sm theme-text-secondary">${dataset.type.toUpperCase()} • ${formattedSize}</p>
                    </div>
                    <button type="button" onclick="removeDataset('${dataset.id}')" class="flex-shrink-0 p-1.5 rounded-lg theme-text-muted hover:theme-danger transition-colors duration-200 opacity-0 group-hover:opacity-100">
                        <i data-lucide="x" class="h-4 w-4"></i>
                    </button>
                </div>
            `;
        }).join('');

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons({ container: listDiv });
    }

    function updateHiddenDatasetsInput() {
        const hiddenInput = document.getElementById('config-datasets');
        if (hiddenInput) {
            hiddenInput.value = state.datasetAutocomplete.selectedDatasets.map(dataset => dataset.id).join(',');
        }
    }

    // Configuration Management
    async function loadConfigurations() {
        console.log('Loading configurations...');
        showLoading('configs');

        try {
            // Load both configs and policies in parallel
            const [configsResponse, policiesResponse] = await Promise.all([
                fetch(API_BASE),
                fetch(POLICIES_API)
            ]);

            if (!configsResponse.ok) {
                throw new Error(`HTTP ${configsResponse.status}: ${configsResponse.statusText}`);
            }

            const configs = await configsResponse.json();
            console.log('Loaded configs:', configs);
            state.configs = configs;

            // Load policies for dropdown
            if (policiesResponse.ok) {
                const policiesData = await policiesResponse.json();
                if (Array.isArray(policiesData)) {
                    state.policies = policiesData;
                } else if (policiesData.policies) {
                    state.policies = policiesData.policies;
                }
            }

            filterAndRenderConfigs();
        } catch (error) {
            console.error('Error loading configurations:', error);
            showError('configs', `Failed to load configurations: ${error.message}`);
        }
    }

    function filterAndRenderConfigs() {
        let filteredConfigs = state.configs;

        if (state.searchQuery) {
            filteredConfigs = state.configs.filter(config =>
                config.config_id.toLowerCase().includes(state.searchQuery) ||
                config.users.some(user => user.toLowerCase().includes(state.searchQuery)) ||
                config.datasets.some(dataset => dataset.toLowerCase().includes(state.searchQuery))
            );
        }

        displayConfigurations(filteredConfigs);
    }

    function displayConfigurations(configs) {
        console.log('Displaying configurations:', configs);
        const container = document.getElementById('configs-list');
        const loading = document.getElementById('configs-loading');
        const empty = document.getElementById('configs-empty');
        const error = document.getElementById('configs-error');

        console.log('Container element:', container);
        console.log('Loading element:', loading);
        console.log('Empty element:', empty);
        console.log('Error element:', error);

        // Hide all states and show the main list
        hideLoading('configs');

        if (configs.length === 0) {
            console.log('No configs to display, showing empty state');
            if (empty) empty.classList.remove('hidden');
            if (container) container.innerHTML = '';
            return;
        }

        console.log('Rendering', configs.length, 'configurations');

        if (!container) {
            console.error('configs-list container not found!');
            return;
        }

        // Make sure the container is visible
        container.classList.remove('hidden');
        console.log('Container classes after removing hidden:', container.className);

        container.innerHTML = configs.map(config => {
            const configId = config.config_id;
            const createdAt = formatTimestamp(config.created_at);
            const updatedAt = formatTimestamp(config.updated_at);

            return `
                <div class="api-config-card theme-bg-surface rounded-xl shadow-sm theme-border border transition-all duration-200 hover:shadow-md">
                    <div class="p-6">
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex-1">
                                <h3 class="text-lg font-semibold theme-text-primary mb-1">API Configuration</h3>
                                <p class="text-sm font-mono theme-text-secondary">${escapeHtml(configId.slice(0, 12))}...</p>
                                <p class="text-xs theme-text-muted mt-1">Created: ${createdAt}</p>
                            </div>
                            <div class="api-config-actions flex items-center" style="gap: 0.25rem;">
                                <button onclick="viewConfigStats('${configId}')" class="api-action-btn" title="View Statistics">
                                    <i data-lucide="bar-chart-2" class="h-4 w-4"></i>
                                </button>
                                <button onclick="editConfig('${configId}')" class="api-action-btn" title="Edit">
                                    <i data-lucide="edit-3" class="h-4 w-4"></i>
                                </button>
                                <button onclick="deleteConfig('${configId}')" class="api-action-btn api-action-btn-danger" title="Delete">
                                    <i data-lucide="trash-2" class="h-4 w-4"></i>
                                </button>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                            <!-- Users Section -->
                            <div class="space-y-2">
                                <div class="flex items-center gap-2 text-sm font-medium theme-text-secondary">
                                    <i data-lucide="users" class="h-4 w-4 theme-primary"></i>
                                    <span>Users (${config.users.length})</span>
                                </div>
                                <div class="border theme-border rounded-lg p-2 overflow-y-auto" style="height: 108px;">
                                    ${config.users.length > 0
                                        ? '<div class="space-y-1">' + config.users.map(user => `
                                            <div class="flex items-center gap-2 p-1.5 hover:theme-bg-surface rounded transition-colors">
                                                <div class="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                                                    ${escapeHtml(user.substring(0, 2).toUpperCase())}
                                                </div>
                                                <span class="text-xs theme-text-primary truncate">${escapeHtml(user)}</span>
                                            </div>
                                        `).join('') + '</div>'
                                        : '<div class="text-xs theme-text-muted opacity-60 text-center py-2">No users configured</div>'
                                    }
                                </div>
                            </div>

                            <!-- Datasets Section -->
                            <div class="space-y-2">
                                <div class="flex items-center gap-2 text-sm font-medium theme-text-secondary">
                                    <i data-lucide="database" class="h-4 w-4 theme-primary"></i>
                                    <span>Datasets (${config.datasets.length})</span>
                                </div>
                                <div class="border theme-border rounded-lg p-2 overflow-y-auto" style="height: 108px;">
                                    ${config.datasets.length > 0
                                        ? '<div class="space-y-1">' + config.datasets.map(dataset => `
                                            <div class="flex items-center gap-2 p-1.5 hover:theme-bg-surface rounded transition-colors">
                                                <i data-lucide="file-text" class="h-4 w-4 theme-text-muted flex-shrink-0"></i>
                                                <span class="text-xs theme-text-primary truncate" title="${escapeHtml(dataset)}">${escapeHtml(dataset.length > 40 ? dataset.slice(0, 40) + '...' : dataset)}</span>
                                            </div>
                                        `).join('') + '</div>'
                                        : '<div class="text-xs theme-text-muted opacity-60 text-center py-2">No datasets configured</div>'
                                    }
                                </div>
                            </div>
                        </div>

                        <!-- Policy Selection -->
                        <div class="mt-4 p-3 theme-bg-background rounded-lg">
                            <div class="flex items-center justify-between">
                                <label class="text-sm font-medium theme-text-secondary flex items-center gap-2">
                                    <i data-lucide="shield" class="h-4 w-4 theme-text-muted"></i>
                                    Policy
                                </label>
                                <select
                                    class="uk-select text-sm border theme-border theme-bg-surface rounded px-3 py-1.5"
                                    style="width: auto; min-width: 200px;"
                                    onchange="attachPolicyToConfig('${configId}', this.value)">
                                    <option value="">No Policy</option>
                                    ${state.policies.map(policy => {
                                        const policyId = policy.policy_id;
                                        const isAttached = config.policy_id === policyId;
                                        return `<option value="${policyId}" ${isAttached ? 'selected' : ''}>${escapeHtml(policy.name)}</option>`;
                                    }).join('')}
                                </select>
                            </div>
                        </div>

                        <div class="flex justify-between items-center pt-4 border-t theme-border mt-4">
                            <div class="flex items-center gap-2 text-xs theme-text-muted">
                                <i data-lucide="clock" class="h-3 w-3"></i>
                                <span>Updated ${updatedAt}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                                <span class="text-xs theme-text-secondary">Active</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons({ container });
    }

    // Modal Functions
    async function openCreateConfigModal() {
        resetForm();

        // Set modal title and button text
        const title = document.getElementById('modal-title');
        const btnText = document.getElementById('config-btn-text');
        if (title) title.textContent = 'Create API Configuration';
        if (btnText) btnText.textContent = 'Create Configuration';

        // Fetch users and datasets
        await Promise.all([
            fetchUsers(),
            fetchDatasets()
        ]);

        // Show modal
        if (window.configModal) {
            window.configModal.show();
        }
    }

    async function editConfig(configId) {
        try {
            const response = await fetch(`${API_BASE}/${configId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch configuration');
            }

            const config = await response.json();

            // Set form values
            document.getElementById('config-id').value = config.config_id;

            // Set modal title and button text
            const title = document.getElementById('modal-title');
            const btnText = document.getElementById('config-btn-text');
            if (title) title.textContent = 'Edit API Configuration';
            if (btnText) btnText.textContent = 'Update Configuration';

            // Fetch users and datasets first
            await Promise.all([
                fetchUsers(),
                fetchDatasets()
            ]);

            // Map user IDs to user objects
            state.userAutocomplete.selectedUsers = [];
            config.users.forEach(userId => {
                const user = state.userAutocomplete.allUsers.find(u => u.id === userId);
                if (user) {
                    state.userAutocomplete.selectedUsers.push(user);
                } else {
                    // Create temporary user object if not found
                    state.userAutocomplete.selectedUsers.push({
                        id: userId,
                        name: userId,
                        avatar: userId.substring(0, 2).toUpperCase(),
                        online: false
                    });
                }
            });

            // Map dataset IDs to dataset objects
            state.datasetAutocomplete.selectedDatasets = [];
            config.datasets.forEach(datasetId => {
                const dataset = state.datasetAutocomplete.allDatasets.find(d => d.id === datasetId);
                if (dataset) {
                    state.datasetAutocomplete.selectedDatasets.push(dataset);
                } else {
                    // Create temporary dataset object if not found
                    state.datasetAutocomplete.selectedDatasets.push({
                        id: datasetId,
                        name: datasetId,
                        type: 'unknown',
                        size: 0,
                        createdAt: new Date().toISOString()
                    });
                }
            });

            // Render selected items
            renderSelectedUsers();
            renderSelectedDatasets();
            updateHiddenUsersInput();
            updateHiddenDatasetsInput();

            // Show modal
            if (window.configModal) {
                window.configModal.show();
            }
        } catch (error) {
            console.error('Error loading configuration:', error);
            showNotification('Failed to load configuration for editing', 'error');
        }
    }

    async function deleteConfig(configId) {
        if (!confirm('Are you sure you want to delete this API configuration? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/${configId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete configuration');
            }

            await loadConfigurations();
            showNotification('Configuration deleted successfully', 'success');
        } catch (error) {
            console.error('Error deleting configuration:', error);
            showNotification('Failed to delete configuration', 'error');
        }
    }

    async function viewConfigStats(configId) {
        // Set modal title
        const title = document.getElementById('stats-modal-title');
        if (title) {
            title.textContent = `API Usage Statistics (${configId.slice(0, 8)})`;
        }

        // Show loading state
        const content = document.getElementById('stats-content');
        if (content) {
            content.innerHTML = `
                <div class="stats-loading text-center py-8">
                    <div class="uk-spinner uk-spinner-medium theme-text-muted mx-auto mb-4"></div>
                    <p class="theme-text-secondary">Loading statistics...</p>
                </div>
            `;
        }

        // Show modal
        if (window.statsModal) {
            window.statsModal.show();
        }

        try {
            // Fetch usage statistics
            const [usageResponse, topUsersResponse] = await Promise.all([
                fetch(`${API_BASE}/${configId}/usage`),
                fetch(`${API_BASE}/${configId}/top-users?limit=5`)
            ]);

            const stats = usageResponse.ok ? await usageResponse.json() : {
                total_requests: 0,
                total_input_word_count: 0,
                total_output_word_count: 0,
                last_updated: null
            };

            const topUsersData = topUsersResponse.ok ? await topUsersResponse.json() : { top_users: [] };
            const topUsers = topUsersData.top_users || [];

            // Format and display statistics
            const lastUpdated = stats.last_updated
                ? new Date(stats.last_updated).toLocaleString()
                : 'Never';

            content.innerHTML = `
                <div class="stats-grid mb-6">
                    <div class="stats-card">
                        <div class="stats-card-header">
                            <i data-lucide="activity" class="stats-card-icon"></i>
                            <h4 class="font-medium theme-text-primary">Total Requests</h4>
                        </div>
                        <div class="stats-card-value">${(stats.total_requests || 0).toLocaleString()}</div>
                    </div>

                    <div class="stats-card">
                        <div class="stats-card-header">
                            <i data-lucide="message-square" class="stats-card-icon"></i>
                            <h4 class="font-medium theme-text-primary">Input Words</h4>
                        </div>
                        <div class="stats-card-value">${(stats.total_input_word_count || 0).toLocaleString()}</div>
                    </div>

                    <div class="stats-card">
                        <div class="stats-card-header">
                            <i data-lucide="message-circle" class="stats-card-icon"></i>
                            <h4 class="font-medium theme-text-primary">Output Words</h4>
                        </div>
                        <div class="stats-card-value">${(stats.total_output_word_count || 0).toLocaleString()}</div>
                    </div>
                </div>

                <div class="space-y-4">
                    <h4 class="text-lg font-semibold theme-text-primary flex items-center gap-2">
                        <i data-lucide="users" class="h-5 w-5 theme-primary"></i>
                        <span>Top Users</span>
                    </h4>
                    ${topUsers.length > 0 ? `
                        <div class="stats-user-chart">
                            ${topUsers.map(user => {
                                const maxCount = topUsers[0]?.count || 1;
                                const percentage = Math.max(10, (user.count / maxCount) * 100);
                                return `
                                    <div class="stats-user-bar">
                                        <div class="w-24 text-sm font-medium theme-text-primary truncate">
                                            ${escapeHtml(user.user_id)}
                                        </div>
                                        <div class="stats-user-bar-container">
                                            <div class="stats-user-bar-fill" style="width: ${percentage}%"></div>
                                            <span class="stats-user-bar-value">${user.count}</span>
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : `
                        <p class="text-center theme-text-muted py-8">No usage data available</p>
                    `}
                </div>

                <div class="mt-6 pt-4 border-t theme-border text-center">
                    <small class="theme-text-muted">Last updated: ${lastUpdated}</small>
                </div>
            `;

            // Initialize Lucide icons
            if (window.lucide) lucide.createIcons({ container: content });

        } catch (error) {
            console.error('Error loading configuration statistics:', error);
            content.innerHTML = `
                <div class="text-center py-8">
                    <i data-lucide="alert-circle" class="h-12 w-12 theme-text-danger mx-auto mb-4"></i>
                    <p class="theme-text-primary font-medium mb-2">Failed to load statistics</p>
                    <p class="theme-text-secondary text-sm">${error.message}</p>
                </div>
            `;

            if (window.lucide) lucide.createIcons({ container: content });
        }
    }

    // Form Handling
    async function handleFormSubmit(e) {
        e.preventDefault();

        const configId = document.getElementById('config-id').value;
        const users = state.userAutocomplete.selectedUsers.map(u => u.id);
        const datasets = state.datasetAutocomplete.selectedDatasets.map(d => d.id);

        if (users.length === 0) {
            showNotification('Please select at least one user', 'error');
            return;
        }

        if (datasets.length === 0) {
            showNotification('Please select at least one dataset', 'error');
            return;
        }

        // Show loading state
        const submitBtn = document.getElementById('config-submit-btn');
        const spinner = document.getElementById('config-spinner');
        const btnText = document.getElementById('config-btn-text');

        if (submitBtn) submitBtn.disabled = true;
        if (spinner) spinner.classList.remove('hidden');
        if (btnText) btnText.textContent = configId ? 'Updating...' : 'Creating...';

        try {
            const method = configId ? 'PUT' : 'POST';
            const url = configId ? `${API_BASE}/${configId}` : API_BASE;

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ users, datasets })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save configuration');
            }

            // Close modal and reload configurations
            if (window.configModal) {
                window.configModal.hide();
            }

            await loadConfigurations();
            showNotification(
                configId ? 'Configuration updated successfully' : 'Configuration created successfully',
                'success'
            );
        } catch (error) {
            console.error('Error saving configuration:', error);
            showNotification(`Failed to save configuration: ${error.message}`, 'error');
        } finally {
            // Reset button state
            if (submitBtn) submitBtn.disabled = false;
            if (spinner) spinner.classList.add('hidden');
            if (btnText) btnText.textContent = configId ? 'Update Configuration' : 'Create Configuration';
        }
    }

    function resetForm() {
        document.getElementById('config-id').value = '';
        document.getElementById('users-autocomplete-input').value = '';
        document.getElementById('datasets-autocomplete-input').value = '';

        // Reset autocomplete state
        state.userAutocomplete.selectedUsers = [];
        state.userAutocomplete.filteredUsers = [];
        state.userAutocomplete.selectedIndex = 0;

        state.datasetAutocomplete.selectedDatasets = [];
        state.datasetAutocomplete.filteredDatasets = [];
        state.datasetAutocomplete.selectedIndex = 0;

        // Hide autocomplete popups
        hideUserAutocomplete();
        hideDatasetAutocomplete();

        // Clear selected items using the new rendering functions
        renderSelectedUsers();
        renderSelectedDatasets();

        // Clear hidden inputs
        updateHiddenUsersInput();
        updateHiddenDatasetsInput();
    }

    // Policy Management
    async function loadPolicies() {
        console.log('Loading policies...');
        showLoading('policies');

        try {
            const response = await fetch(POLICIES_API);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Loaded policies:', data);

            // Handle both array response and object with policies property
            if (Array.isArray(data)) {
                state.policies = data;
            } else if (data.policies && Array.isArray(data.policies)) {
                state.policies = data.policies;
            } else {
                // If it's a single policy object, wrap it in an array
                state.policies = [data];
            }

            filterAndRenderPolicies();
        } catch (error) {
            console.error('Error loading policies:', error);
            showError('policies', error.message);
        }
    }

    function filterAndRenderPolicies() {
        const filteredPolicies = state.policies.filter(policy => {
            if (!state.policySearchQuery) return true;
            return policy.name.toLowerCase().includes(state.policySearchQuery) ||
                   (policy.description && policy.description.toLowerCase().includes(state.policySearchQuery));
        });

        renderPolicies(filteredPolicies);
    }

    function renderPolicies(policies) {
        const container = document.getElementById('policies-list');
        if (!container) return;

        hideLoading('policies');

        if (policies.length === 0) {
            showEmpty('policies');
            return;
        }

        container.innerHTML = policies.map(policy => {
            // Handle both 'id' and 'policy_id' field names
            const policyId = policy.policy_id;
            const attachedAPIs = policy.api_configs || [];
            const rulesCount = policy.rules ? policy.rules.length : 0;
            const isActive = policy.is_active !== false;  // Default to active if not specified
            const enforcementMode = policy.settings?.enforcement_mode || 'block';

            return `
                <div class="policy-card theme-bg-surface rounded-xl shadow-sm theme-border border hover:shadow-md transition-all duration-200">
                    <div class="p-6">
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex-1">
                                <h3 class="text-lg font-semibold theme-text-primary flex items-center gap-2">
                                    ${escapeHtml(policy.name)}
                                    <span class="policy-status-badge ${isActive ? 'active' : 'inactive'}">
                                        ${isActive ? 'Active' : 'Inactive'}
                                    </span>
                                </h3>
                                ${policy.description ? `
                                    <p class="theme-text-secondary text-sm mt-1">${escapeHtml(policy.description)}</p>
                                ` : ''}
                            </div>
                            <div class="policy-actions flex space-x-2">
                                <button onclick="viewPolicyStats('${policyId}')" class="api-action-btn" title="View Statistics">
                                    <i data-lucide="bar-chart" class="h-4 w-4"></i>
                                </button>
                                <button onclick="editPolicy('${policyId}')" class="api-action-btn" title="Edit Policy">
                                    <i data-lucide="edit" class="h-4 w-4"></i>
                                </button>
                                <button onclick="deletePolicy('${policyId}')" class="api-action-btn api-action-btn-danger" title="Delete Policy">
                                    <i data-lucide="trash-2" class="h-4 w-4"></i>
                                </button>
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-6">
                            <div>
                                <h4 class="text-sm font-medium theme-text-secondary mb-2">Policy Type</h4>
                                <p class="theme-text-primary flex items-center gap-2">
                                    <i data-lucide="${enforcementMode === 'block' ? 'shield' : 'eye'}" class="h-4 w-4 theme-text-muted"></i>
                                    <span class="capitalize">${policy.type || 'combined'}</span>
                                </p>
                            </div>
                            <div>
                                <h4 class="text-sm font-medium theme-text-secondary mb-2">Rules</h4>
                                <p class="theme-text-primary">${rulesCount} rule${rulesCount !== 1 ? 's' : ''}</p>
                            </div>
                        </div>

                        ${attachedAPIs.length > 0 ? `
                            <div class="mt-4">
                                <h4 class="text-sm font-medium theme-text-secondary mb-2">Attached to APIs</h4>
                                <div class="flex flex-wrap gap-2">
                                    ${attachedAPIs.map(apiId => `
                                        <span class="px-2 py-1 text-xs rounded-full theme-bg-background theme-text-primary">
                                            ${escapeHtml(apiId)}
                                        </span>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}

                        <div class="flex justify-between items-center mt-4 pt-4 theme-border border-t">
                            <span class="text-sm theme-text-secondary">
                                Created ${new Date(policy.created_at).toLocaleDateString()}
                            </span>
                            ${policy.updated_at ? `
                                <span class="text-sm theme-text-secondary">
                                    Updated ${new Date(policy.updated_at).toLocaleDateString()}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons();
    }

    function openCreatePolicyModal() {
        console.log('Opening create policy modal');

        // Reset form
        const form = document.getElementById('policy-form');
        if (form) form.reset();

        // Clear policy ID
        const policyIdField = document.getElementById('policy-id');
        if (policyIdField) policyIdField.value = '';

        // Clear rules
        state.policyRules = [];
        renderPolicyRules();

        // Set modal title and button text
        const title = document.getElementById('policy-modal-title');
        const btnText = document.getElementById('policy-btn-text');
        if (title) title.textContent = 'Create Policy';
        if (btnText) btnText.textContent = 'Create Policy';

        // Show modal
        if (window.policyModal) {
            window.policyModal.show();

            // Setup the add rule button after modal is shown
            setTimeout(() => {
                setupPolicyModalHandlers();
            }, 100);
        } else {
            console.error('Policy modal not initialized');
            showNotification('Policy modal not initialized. Please refresh the page.', 'error');
        }
    }

    function setupPolicyModalHandlers() {
        console.log('Setting up policy modal handlers');
        // Setup add rule button
        const addRuleBtn = document.getElementById('add-rule-btn');
        if (addRuleBtn) {
            // Remove old handler
            const newBtn = addRuleBtn.cloneNode(true);
            addRuleBtn.parentNode.replaceChild(newBtn, addRuleBtn);
            // Add new handler
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Add rule button clicked');
                if (typeof addPolicyRule === 'function') {
                    addPolicyRule();
                } else {
                    console.error('addPolicyRule function not found');
                    showNotification('Error: Unable to add rule. Please refresh the page.', 'error');
                }
            });
        } else {
            console.warn('Add rule button not found');
        }
    }

    async function editPolicy(policyId) {
        try {
            const response = await fetch(`${POLICIES_API}/${policyId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch policy');
            }

            const data = await response.json();
            // Extract policy from response wrapper if needed
            const policy = data.policy || data;

            console.log('Editing policy:', policy);

            // Handle both 'id' and 'policy_id' field names - use different variable name to avoid conflict
            const actualPolicyId = policy.policy_id || policyId;
            console.log('Policy ID:', actualPolicyId);

            // Set modal title and button text first
            const title = document.getElementById('policy-modal-title');
            const btnText = document.getElementById('policy-btn-text');
            if (title) title.textContent = 'Edit Policy';
            if (btnText) btnText.textContent = 'Update Policy';

            // Show modal first
            if (window.policyModal) {
                window.policyModal.show();
            }

            // Set form values after modal is shown
            setTimeout(() => {
                document.getElementById('policy-id').value = actualPolicyId || '';
                document.getElementById('policy-name').value = policy.name || '';
                document.getElementById('policy-description').value = policy.description || '';
                document.getElementById('policy-enforcement-mode').value = policy.settings?.enforcement_mode || 'block';

                // Load rules - convert from API format if needed
                if (policy.rules && Array.isArray(policy.rules)) {
                    state.policyRules = policy.rules.map(rule => ({
                        id: rule.rule_id || Date.now().toString(),
                        metric_key: rule.metric_key,
                        operator: rule.operator,
                        threshold: rule.threshold,
                        period: rule.period || 'daily',
                        action: rule.action || 'block'
                    }));
                } else {
                    state.policyRules = [];
                }
                renderPolicyRules();

                // Setup modal handlers
                setupPolicyModalHandlers();
            }, 100);
        } catch (error) {
            console.error('Error loading policy:', error);
            showNotification('Failed to load policy for editing', 'error');
        }
    }

    async function deletePolicy(policyId) {
        // Find the policy to get its name
        const policy = state.policies.find(p => (p.policy_id || p.id) === policyId);
        const policyName = policy ? policy.name : 'this policy';

        // Create a custom confirmation toaster with warning theme
        const confirmationId = Date.now().toString();
        const warningColor = window.appTheme ? window.appTheme.getCurrentColors().warning : '#ffc107';
        const dangerColor = window.appTheme ? window.appTheme.getCurrentColors().danger : '#dc3545';

        // Create confirmation toaster HTML for UIkit fallback
        const confirmationHtml = `
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
                <span style="color: var(--color-text-primary); font-size: 0.95em;">
                    Delete <strong>${escapeHtml(policyName)}</strong>?
                </span>
                <div style="display: flex; gap: 8px;">
                    <button onclick="window.cancelPolicyDeletion('${confirmationId}')"
                            style="padding: 4px 12px; border-radius: 4px; border: 1px solid var(--color-border);
                                   background: transparent; color: var(--color-text-secondary);
                                   cursor: pointer; font-size: 0.875rem; transition: all 0.2s;">
                        Cancel
                    </button>
                    <button onclick="window.confirmPolicyDeletion('${confirmationId}', '${policyId}')"
                            style="padding: 4px 12px; border-radius: 4px; border: 1px solid ${dangerColor};
                                   background: transparent; color: ${dangerColor};
                                   cursor: pointer; font-size: 0.875rem; transition: all 0.2s;"
                            onmouseover="this.style.backgroundColor='${dangerColor}'; this.style.color='white';"
                            onmouseout="this.style.backgroundColor='transparent'; this.style.color='${dangerColor}';">
                        Delete
                    </button>
                </div>
            </div>
        `;

        // Store the toaster reference for later dismissal
        window.activePolicyConfirmation = {
            id: confirmationId,
            toastId: null
        };

        // Show the confirmation toaster
        if (window.Toaster && typeof window.Toaster.warningCta === 'function') {
            // Initialize Toaster if not already done
            if (!window.Toaster._initialized) {
                window.Toaster.init();
                window.Toaster._initialized = true;
            }

            const toastId = window.Toaster.warningCta(
                `<div style="font-size: 0.95em;">
                    <span>Delete <strong>${escapeHtml(policyName)}</strong>?</span>
                </div>`,
                {
                    text: 'Delete',
                    dismissText: 'Cancel',
                    callback: async () => {
                        window.activePolicyConfirmation = null;
                        await performPolicyDeletion(policyId);
                    }
                },
                {
                    persist: true,
                    position: 'bottom-right'
                }
            );

            window.activePolicyConfirmation.toastId = toastId;

            // Apply solid warning background and style buttons
            setTimeout(() => {
                // Find the warning notification
                const notification = document.querySelector('.uk-notification-message-warning');
                if (notification) {
                    // Apply solid warning background without opacity
                    const solidWarningBg = window.appTheme && window.appTheme.currentMode === 'dark'
                        ? '#52520a'  // Dark mode: solid dark yellow
                        : '#fef08a';  // Light mode: solid pale yellow

                    notification.style.setProperty('background-color', solidWarningBg, 'important');
                    notification.style.setProperty('border', `1px solid ${warningColor}`, 'important');
                    notification.style.setProperty('box-shadow', '0 2px 8px rgba(0, 0, 0, 0.1)', 'important');
                    notification.style.setProperty('color', 'var(--color-text-primary)', 'important');

                    // Ensure parent container has no transparency
                    const parent = notification.closest('.uk-notification');
                    if (parent) {
                        parent.style.setProperty('background', 'transparent', 'important');
                    }
                }

                // Style the buttons to match the warning theme
                const actionBtn = document.querySelector('.toaster-action');
                const dismissBtn = document.querySelector('.toaster-dismiss');

                if (actionBtn) {
                    // Remove UIkit primary button styling
                    actionBtn.classList.remove('uk-button-primary');
                    actionBtn.classList.add('uk-button-danger');

                    // Apply danger button styling using CSS variable
                    actionBtn.style.setProperty('background-color', 'var(--color-danger)', 'important');
                    actionBtn.style.setProperty('border', '1px solid var(--color-danger)', 'important');
                    actionBtn.style.setProperty('color', 'white', 'important');
                    actionBtn.style.setProperty('font-size', '0.875rem', 'important');
                    actionBtn.style.setProperty('padding', '4px 12px', 'important');
                    actionBtn.style.setProperty('transition', 'all 0.2s', 'important');
                    actionBtn.style.setProperty('box-shadow', 'none', 'important');

                    // Hover effect
                    actionBtn.onmouseover = function() {
                        this.style.setProperty('opacity', '0.9', 'important');
                        this.style.setProperty('box-shadow', '0 2px 4px rgba(0, 0, 0, 0.2)', 'important');
                    };
                    actionBtn.onmouseout = function() {
                        this.style.setProperty('opacity', '1', 'important');
                        this.style.setProperty('box-shadow', 'none', 'important');
                    };
                }

                if (dismissBtn) {
                    dismissBtn.style.setProperty('background-color', '#ffffff', 'important');
                    dismissBtn.style.setProperty('border', '1px solid #e5e7eb', 'important');
                    dismissBtn.style.setProperty('color', '#374151', 'important');
                    dismissBtn.style.setProperty('font-size', '0.875rem', 'important');
                    dismissBtn.style.setProperty('padding', '4px 12px', 'important');
                    dismissBtn.style.setProperty('transition', 'all 0.2s', 'important');
                    dismissBtn.onmouseover = function() {
                        this.style.setProperty('background-color', '#f9fafb', 'important');
                        this.style.setProperty('border-color', '#d1d5db', 'important');
                    };
                    dismissBtn.onmouseout = function() {
                        this.style.setProperty('background-color', '#ffffff', 'important');
                        this.style.setProperty('border-color', '#e5e7eb', 'important');
                    };
                }
            }, 10);
        } else if (window.Toaster && typeof window.Toaster.cta === 'function') {
            // Fallback to regular cta if warningCta is not available
            const toastId = window.Toaster.cta(
                `<div style="font-size: 0.95em;">
                    <span style="color: #000;">Delete <strong>${escapeHtml(policyName)}</strong>?</span>
                </div>`,
                {
                    text: 'Delete',
                    dismissText: 'Cancel',
                    callback: async () => {
                        window.activePolicyConfirmation = null;
                        await performPolicyDeletion(policyId);
                    }
                }
            );

            window.activePolicyConfirmation.toastId = toastId;

            // Force warning styling with solid background
            setTimeout(() => {
                const notifications = document.querySelectorAll('.uk-notification-message-primary, .uk-notification-message');
                notifications.forEach(notification => {
                    notification.classList.remove('uk-notification-message-primary');
                    notification.classList.add('uk-notification-message-warning');

                    const solidWarningBg = window.appTheme && window.appTheme.currentMode === 'dark'
                        ? '#52520a'  // Dark mode: solid dark yellow
                        : '#fef08a';  // Light mode: solid pale yellow

                    notification.style.setProperty('background-color', solidWarningBg, 'important');
                    notification.style.setProperty('border', `1px solid ${warningColor}`, 'important');
                    notification.style.setProperty('color', 'var(--color-text-primary)', 'important');
                });

                // Also style the delete button with danger color
                const actionBtn = document.querySelector('.toaster-action');
                if (actionBtn) {
                    actionBtn.classList.remove('uk-button-primary');
                    actionBtn.classList.add('uk-button-danger');
                    actionBtn.style.setProperty('background-color', 'var(--color-danger)', 'important');
                    actionBtn.style.setProperty('border', '1px solid var(--color-danger)', 'important');
                    actionBtn.style.setProperty('color', 'white', 'important');
                }
            }, 10);
        } else if (window.UIkit && window.UIkit.notification) {
            // Use UIkit notification directly as fallback
            const notification = UIkit.notification({
                message: confirmationHtml,
                status: 'warning',
                pos: 'bottom-right',
                timeout: 0
            });

            window.activePolicyConfirmation.toastId = notification;

            // Style the notification with solid warning theme
            setTimeout(() => {
                const notificationEl = document.querySelector('.uk-notification-message-warning');
                if (notificationEl) {
                    // Apply solid warning theme
                    const solidWarningBg = window.appTheme && window.appTheme.currentMode === 'dark'
                        ? '#52520a'  // Dark mode: solid dark yellow
                        : '#fef08a';  // Light mode: solid pale yellow

                    notificationEl.style.setProperty('background-color', solidWarningBg, 'important');
                    notificationEl.style.setProperty('border', `1px solid ${warningColor}`, 'important');
                    notificationEl.style.setProperty('color', 'var(--color-text-primary)', 'important');
                }
                if (window.lucide) lucide.createIcons();
            }, 10);
        } else {
            // Fallback to standard confirm if neither is available
            if (confirm(`Are you sure you want to delete the policy "${policyName}"? This action cannot be undone.`)) {
                await performPolicyDeletion(policyId);
            }
        }
    }

    // Helper function to perform the actual deletion
    async function performPolicyDeletion(policyId) {
        try {
            const response = await fetch(`${POLICIES_API}/${policyId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                // Try to parse the error response
                let errorMessage = 'Failed to delete policy';
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        // Parse the backend error message
                        const match = errorData.detail.match(/Cannot delete policy.*: attached to (\d+) API\(s\)/);
                        if (match) {
                            const apiCount = match[1];
                            errorMessage = `This policy cannot be deleted because it is currently attached to ${apiCount} API configuration${apiCount > 1 ? 's' : ''}. Please detach the policy from all APIs before deleting.`;
                        } else {
                            errorMessage = errorData.detail;
                        }
                    }
                } catch (parseError) {
                    // If parsing fails, use the generic error message
                    console.error('Error parsing error response:', parseError);
                }
                throw new Error(errorMessage);
            }

            showNotification('Policy deleted successfully', 'success');
            await loadPolicies();
        } catch (error) {
            console.error('Error deleting policy:', error);
            showNotification(error.message || 'Failed to delete policy', 'error');
        }
    }

    // Global functions for confirmation handling (for UIkit fallback)
    window.confirmPolicyDeletion = async function(confirmationId, policyId) {
        // Dismiss the confirmation toaster
        if (window.activePolicyConfirmation &&
            window.activePolicyConfirmation.id === confirmationId &&
            window.activePolicyConfirmation.toastId) {
            if (window.activePolicyConfirmation.toastId.close) {
                window.activePolicyConfirmation.toastId.close();
            }
        }
        window.activePolicyConfirmation = null;

        // Perform the deletion
        await performPolicyDeletion(policyId);
    };

    window.cancelPolicyDeletion = function(confirmationId) {
        // Dismiss the confirmation toaster
        if (window.activePolicyConfirmation &&
            window.activePolicyConfirmation.id === confirmationId &&
            window.activePolicyConfirmation.toastId) {
            if (window.activePolicyConfirmation.toastId.close) {
                window.activePolicyConfirmation.toastId.close();
            }
        }
        window.activePolicyConfirmation = null;
    };

    async function viewPolicyStats(policyId) {
        // Set modal title
        const title = document.getElementById('policy-stats-modal-title');
        if (title) {
            const policy = state.policies.find(p => (p.policy_id || p.id) === policyId);
            title.textContent = `Policy Statistics: ${policy ? policy.name : policyId}`;
        }

        // Show loading state
        const content = document.getElementById('policy-stats-content');
        if (content) {
            content.innerHTML = `
                <div class="stats-loading text-center py-8">
                    <div class="uk-spinner uk-spinner-medium theme-text-muted mx-auto mb-4"></div>
                    <p class="theme-text-secondary">Loading statistics...</p>
                </div>
            `;
        }

        // Show modal
        if (window.policyStatsModal) {
            window.policyStatsModal.show();
        }

        try {
            // For now, we'll show a placeholder since the stats endpoint might not be implemented yet
            setTimeout(() => {
                if (content) {
                    content.innerHTML = `
                        <div class="text-center py-8">
                            <i data-lucide="info" class="h-12 w-12 theme-text-muted mx-auto mb-4"></i>
                            <p class="theme-text-secondary">Policy statistics will be available soon</p>
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();
                }
            }, 1000);
        } catch (error) {
            console.error('Error loading policy statistics:', error);
            if (content) {
                content.innerHTML = `
                    <div class="text-center py-8">
                        <i data-lucide="alert-circle" class="h-12 w-12 theme-text-danger mx-auto mb-4"></i>
                        <p class="theme-text-secondary">Failed to load statistics</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
            }
        }
    }

    // Policy Rules Management
    function addPolicyRule() {
        console.log('Adding new policy rule');
        const rule = {
            id: Date.now().toString(),
            metric_key: 'requests_count', // Default to requests_count instead of empty
            operator: 'less_than',
            threshold: 100, // Default to 100 instead of 0
            period: 'daily',
            action: 'block'
        };

        state.policyRules.push(rule);
        console.log('Current rules:', state.policyRules);
        renderPolicyRules();
    }

    function removeRule(ruleId) {
        state.policyRules = state.policyRules.filter(rule => rule.id !== ruleId);
        renderPolicyRules();
    }

    function renderPolicyRules() {
        const container = document.getElementById('policy-rules-container');
        if (!container) return;

        if (state.policyRules.length === 0) {
            container.innerHTML = '<p class="theme-text-secondary text-sm">No rules defined. Click "Add Rule" to create one.</p>';
            return;
        }

        container.innerHTML = state.policyRules.map((rule, index) => {
            const isValid = rule.metric_key &&
                          rule.threshold !== undefined &&
                          rule.threshold !== '' &&
                          !isNaN(rule.threshold);
            const borderClass = isValid ? '' : 'border-red-500 border-2';

            return `
            <div class="policy-rule-item ${borderClass}" data-rule-id="${rule.id}">
                <button type="button" class="policy-rule-remove" data-rule-id="${rule.id}">
                    <i data-lucide="x" class="h-4 w-4"></i>
                </button>

                ${!isValid ? '<p class="text-red-500 text-sm mb-2"><i data-lucide="alert-circle" class="inline h-4 w-4"></i> This rule is incomplete and will not be saved</p>' : ''}

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="text-sm font-medium theme-text-primary mb-1">Metric <span class="text-red-500">*</span></label>
                        <select class="uk-select w-full border ${!rule.metric_key ? 'border-red-500' : 'theme-border'} theme-bg-surface rounded-lg p-2"
                                data-rule-id="${rule.id}" data-field="metric_key">
                            <option value="">Select metric...</option>
                            <option value="requests_count" ${rule.metric_key === 'requests_count' ? 'selected' : ''}>Request Count</option>
                            <option value="total_words_count" ${rule.metric_key === 'total_words_count' ? 'selected' : ''}>Total Words</option>
                            <option value="input_words_count" ${rule.metric_key === 'input_words_count' ? 'selected' : ''}>Input Words</option>
                            <option value="output_words_count" ${rule.metric_key === 'output_words_count' ? 'selected' : ''}>Output Words</option>
                            <option value="credits_used" ${rule.metric_key === 'credits_used' ? 'selected' : ''}>Credits Used</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-sm font-medium theme-text-primary mb-1">Operator</label>
                        <select class="uk-select w-full border theme-border theme-bg-surface rounded-lg p-2"
                                data-rule-id="${rule.id}" data-field="operator">
                            <option value="less_than" ${rule.operator === 'less_than' ? 'selected' : ''}>Less Than</option>
                            <option value="less_than_or_equal" ${rule.operator === 'less_than_or_equal' ? 'selected' : ''}>Less Than or Equal</option>
                            <option value="greater_than" ${rule.operator === 'greater_than' ? 'selected' : ''}>Greater Than</option>
                            <option value="greater_than_or_equal" ${rule.operator === 'greater_than_or_equal' ? 'selected' : ''}>Greater Than or Equal</option>
                            <option value="equal" ${rule.operator === 'equal' ? 'selected' : ''}>Equal To</option>
                            <option value="not_equal" ${rule.operator === 'not_equal' ? 'selected' : ''}>Not Equal To</option>
                        </select>
                    </div>

                    <div>
                        <label class="text-sm font-medium theme-text-primary mb-1">Threshold <span class="text-red-500">*</span></label>
                        <input type="number"
                               class="uk-input w-full border ${rule.threshold === undefined || rule.threshold === '' ? 'border-red-500' : 'theme-border'} theme-bg-surface rounded-lg p-2"
                               value="${rule.threshold}"
                               data-rule-id="${rule.id}" data-field="threshold"
                               placeholder="e.g., 1000"
                               required>
                    </div>

                    <div>
                        <label class="text-sm font-medium theme-text-primary mb-1">Period</label>
                        <select class="uk-select w-full border theme-border theme-bg-surface rounded-lg p-2"
                                data-rule-id="${rule.id}" data-field="period">
                            <option value="hourly" ${rule.period === 'hourly' ? 'selected' : ''}>Hourly</option>
                            <option value="daily" ${rule.period === 'daily' ? 'selected' : ''}>Daily</option>
                            <option value="monthly" ${rule.period === 'monthly' ? 'selected' : ''}>Monthly</option>
                            <option value="total" ${rule.period === 'total' ? 'selected' : ''}>Total (Lifetime)</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
        }).join('');

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons();

        // Setup event handlers for rule controls
        setupRuleEventHandlers();
    }

    function setupRuleEventHandlers() {
        const container = document.getElementById('policy-rules-container');
        if (!container) return;

        // Remove button handlers
        container.querySelectorAll('.policy-rule-remove').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const ruleId = this.getAttribute('data-rule-id');
                removeRule(ruleId);
            });
        });

        // Select handlers
        container.querySelectorAll('select[data-rule-id]').forEach(select => {
            select.addEventListener('change', function() {
                const ruleId = this.getAttribute('data-rule-id');
                const field = this.getAttribute('data-field');
                updateRule(ruleId, field, this.value);
                if (field === 'metric_key') {
                    renderPolicyRules(); // Re-render for validation
                }
            });
        });

        // Input handlers
        container.querySelectorAll('input[data-rule-id]').forEach(input => {
            input.addEventListener('change', function() {
                const ruleId = this.getAttribute('data-rule-id');
                const field = this.getAttribute('data-field');
                let value = this.value;

                if (field === 'threshold') {
                    // Parse as float but keep empty string as empty
                    value = this.value === '' ? '' : parseFloat(this.value);
                    // If parsing failed, set to 0
                    if (this.value !== '' && isNaN(value)) {
                        value = 0;
                    }
                }

                updateRule(ruleId, field, value);
                renderPolicyRules(); // Re-render for validation
            });
        });
    }

    function updateRule(ruleId, field, value) {
        const rule = state.policyRules.find(r => r.id === ruleId);
        if (rule) {
            rule[field] = value;
        }
    }

    async function handlePolicyFormSubmit(e) {
        e.preventDefault();

        const submitBtn = document.getElementById('policy-submit-btn');
        const spinner = document.getElementById('policy-spinner');

        if (submitBtn) submitBtn.disabled = true;
        if (spinner) spinner.classList.remove('hidden');

        try {
            const policyId = document.getElementById('policy-id').value;
            const isEdit = !!policyId;

            console.log('Form submit - Policy ID:', policyId);
            console.log('Is edit mode:', isEdit);

            // Validate rules
            const allRules = state.policyRules;
            const validRules = state.policyRules.filter(rule =>
                rule.metric_key &&
                rule.threshold !== undefined &&
                rule.threshold !== '' &&
                !isNaN(rule.threshold)
            );

            // Warn about incomplete rules
            if (allRules.length > validRules.length) {
                const invalidCount = allRules.length - validRules.length;
                showNotification(`${invalidCount} incomplete rule(s) were not saved. Please select a metric and set a threshold for all rules.`, 'warning');
            }

            if (validRules.length === 0) {
                throw new Error('Please add at least one complete rule with a metric and threshold');
            }

            // Get form values
            const policyName = document.getElementById('policy-name').value;
            const policyDescription = document.getElementById('policy-description').value;
            const enforcementMode = document.getElementById('policy-enforcement-mode').value;

            // Validate form fields
            if (!policyName || policyName.trim() === '') {
                throw new Error('Please enter a policy name');
            }

            const policyData = {
                name: policyName.trim(),
                description: policyDescription ? policyDescription.trim() : '',
                type: 'combined',  // Default to combined type
                rules: validRules.map(rule => ({
                    metric_key: rule.metric_key,
                    operator: rule.operator,
                    threshold: rule.threshold,
                    period: rule.period,
                    action: rule.action || 'block'
                })),
                settings: {
                    enforcement_mode: enforcementMode || 'block'
                }
            };

            console.log('Sending policy data:', JSON.stringify(policyData, null, 2));

            const url = isEdit ? `${POLICIES_API}/${policyId}` : POLICIES_API;
            const method = isEdit ? 'PUT' : 'POST';

            console.log(`Making ${method} request to ${url}`);

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(policyData)
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                let errorMessage = 'Failed to save policy';
                try {
                    const error = await response.json();
                    errorMessage = error.detail || errorMessage;
                } catch (e) {
                    // If response is not JSON, use status text
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(errorMessage);
            }

            showNotification(
                isEdit ? 'Policy updated successfully' : 'Policy created successfully',
                'success'
            );

            // Close modal and reload policies
            if (window.policyModal) {
                window.policyModal.hide();
            }

            await loadPolicies();
        } catch (error) {
            console.error('Error saving policy:', error);
            showNotification(error.message || 'Failed to save policy', 'error');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
            if (spinner) spinner.classList.add('hidden');
            // Re-enable form elements
            const form = document.getElementById('policy-form');
            if (form) {
                form.querySelectorAll('input, select, textarea, button').forEach(el => {
                    if (el.id !== 'policy-submit-btn') {
                        el.disabled = false;
                    }
                });
            }
        }
    }

    // Policy Attachment Functions
    async function attachPolicyToConfig(configId, policyId) {
        if (!policyId) {
            // Detach policy if empty
            return detachPolicyFromConfig(configId);
        }

        try {
            const response = await fetch(`${POLICIES_API}/attach`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    policy_id: policyId,
                    api_config_id: configId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to attach policy');
            }

            showNotification('Policy attached successfully', 'success');
            await loadConfigurations();
        } catch (error) {
            console.error('Error attaching policy:', error);
            showNotification('Failed to attach policy', 'error');
        }
    }

    async function detachPolicyFromConfig(configId) {
        try {
            const response = await fetch(`${POLICIES_API}/detach/${configId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to detach policy');
            }

            showNotification('Policy detached successfully', 'success');
            await loadConfigurations();
        } catch (error) {
            console.error('Error detaching policy:', error);
            showNotification('Failed to detach policy', 'error');
        }
    }

    // Make functions globally available
    window.addPolicyRule = addPolicyRule;
    window.removeRule = removeRule;
    window.updateRule = updateRule;
    window.editPolicy = editPolicy;
    window.deletePolicy = deletePolicy;
    window.viewPolicyStats = viewPolicyStats;
    window.attachPolicyToConfig = attachPolicyToConfig;

    // Usage Metrics
    async function loadUsageMetrics() {
        console.log('Loading usage metrics...');
        showLoading('usage');

        try {
            const response = await fetch(`${API_BASE}/usage`);
            if (!response.ok) {
                console.warn('Usage metrics endpoint returned:', response.status, response.statusText);
                // Show empty metrics instead of error
                displayUsageMetrics([]);
                return;
            }

            const metrics = await response.json();
            console.log('Usage metrics loaded:', metrics);
            displayUsageMetrics(metrics);
        } catch (error) {
            console.error('Error loading usage metrics:', error);
            // Show empty metrics instead of error to avoid blocking UI
            displayUsageMetrics([]);
        }
    }

    function displayUsageMetrics(metrics) {
        hideLoading('usage');

        // Calculate totals
        let totalRequests = 0;
        let totalInput = 0;
        let totalOutput = 0;

        if (Array.isArray(metrics)) {
            metrics.forEach(metric => {
                totalRequests += metric.total_requests || 0;
                totalInput += metric.total_input_word_count || 0;
                totalOutput += metric.total_output_word_count || 0;
            });
        }

        // Update summary metrics
        const totalRequestsEl = document.getElementById('total-requests');
        const totalInputEl = document.getElementById('total-input');
        const totalOutputEl = document.getElementById('total-output');
        const activeConfigsEl = document.getElementById('active-configs');

        if (totalRequestsEl) totalRequestsEl.textContent = totalRequests.toLocaleString();
        if (totalInputEl) totalInputEl.textContent = totalInput.toLocaleString();
        if (totalOutputEl) totalOutputEl.textContent = totalOutput.toLocaleString();
        if (activeConfigsEl) activeConfigsEl.textContent = Array.isArray(metrics) ? metrics.length : 0;

        // Display usage details
        const detailsContainer = document.getElementById('usage-details');
        if (detailsContainer) {
            if (!Array.isArray(metrics) || metrics.length === 0) {
                detailsContainer.innerHTML = '<p class="theme-text-muted text-center py-4">No usage data available</p>';
            } else {
                detailsContainer.innerHTML = metrics.map(metric => `
                    <div class="flex items-center justify-between py-3 border-b theme-border border-opacity-50 last:border-b-0">
                        <div>
                            <h4 class="font-medium theme-text-primary">${escapeHtml(metric.api_config_id || 'Unknown')}</h4>
                            <p class="text-sm theme-text-secondary">${(metric.total_requests || 0).toLocaleString()} requests</p>
                        </div>
                        <div class="text-right text-sm theme-text-secondary">
                            <div>Input: ${(metric.total_input_word_count || 0).toLocaleString()} words</div>
                            <div>Output: ${(metric.total_output_word_count || 0).toLocaleString()} words</div>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    // Top Users
    async function loadTopUsers() {
        showLoading('users');

        try {
            // For now, show empty state since endpoint might not be available
            setTimeout(() => {
                showEmpty('users');
            }, 500);
        } catch (error) {
            console.error('Error loading top users:', error);
            showError('users', 'Failed to load top users');
        }
    }

    // State Management Functions
    function showLoading(section) {
        const loading = document.getElementById(`${section}-loading`);
        const list = document.getElementById(`${section}-list`);
        const empty = document.getElementById(`${section}-empty`);
        const error = document.getElementById(`${section}-error`);

        if (loading) loading.classList.remove('hidden');
        if (list) list.classList.add('hidden');
        if (empty) empty.classList.add('hidden');
        if (error) error.classList.add('hidden');
    }

    function hideLoading(section) {
        const loading = document.getElementById(`${section}-loading`);
        const list = document.getElementById(`${section}-list`);

        if (loading) loading.classList.add('hidden');
        if (list) list.classList.remove('hidden');
    }

    function showEmpty(section) {
        const loading = document.getElementById(`${section}-loading`);
        const list = document.getElementById(`${section}-list`);
        const empty = document.getElementById(`${section}-empty`);
        const error = document.getElementById(`${section}-error`);

        if (loading) loading.classList.add('hidden');
        if (list) list.classList.add('hidden');
        if (empty) empty.classList.remove('hidden');
        if (error) error.classList.add('hidden');
    }

    function showError(section, message) {
        const loading = document.getElementById(`${section}-loading`);
        const list = document.getElementById(`${section}-list`);
        const empty = document.getElementById(`${section}-empty`);
        const error = document.getElementById(`${section}-error`);
        const errorMessage = document.getElementById(`${section}-error-message`);

        if (loading) loading.classList.add('hidden');
        if (list) list.classList.add('hidden');
        if (empty) empty.classList.add('hidden');
        if (error) error.classList.remove('hidden');
        if (errorMessage) errorMessage.textContent = message;
    }

    // Utility Functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatTimestamp(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }

    function getFileExtension(fileName) {
        return fileName.split('.').pop().toLowerCase();
    }

    function getFileTypeIcon(type) {
        const iconMap = {
            'txt': 'file-text',
            'md': 'file-text',
            'json': 'file-code',
            'js': 'file-code',
            'py': 'file-code',
            'html': 'file-code',
            'css': 'file-code',
            'pdf': 'file',
            'doc': 'file',
            'docx': 'file',
            'xls': 'file',
            'xlsx': 'file',
            'png': 'image',
            'jpg': 'image',
            'jpeg': 'image',
            'gif': 'image',
            'svg': 'image'
        };
        return iconMap[type] || 'file';
    }

    function showNotification(message, type = 'info') {
        // Ensure Toaster is initialized
        if (window.Toaster && typeof window.Toaster.init === 'function') {
            // Initialize if not already done
            if (!window.Toaster._initialized) {
                window.Toaster.init();
                window.Toaster._initialized = true;
            }

            switch(type) {
                case 'success':
                    window.Toaster.success(message);
                    break;
                case 'warning':
                    window.Toaster.warning(message);
                    break;
                case 'error':
                case 'danger':
                    window.Toaster.error(message);
                    break;
                default:
                    window.Toaster.info(message);
            }
        } else if (window.UIkit && UIkit.notification) {
            // Fallback to UIkit notification
            UIkit.notification({
                message: message,
                status: type === 'error' ? 'danger' : (type === 'success' ? 'success' : 'primary'),
                pos: 'bottom-right',
                timeout: 5000
            });
        } else {
            // Fallback to alert for now
            alert(message);
        }
    }

    // Clear all functions
    function clearAllUsers() {
        state.userAutocomplete.selectedUsers = [];
        renderSelectedUsers();
        updateHiddenUsersInput();
    }

    function clearAllDatasets() {
        state.datasetAutocomplete.selectedDatasets = [];
        renderSelectedDatasets();
        updateHiddenDatasetsInput();
    }

    // Make functions globally available for onclick handlers
    window.editConfig = editConfig;
    window.deleteConfig = deleteConfig;
    window.viewConfigStats = viewConfigStats;
    window.removeUser = removeUser;
    window.removeDataset = removeDataset;
    window.clearAllUsers = clearAllUsers;
    window.clearAllDatasets = clearAllDatasets;

    // Make initialization function globally available for dynamic loading
    window.initializeApiConfigs = initializeApiConfigs;

    // Also make sure openCreatePolicyModal is available immediately
    // in case HTML is loaded before JS initialization completes
    if (!window.openCreatePolicyModal) {
        window.openCreatePolicyModal = openCreatePolicyModal;
    }
})();
