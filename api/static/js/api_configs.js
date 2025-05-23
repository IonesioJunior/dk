// Advanced API Configuration Manager - Based on another_example.html patterns
(function() {
    'use strict';

    // Constants
    const API_BASE = '/api/api_configs';
    const DOCUMENTS_API = '/api/documents-collection';
    const USERS_API = '/api/active-users';

    // State management
    const state = {
        configs: [],
        currentTab: 'configs',
        searchQuery: '',
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
        }
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
            { id: 'empty-create-btn', handler: openCreateConfigModal }
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

                if (configModalEl && window.UIkit) {
                    const configModal = UIkit.modal(configModalEl);
                    window.configModal = configModal;
                }

                if (statsModalEl && window.UIkit) {
                    const statsModal = UIkit.modal(statsModalEl);
                    window.statsModal = statsModal;
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
    }

    function handleSearch(e) {
        state.searchQuery = e.target.value.toLowerCase();
        filterAndRenderConfigs();
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
            const response = await fetch(API_BASE);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const configs = await response.json();
            console.log('Loaded configs:', configs);
            state.configs = configs;
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
                config.id.toLowerCase().includes(state.searchQuery) ||
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
            const configId = config.id || config.config_id;
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

                        <div class="flex justify-between items-center pt-4 border-t theme-border">
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
            document.getElementById('config-id').value = config.id || config.config_id;

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
                total_input_size: 0,
                total_output_size: 0,
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
                            <h4 class="font-medium theme-text-primary">Input Size</h4>
                        </div>
                        <div class="stats-card-value">${formatBytes(stats.total_input_size || 0)}</div>
                    </div>

                    <div class="stats-card">
                        <div class="stats-card-header">
                            <i data-lucide="message-circle" class="stats-card-icon"></i>
                            <h4 class="font-medium theme-text-primary">Output Size</h4>
                        </div>
                        <div class="stats-card-value">${formatBytes(stats.total_output_size || 0)}</div>
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
                totalInput += metric.total_input_size || 0;
                totalOutput += metric.total_output_size || 0;
            });
        }

        // Update summary metrics
        const totalRequestsEl = document.getElementById('total-requests');
        const totalInputEl = document.getElementById('total-input');
        const totalOutputEl = document.getElementById('total-output');
        const activeConfigsEl = document.getElementById('active-configs');

        if (totalRequestsEl) totalRequestsEl.textContent = totalRequests.toLocaleString();
        if (totalInputEl) totalInputEl.textContent = formatBytes(totalInput);
        if (totalOutputEl) totalOutputEl.textContent = formatBytes(totalOutput);
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
                            <div>Input: ${formatBytes(metric.total_input_size || 0)}</div>
                            <div>Output: ${formatBytes(metric.total_output_size || 0)}</div>
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
})();
