// Advanced API Configuration Manager - Based on another_example.html patterns
(function() {
    'use strict';

    // Log initial state
    console.log('=== api_configs.js loading ===');
    console.log('window object:', typeof window);

    // Define critical functions on window immediately for inline handlers
    window.switchPolicyTab = function(tabName) {
        console.log('=== window.switchPolicyTab called with:', tabName);
        console.log('Called from:', new Error().stack.split('\n')[2]);

        // Check if we're in the modal context
        const modal = document.getElementById('policy-modal');
        if (!modal) {
            console.error('Policy modal not found!');
            return;
        }

        // Update tab buttons
        const tabBtns = document.querySelectorAll('.policy-tab-btn');
        console.log('Found tab buttons:', tabBtns.length);

        tabBtns.forEach(btn => {
            const btnTab = btn.getAttribute('data-tab');
            console.log(`Checking button with data-tab="${btnTab}"`);

            if (btnTab === tabName) {
                btn.classList.add('active');
                console.log(`Activated tab: ${btnTab}`);
            } else {
                btn.classList.remove('active');
            }
        });

        // Update tab content
        const tabContents = document.querySelectorAll('.policy-tab-content');
        console.log('Found tab contents:', tabContents.length);

        tabContents.forEach(content => {
            const contentId = content.id;
            console.log(`Checking content with id="${contentId}"`);

            if (contentId === `policy-tab-${tabName}`) {
                content.classList.remove('hidden');
                content.style.display = 'block';
                console.log(`Showing content: ${contentId}`);
            } else {
                content.classList.add('hidden');
                content.style.display = 'none';
                console.log(`Hiding content: ${contentId}`);
            }
        });

        // Initialize Lucide icons for the new content
        if (window.lucide) {
            lucide.createIcons();
            console.log('Lucide icons refreshed');
        }

        console.log('=== window.switchPolicyTab completed');
    };

    // Define all possible variations that might be generated
    window.SwitchPolicyTab = window.switchPolicyTab;
    window.switchpolicytab = window.switchPolicyTab;
    window.SWITCHPOLICYTAB = window.switchPolicyTab;
    window.Switchpolicytab = window.switchPolicyTab;

    // Also define on the global object directly
    globalThis.switchPolicyTab = window.switchPolicyTab;
    globalThis.SwitchPolicyTab = window.switchPolicyTab;

    // Override any attempts to call undefined functions
    const handler = {
        get: function(target, property) {
            if (property.toLowerCase() === 'switchpolicytab' && !target[property]) {
                console.log(`Property ${property} accessed, redirecting to switchPolicyTab`);
                return window.switchPolicyTab;
            }
            return target[property];
        }
    };

    // Try to wrap window in a Proxy if supported
    try {
        if (typeof Proxy !== 'undefined') {
            // This might not work in all browsers but worth trying
            Object.setPrototypeOf(window, new Proxy(Object.getPrototypeOf(window), handler));
        }
    } catch (e) {
        console.log('Could not set up Proxy for window');
    }

    // Test that switchPolicyTab is available
    console.log('window.switchPolicyTab is defined:', typeof window.switchPolicyTab === 'function');
    console.log('window.SwitchPolicyTab is defined:', typeof window.SwitchPolicyTab === 'function');

    // Verify setup after a short delay
    setTimeout(() => {
        console.log('=== Verification after 1 second ===');
        console.log('window.switchPolicyTab:', typeof window.switchPolicyTab);
        console.log('window.SwitchPolicyTab:', typeof window.SwitchPolicyTab);
        console.log('All switch variants on window:', Object.keys(window).filter(k => k.toLowerCase().includes('switchpolicy')));
    }, 1000);

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
        // New usage stats modal doesn't need cleanup as it's handled by the custom implementation

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
        }
    }

    // Modal Setup
    function setupModals() {
        try {
            // Wait a bit for UIkit to be available and DOM to settle
            setTimeout(() => {
                // Check if modal elements exist before initializing
                const configModalEl = document.getElementById('config-modal');
                const policyModalEl = document.getElementById('policy-modal');
                const policyStatsModalEl = document.getElementById('policy-stats-modal');

                if (configModalEl && window.UIkit) {
                    const configModal = UIkit.modal(configModalEl);
                    window.configModal = configModal;
                }

                // New usage stats modal doesn't need UIkit initialization
                // It's handled by the custom modal implementation

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

                    // Add modal shown handler to ensure proper initialization
                    policyModalEl.addEventListener('shown', function() {
                        console.log('Policy modal shown event');
                        // Re-initialize Lucide icons
                        if (window.lucide) lucide.createIcons();

                        // Always set up handlers when modal is shown
                        // This is crucial because UIkit might move/clone the modal content
                        setupPolicyModalHandlers();

                        // Debug: Check modal structure
                        console.log('Modal DOM structure after shown:');
                        console.log('policy-tab-nav exists:', !!document.getElementById('policy-tab-nav'));
                        console.log('policy-form exists:', !!document.getElementById('policy-form'));

                        // Set up form submit handler
                        const policyForm = document.getElementById('policy-form');
                        if (policyForm && !policyForm.hasAttribute('data-handler-attached')) {
                            policyForm.setAttribute('data-handler-attached', 'true');
                            policyForm.addEventListener('submit', handlePolicyFormSubmit);
                            console.log('Policy form submit handler attached');
                        }
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

    // Global variables for the usage stats modal
    let currentConfigId = null;

    async function viewConfigStats(configId) {
        currentConfigId = configId;

        // Update modal subtitle
        const subtitle = document.getElementById('stats-config-name');
        if (subtitle) {
            subtitle.textContent = `Configuration ID: ${configId.slice(0, 8)}...`;
        }

        // Show modal
        const modal = document.getElementById('usage-stats-modal');
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        // Load statistics
        await loadUsageStatistics(configId);
    }

    function closeUsageStatsModal() {
        const modal = document.getElementById('usage-stats-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }

    }

    async function loadUsageStatistics(configId) {
        const content = document.getElementById('usage-stats-content');
        if (!content) return;

        // Show loading state
        content.innerHTML = `
            <div class="usage-stats-loading">
                <div class="loading-spinner"></div>
                <p class="loading-text">Loading usage analytics...</p>
            </div>
        `;

        try {
            // Fetch all required data
            const [usageResponse, topUsersResponse] = await Promise.all([
                fetch(`${API_BASE}/${configId}/usage`),
                fetch(`${API_BASE}/${configId}/top-users?limit=10`)
            ]);

            const stats = usageResponse.ok ? await usageResponse.json() : {
                total_requests: 0,
                total_input_word_count: 0,
                total_output_word_count: 0,
                last_updated: null
            };

            const topUsersData = topUsersResponse.ok ? await topUsersResponse.json() : { top_users: [] };
            const topUsers = topUsersData.top_users || [];


            // Update last updated timestamp
            const lastUpdated = stats.last_updated
                ? new Date(stats.last_updated).toLocaleString()
                : 'Never';
            document.getElementById('stats-last-updated').textContent = `Last updated: ${lastUpdated}`;

            // Render the statistics content
            content.innerHTML = `
                <!-- Metrics Grid -->
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-card-header">
                            <div class="metric-card-info">
                                <div class="metric-card-title">Total Requests</div>
                                <div class="metric-card-value">${(stats.total_requests || 0).toLocaleString()}</div>
                            </div>
                            <div class="metric-card-icon requests">
                                <i data-lucide="activity"></i>
                            </div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <div class="metric-card-header">
                            <div class="metric-card-info">
                                <div class="metric-card-title">Input Words</div>
                                <div class="metric-card-value">${(stats.total_input_word_count || 0).toLocaleString()}</div>
                            </div>
                            <div class="metric-card-icon input">
                                <i data-lucide="message-square"></i>
                            </div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <div class="metric-card-header">
                            <div class="metric-card-info">
                                <div class="metric-card-title">Output Words</div>
                                <div class="metric-card-value">${(stats.total_output_word_count || 0).toLocaleString()}</div>
                            </div>
                            <div class="metric-card-icon output">
                                <i data-lucide="message-circle"></i>
                            </div>
                        </div>
                    </div>

                    <div class="metric-card">
                        <div class="metric-card-header">
                            <div class="metric-card-info">
                                <div class="metric-card-title">Active Users</div>
                                <div class="metric-card-value">${topUsers.length}</div>
                            </div>
                            <div class="metric-card-icon users">
                                <i data-lucide="users"></i>
                            </div>
                        </div>
                    </div>
                </div>


                <!-- User Activity Table -->
                <div class="user-activity-section">
                    <div class="user-activity-header">
                        <h3 class="user-activity-title">
                            <i data-lucide="users" style="width: 20px; height: 20px;"></i>
                            Top Users Activity
                        </h3>
                        <div class="user-search">
                            <i data-lucide="search" class="user-search-icon"></i>
                            <input type="text" class="user-search-input" placeholder="Search users..." onkeyup="filterUserTable(this.value)">
                        </div>
                    </div>

                    ${topUsers.length > 0 ? `
                        <table class="user-table" id="user-activity-table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Requests</th>
                                    <th>Input Words</th>
                                    <th>Output Words</th>
                                    <th>Usage</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${topUsers.map((user, index) => {
                                    const maxCount = topUsers[0]?.count || 1;
                                    const percentage = (user.count / maxCount) * 100;
                                    const initials = user.user_id.substring(0, 2).toUpperCase();

                                    return `
                                        <tr>
                                            <td>
                                                <div class="user-info">
                                                    <div class="user-avatar">${initials}</div>
                                                    <span class="user-name">${escapeHtml(user.user_id)}</span>
                                                </div>
                                            </td>
                                            <td>${user.count.toLocaleString()}</td>
                                            <td>${Math.floor(user.count * 150).toLocaleString()}</td>
                                            <td>${Math.floor(user.count * 200).toLocaleString()}</td>
                                            <td>
                                                <div class="usage-bar">
                                                    <div class="usage-bar-fill" style="width: ${percentage}%"></div>
                                                </div>
                                            </td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    ` : `
                        <div class="empty-state">
                            <i data-lucide="users" class="empty-state-icon"></i>
                            <h3 class="empty-state-title">No User Activity</h3>
                            <p class="empty-state-text">No usage data available for the selected time period.</p>
                        </div>
                    `}
                </div>
            `;

            // Initialize Lucide icons
            if (window.lucide) lucide.createIcons({ container: content });


        } catch (error) {
            console.error('Error loading usage statistics:', error);
            content.innerHTML = `
                <div class="empty-state">
                    <i data-lucide="alert-circle" class="empty-state-icon"></i>
                    <h3 class="empty-state-title">Failed to Load Statistics</h3>
                    <p class="empty-state-text">${error.message}</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons({ container: content });
        }
    }


    window.filterUserTable = function(searchTerm) {
        const table = document.getElementById('user-activity-table');
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        const term = searchTerm.toLowerCase();

        rows.forEach(row => {
            const userName = row.querySelector('.user-name')?.textContent.toLowerCase() || '';
            if (userName.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    };

    window.refreshUsageStats = async function() {
        if (currentConfigId) {
            await loadUsageStatistics(currentConfigId);
        }
    };

    window.closeUsageStatsModal = closeUsageStatsModal;

    // Add click outside to close functionality
    document.addEventListener('DOMContentLoaded', () => {
        const modal = document.getElementById('usage-stats-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeUsageStatsModal();
                }
            });
        }
    });

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
            const policyId = policy.policy_id;
            const attachedAPIs = policy.api_configs || [];
            const rules = policy.rules || [];
            const isActive = policy.is_active !== false;
            const enforcementMode = policy.settings?.enforcement_mode || 'block';
            const violations = policy.violations_count || 0;

            return `
                <div class="policy-card theme-bg-surface rounded-xl shadow-sm theme-border border">
                    <div class="p-6">
                        <!-- Header with Status Badge -->
                        <div class="flex items-start justify-between mb-4">
                            <div class="flex-1">
                                <div class="flex items-center gap-3 mb-2">
                                    <h3 class="text-lg font-semibold theme-text-primary">
                                        ${escapeHtml(policy.name)}
                                    </h3>
                                    <span class="policy-status-badge ${isActive ? 'active' : 'inactive'}">
                                        ${isActive ? 'Active' : 'Inactive'}
                                    </span>
                                    <span class="px-2 py-1 text-xs rounded-full ${enforcementMode === 'block' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
                                        <i data-lucide="${enforcementMode === 'block' ? 'shield' : 'eye'}" class="inline h-3 w-3 mr-1"></i>
                                        ${enforcementMode === 'block' ? 'Blocking' : 'Monitoring'}
                                    </span>
                                </div>
                                ${policy.description ? `
                                    <p class="theme-text-secondary text-sm">${escapeHtml(policy.description)}</p>
                                ` : ''}
                            </div>
                            <div class="policy-actions flex space-x-2 ml-4">
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

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                            <!-- Rules Section -->
                            <div class="space-y-2">
                                <div class="flex items-center gap-2 text-sm font-medium theme-text-secondary">
                                    <i data-lucide="shield-check" class="h-4 w-4 theme-primary"></i>
                                    <span>Rules (${rules.length})</span>
                                </div>
                                <div class="border theme-border rounded-lg p-2 overflow-y-auto" style="height: 108px;">
                                    ${rules.length > 0
                                        ? '<div class="space-y-1">' + rules.map(rule => {
                                            const metricNames = {
                                                'requests_count': 'Requests',
                                                'total_words_count': 'Total Words',
                                                'input_words_count': 'Input Words',
                                                'output_words_count': 'Output Words',
                                                'credits_used': 'Credits'
                                            };
                                            const periodNames = {
                                                'hourly': '/hr',
                                                'daily': '/day',
                                                'monthly': '/mo',
                                                'total': 'total'
                                            };
                                            const operatorSymbols = {
                                                'less_than': '<',
                                                'less_than_or_equal': '≤',
                                                'greater_than': '>',
                                                'greater_than_or_equal': '≥',
                                                'equal': '=',
                                                'not_equal': '≠'
                                            };

                                            return `
                                                <div class="flex items-center gap-2 p-1.5 hover:theme-bg-surface rounded transition-colors">
                                                    <div class="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                                                        <i data-lucide="check" class="h-3 w-3"></i>
                                                    </div>
                                                    <span class="text-xs theme-text-primary truncate">
                                                        ${metricNames[rule.metric_key]} ${operatorSymbols[rule.operator]} ${rule.threshold.toLocaleString()} ${periodNames[rule.period]}
                                                    </span>
                                                </div>
                                            `;
                                        }).join('') + '</div>'
                                        : '<div class="h-full flex items-center justify-center"><p class="text-xs theme-text-muted">No rules defined</p></div>'
                                    }
                                </div>
                            </div>

                            <!-- Attached APIs Section -->
                            <div class="space-y-2">
                                <div class="flex items-center gap-2 text-sm font-medium theme-text-secondary">
                                    <i data-lucide="link" class="h-4 w-4 theme-primary"></i>
                                    <span>Attached APIs (${attachedAPIs.length})</span>
                                </div>
                                <div class="border theme-border rounded-lg p-2 overflow-y-auto" style="height: 108px;">
                                    ${attachedAPIs.length > 0
                                        ? '<div class="space-y-1">' + attachedAPIs.map(apiConfig => {
                                            const api = state.configs?.find(c => c.config_id === apiConfig) || {};
                                            return `
                                                <div class="flex items-center gap-2 p-1.5 hover:theme-bg-surface rounded transition-colors">
                                                    <div class="w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                                                        ${api.name?.substring(0, 2).toUpperCase() || 'AP'}
                                                    </div>
                                                    <span class="text-xs theme-text-primary truncate">${api.name || apiConfig.substring(0, 12) + '...'}</span>
                                                </div>
                                            `;
                                        }).join('') + '</div>'
                                        : '<div class="h-full flex items-center justify-center"><p class="text-xs theme-text-muted">No APIs attached</p></div>'
                                    }
                                </div>
                            </div>
                        </div>

                        <!-- Statistics Bar -->
                        <div class="grid grid-cols-3 gap-4 mb-4 p-4 theme-bg-background rounded-lg stats-mini-card">
                            <div class="text-center">
                                <p class="text-2xl font-bold theme-text-primary">${violations || 0}</p>
                                <p class="text-xs theme-text-secondary">Violations</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold theme-text-primary">${policy.blocked_requests || 0}</p>
                                <p class="text-xs theme-text-secondary">Blocked</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold theme-text-primary">${policy.total_requests || 0}</p>
                                <p class="text-xs theme-text-secondary">Total Requests</p>
                            </div>
                        </div>

                        <!-- Footer with Timestamps -->
                        <div class="flex justify-between items-center pt-4 theme-border border-t text-xs theme-text-secondary">
                            <span>Created ${new Date(policy.created_at).toLocaleDateString()}</span>
                            ${policy.last_evaluated ? `
                                <span>Last evaluated ${timeAgo(policy.last_evaluated)}</span>
                            ` : ''}
                            ${policy.updated_at ? `
                                <span>Updated ${new Date(policy.updated_at).toLocaleDateString()}</span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Initialize Lucide icons
        if (window.lucide) lucide.createIcons();
    }

    // Helper function for relative time
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        const intervals = {
            year: 31536000,
            month: 2592000,
            week: 604800,
            day: 86400,
            hour: 3600,
            minute: 60
        };

        for (const [unit, secondsInUnit] of Object.entries(intervals)) {
            const interval = Math.floor(seconds / secondsInUnit);
            if (interval >= 1) {
                return `${interval} ${unit}${interval === 1 ? '' : 's'} ago`;
            }
        }
        return 'just now';
    }

    function openCreatePolicyModal() {
        console.log('Opening create policy modal');

        // Reset form
        const form = document.getElementById('policy-form');
        if (form) {
            form.reset();
            console.log('Form reset');
        }

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

        // Reset to General tab
        window.switchPolicyTab('general');

        // Enable submit button
        const submitBtn = document.getElementById('policy-submit-btn');
        if (submitBtn) submitBtn.disabled = false;

        // Clear validation message
        const validationMsg = document.getElementById('policy-validation-message');
        if (validationMsg) validationMsg.textContent = '';

        // Show modal
        if (window.policyModal) {
            console.log('Showing policy modal');
            window.policyModal.show();

            // Don't rely on timeout, setup handlers immediately
            setupPolicyModalHandlers();
            validatePolicyForm();

            // Also setup after a delay as backup
            setTimeout(() => {
                console.log('Setting up handlers again after delay');
                setupPolicyModalHandlers();
                validatePolicyForm();
            }, 200);
        } else {
            console.error('Policy modal not initialized');
            showNotification('Policy modal not initialized. Please refresh the page.', 'error');
        }
    }

    function setupPolicyModalHandlers() {
        console.log('Setting up policy modal handlers');

        // Use event delegation on the nav container
        const tabNav = document.getElementById('policy-tab-nav');
        if (tabNav) {
            console.log('Setting up event delegation on policy-tab-nav');

            // Clone and replace to remove ALL event listeners
            const newTabNav = tabNav.cloneNode(true);
            tabNav.parentNode.replaceChild(newTabNav, tabNav);

            // Now work with the new element
            const cleanTabNav = document.getElementById('policy-tab-nav');

            // Add click handler using event delegation
            cleanTabNav.addEventListener('click', function(e) {
                console.log('Click event on tab nav, target:', e.target);

                // Find the closest button
                let button = e.target.closest('.policy-tab-btn');
                if (button) {
                    e.preventDefault();
                    e.stopPropagation();
                    const tabName = button.getAttribute('data-tab');
                    console.log('Tab button clicked via delegation:', tabName);

                    // Call the function directly
                    if (typeof window.switchPolicyTab === 'function') {
                        window.switchPolicyTab(tabName);
                    } else {
                        console.error('window.switchPolicyTab is not a function!');
                        console.log('Available on window:', Object.keys(window).filter(k => k.toLowerCase().includes('switch')));
                    }
                    return false;
                }
            }, true); // Use capture phase

            // Also add individual click handlers as backup
            const buttons = cleanTabNav.querySelectorAll('.policy-tab-btn');
            buttons.forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const tabName = this.getAttribute('data-tab');
                    console.log('Direct button click:', tabName);
                    window.switchPolicyTab(tabName);
                });
            });
        } else {
            console.error('policy-tab-nav not found!');
        }

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
                    // Switch to rules tab if not already there
                    window.switchPolicyTab('rules');
                } else {
                    console.error('addPolicyRule function not found');
                    showNotification('Error: Unable to add rule. Please refresh the page.', 'error');
                }
            });
        }

        // Setup rule template buttons
        const templateBtns = document.querySelectorAll('.rule-template-btn');
        templateBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const metric = this.getAttribute('data-metric');
                const operator = this.getAttribute('data-operator');
                const threshold = parseInt(this.getAttribute('data-threshold'));
                const period = this.getAttribute('data-period');

                addRuleFromTemplate(metric, operator, threshold, period);

                // Visual feedback
                this.classList.add('active');
                setTimeout(() => {
                    this.classList.remove('active');
                }, 300);
            });
        });

        // Setup form field validation
        const policyNameInput = document.getElementById('policy-name');
        if (policyNameInput) {
            policyNameInput.addEventListener('input', validatePolicyForm);
        }

        // Setup enforcement mode radio buttons
        const enforcementRadios = document.querySelectorAll('input[name="enforcement-mode"]');
        enforcementRadios.forEach(radio => {
            radio.addEventListener('change', validatePolicyForm);
        });
    }


    function addRuleFromTemplate(metric, operator, threshold, period) {
        const rule = {
            id: Date.now().toString(),
            metric_key: metric,
            operator: operator,
            threshold: threshold,
            period: period,
            action: 'block'
        };

        state.policyRules.push(rule);
        renderPolicyRules();
        validatePolicyForm();

        showNotification('Rule template added', 'success');
    }

    function validatePolicyForm() {
        const policyName = document.getElementById('policy-name').value.trim();
        const validRules = state.policyRules.filter(rule =>
            rule.metric_key &&
            rule.threshold !== undefined &&
            rule.threshold !== '' &&
            !isNaN(rule.threshold)
        );

        const submitBtn = document.getElementById('policy-submit-btn');
        const validationMsg = document.getElementById('policy-validation-message');
        const rulesCountBadge = document.getElementById('rules-count-badge');

        // Update rules count badge
        if (rulesCountBadge) {
            if (validRules.length > 0) {
                rulesCountBadge.textContent = validRules.length;
                rulesCountBadge.classList.remove('hidden');
            } else {
                rulesCountBadge.classList.add('hidden');
            }
        }

        // Validate form
        let isValid = true;
        let message = '';

        if (!policyName) {
            isValid = false;
            message = 'Policy name is required';
        } else if (validRules.length === 0) {
            isValid = false;
            message = 'At least one valid rule is required';
        } else if (state.policyRules.length > validRules.length) {
            message = `${state.policyRules.length - validRules.length} incomplete rule(s) will not be saved`;
        }

        // Update UI
        if (submitBtn) {
            submitBtn.disabled = !isValid;
        }

        if (validationMsg) {
            validationMsg.textContent = message;
            validationMsg.className = isValid ? 'text-sm theme-text-success' : 'text-sm theme-text-danger';
        }

        return isValid;
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

            // Reset to General tab
            window.switchPolicyTab('general');

            // Show modal first
            if (window.policyModal) {
                window.policyModal.show();
            }

            // Set form values after modal is shown
            setTimeout(() => {
                document.getElementById('policy-id').value = actualPolicyId || '';
                document.getElementById('policy-name').value = policy.name || '';
                document.getElementById('policy-description').value = policy.description || '';

                // Set enforcement mode radio button
                const enforcementMode = policy.settings?.enforcement_mode || 'block';
                const radioButton = document.querySelector(`input[name="enforcement-mode"][value="${enforcementMode}"]`);
                if (radioButton) {
                    radioButton.checked = true;
                }

                // Load rules - convert from API format if needed
                if (policy.rules && Array.isArray(policy.rules)) {
                    state.policyRules = policy.rules.map((rule, index) => ({
                        id: rule.rule_id || `${Date.now()}_${index}`,
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

                // Setup modal handlers and validate
                setupPolicyModalHandlers();
                validatePolicyForm();
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
        const title = document.getElementById('policy-stats-modal-title');
        const policy = state.policies.find(p => (p.policy_id || p.id) === policyId);

        if (title && policy) {
            title.textContent = `Policy Statistics: ${policy.name}`;
        }

        const content = document.getElementById('policy-stats-content');

        // Show modal first
        if (window.policyStatsModal) {
            window.policyStatsModal.show();
        }

        if (content) {
            // Show loading state
            content.innerHTML = `
                <div class="stats-loading text-center py-8">
                    <div class="uk-spinner uk-spinner-medium theme-text-muted mx-auto mb-4"></div>
                    <p class="theme-text-secondary">Loading statistics...</p>
                </div>
            `;

            // Simulate loading and show enhanced statistics
            setTimeout(() => {
                if (!policy) {
                    content.innerHTML = `
                        <div class="text-center py-8">
                            <i data-lucide="alert-circle" class="h-12 w-12 theme-text-danger mx-auto mb-4"></i>
                            <p class="theme-text-secondary">Policy not found</p>
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();
                    return;
                }

                // Generate mock data for demonstration (in production, this would come from API)
                const mockApiUsage = (policy.api_configs || []).map((apiId, index) => ({
                    name: `API ${index + 1}`,
                    requests: Math.floor(Math.random() * 1000) + 100,
                    percentage: Math.floor(Math.random() * 60) + 20
                }));

                const mockRuleStats = (policy.rules || []).map(rule => ({
                    ...rule,
                    violations: Math.floor(Math.random() * 50)
                }));

                content.innerHTML = `
                    <div class="space-y-6">
                        <!-- Overview Cards -->
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="stats-card">
                                <div class="stats-card-header">
                                    <i data-lucide="shield-check" class="stats-card-icon"></i>
                                    <p class="text-sm font-medium theme-text-secondary">Status</p>
                                </div>
                                <p class="stats-card-value">${policy.is_active !== false ? 'Active' : 'Inactive'}</p>
                            </div>
                            <div class="stats-card">
                                <div class="stats-card-header">
                                    <i data-lucide="alert-triangle" class="stats-card-icon"></i>
                                    <p class="text-sm font-medium theme-text-secondary">Violations</p>
                                </div>
                                <p class="stats-card-value">${policy.violations_count || 0}</p>
                            </div>
                            <div class="stats-card">
                                <div class="stats-card-header">
                                    <i data-lucide="shield-off" class="stats-card-icon"></i>
                                    <p class="text-sm font-medium theme-text-secondary">Blocked</p>
                                </div>
                                <p class="stats-card-value">${policy.blocked_requests || 0}</p>
                            </div>
                            <div class="stats-card">
                                <div class="stats-card-header">
                                    <i data-lucide="activity" class="stats-card-icon"></i>
                                    <p class="text-sm font-medium theme-text-secondary">Total Requests</p>
                                </div>
                                <p class="stats-card-value">${policy.total_requests || 0}</p>
                            </div>
                        </div>

                        <!-- Rule Performance -->
                        ${mockRuleStats.length > 0 ? `
                            <div class="theme-bg-surface rounded-lg p-6 theme-border border">
                                <h3 class="text-lg font-semibold theme-text-primary mb-4 flex items-center gap-2">
                                    <i data-lucide="shield-check" class="h-5 w-5"></i>
                                    Rule Performance
                                </h3>
                                <div class="space-y-4">
                                    ${mockRuleStats.map(rule => {
                                        const metricNames = {
                                            'requests_count': 'Request Count',
                                            'total_words_count': 'Total Words',
                                            'input_words_count': 'Input Words',
                                            'output_words_count': 'Output Words',
                                            'credits_used': 'Credits Used'
                                        };
                                        const periodNames = {
                                            'hourly': 'per hour',
                                            'daily': 'per day',
                                            'monthly': 'per month',
                                            'total': 'lifetime'
                                        };
                                        return `
                                            <div class="flex items-center justify-between p-4 theme-bg-background rounded-lg">
                                                <div class="flex-1">
                                                    <p class="font-medium theme-text-primary">
                                                        ${metricNames[rule.metric_key] || rule.metric_key}
                                                    </p>
                                                    <p class="text-sm theme-text-secondary">
                                                        Limit: ${rule.threshold.toLocaleString()} ${periodNames[rule.period] || rule.period}
                                                    </p>
                                                </div>
                                                <div class="text-right">
                                                    <p class="text-2xl font-bold ${rule.violations > 0 ? 'theme-text-danger' : 'theme-text-success'}">
                                                        ${rule.violations}
                                                    </p>
                                                    <p class="text-xs theme-text-secondary">violations</p>
                                                </div>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        ` : ''}

                        <!-- API Usage Distribution -->
                        ${mockApiUsage.length > 0 ? `
                            <div class="theme-bg-surface rounded-lg p-6 theme-border border">
                                <h3 class="text-lg font-semibold theme-text-primary mb-4 flex items-center gap-2">
                                    <i data-lucide="bar-chart-2" class="h-5 w-5"></i>
                                    API Usage Distribution
                                </h3>
                                <div class="space-y-3">
                                    ${mockApiUsage.map(api => `
                                        <div class="flex items-center gap-3">
                                            <span class="text-sm theme-text-primary w-32 truncate">${api.name}</span>
                                            <div class="flex-1 relative rounded-full h-6 theme-bg-background">
                                                <div class="h-full rounded-full theme-bg-primary"
                                                     style="width: ${api.percentage}%"></div>
                                                <span class="absolute right-2 top-0 text-xs font-medium theme-text-primary leading-6">
                                                    ${api.requests.toLocaleString()} requests
                                                </span>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}

                        <!-- Time-based Statistics -->
                        <div class="theme-bg-surface rounded-lg p-6 theme-border border">
                            <h3 class="text-lg font-semibold theme-text-primary mb-4 flex items-center gap-2">
                                <i data-lucide="clock" class="h-5 w-5"></i>
                                Timeline
                            </h3>
                            <div class="space-y-3">
                                <div class="flex justify-between items-center p-3 theme-bg-background rounded">
                                    <span class="text-sm theme-text-secondary">Created</span>
                                    <span class="text-sm font-medium theme-text-primary">
                                        ${new Date(policy.created_at).toLocaleString()}
                                    </span>
                                </div>
                                ${policy.updated_at ? `
                                    <div class="flex justify-between items-center p-3 theme-bg-background rounded">
                                        <span class="text-sm theme-text-secondary">Last Updated</span>
                                        <span class="text-sm font-medium theme-text-primary">
                                            ${new Date(policy.updated_at).toLocaleString()}
                                        </span>
                                    </div>
                                ` : ''}
                                ${policy.last_evaluated ? `
                                    <div class="flex justify-between items-center p-3 theme-bg-background rounded">
                                        <span class="text-sm theme-text-secondary">Last Evaluated</span>
                                        <span class="text-sm font-medium theme-text-primary">
                                            ${timeAgo(policy.last_evaluated)}
                                        </span>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;

                if (window.lucide) lucide.createIcons();
            }, 800);
        }
    }

    // Policy Rules Management
    function addPolicyRule() {
        console.log('Adding new policy rule');
        const rule = {
            id: Date.now().toString(),
            metric_key: '', // Start empty to force user to select
            operator: 'less_than',
            threshold: '', // Start empty to force user to enter
            period: 'daily',
            action: 'block'
        };

        state.policyRules.push(rule);
        console.log('Current rules:', state.policyRules);

        // Switch to rules tab to show the new rule
        window.switchPolicyTab('rules');

        renderPolicyRules();

        // Focus on the first empty field of the new rule
        setTimeout(() => {
            const newRuleElement = document.querySelector(`[data-rule-id="${rule.id}"]`);
            if (newRuleElement) {
                const firstEmptyField = newRuleElement.querySelector('select[data-field="metric_key"], input[data-field="threshold"]');
                if (firstEmptyField) {
                    firstEmptyField.focus();
                }
            }
        }, 100);
    }

    function removeRule(ruleId) {
        state.policyRules = state.policyRules.filter(rule => rule.id !== ruleId);
        renderPolicyRules();
    }

    function renderPolicyRules() {
        const container = document.getElementById('policy-rules-container');
        const emptyState = document.getElementById('rules-empty-state');
        if (!container) return;

        // Show/hide empty state
        if (emptyState) {
            emptyState.style.display = state.policyRules.length === 0 ? 'block' : 'none';
        }

        if (state.policyRules.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = state.policyRules.map((rule, index) => {
            const isValid = rule.metric_key &&
                          rule.threshold !== undefined &&
                          rule.threshold !== '' &&
                          !isNaN(rule.threshold);

            // Get friendly names for display
            const metricNames = {
                'requests_count': 'Request Count',
                'total_words_count': 'Total Words',
                'input_words_count': 'Input Words',
                'output_words_count': 'Output Words',
                'credits_used': 'Credits Used'
            };

            const periodNames = {
                'hourly': 'per hour',
                'daily': 'per day',
                'monthly': 'per month',
                'total': 'lifetime total'
            };

            const operatorSymbols = {
                'less_than': '<',
                'less_than_or_equal': '≤',
                'greater_than': '>',
                'greater_than_or_equal': '≥',
                'equal': '=',
                'not_equal': '≠'
            };

            return `
            <div class="policy-rule-card ${!isValid ? 'invalid' : ''}" data-rule-id="${rule.id}">
                <button type="button" class="absolute top-3 right-3 text-red-500 hover:text-red-700 transition-colors" data-rule-id="${rule.id}" onclick="removeRule('${rule.id}')">
                    <i data-lucide="trash-2" class="h-4 w-4"></i>
                </button>

                ${!isValid ? `
                    <div class="flex items-center gap-2 mb-3 text-red-600">
                        <i data-lucide="alert-circle" class="h-4 w-4"></i>
                        <span class="text-sm font-medium">Incomplete rule - will not be saved</span>
                    </div>
                ` : ''}

                <!-- Rule Summary -->
                ${isValid ? `
                    <div class="mb-4 p-3 theme-bg-background rounded-lg">
                        <p class="text-sm theme-text-primary">
                            <span class="font-medium">${metricNames[rule.metric_key] || rule.metric_key}</span>
                            <span class="mx-2 font-mono">${operatorSymbols[rule.operator] || rule.operator}</span>
                            <span class="font-medium">${rule.threshold.toLocaleString()}</span>
                            <span class="ml-2 theme-text-secondary">${periodNames[rule.period] || rule.period}</span>
                        </p>
                    </div>
                ` : ''}

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-medium theme-text-secondary mb-1.5 uppercase tracking-wider">
                            Metric <span class="text-red-500">*</span>
                        </label>
                        <select class="w-full px-3 py-2 border ${!rule.metric_key ? 'border-red-500' : 'theme-border'} theme-bg-surface rounded-lg focus:ring-2 focus:ring-blue-500 transition-all text-sm"
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
                        <label class="block text-xs font-medium theme-text-secondary mb-1.5 uppercase tracking-wider">
                            Condition
                        </label>
                        <select class="w-full px-3 py-2 border theme-border theme-bg-surface rounded-lg focus:ring-2 focus:ring-blue-500 transition-all text-sm"
                                data-rule-id="${rule.id}" data-field="operator">
                            <option value="less_than" ${rule.operator === 'less_than' ? 'selected' : ''}>Less Than (<)</option>
                            <option value="less_than_or_equal" ${rule.operator === 'less_than_or_equal' ? 'selected' : ''}>Less Than or Equal (≤)</option>
                            <option value="greater_than" ${rule.operator === 'greater_than' ? 'selected' : ''}>Greater Than (>)</option>
                            <option value="greater_than_or_equal" ${rule.operator === 'greater_than_or_equal' ? 'selected' : ''}>Greater Than or Equal (≥)</option>
                            <option value="equal" ${rule.operator === 'equal' ? 'selected' : ''}>Equal To (=)</option>
                            <option value="not_equal" ${rule.operator === 'not_equal' ? 'selected' : ''}>Not Equal To (≠)</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-medium theme-text-secondary mb-1.5 uppercase tracking-wider">
                            Limit Value <span class="text-red-500">*</span>
                        </label>
                        <input type="number"
                               class="w-full px-3 py-2 border ${rule.threshold === undefined || rule.threshold === '' ? 'border-red-500' : 'theme-border'} theme-bg-surface rounded-lg focus:ring-2 focus:ring-blue-500 transition-all text-sm"
                               value="${rule.threshold}"
                               data-rule-id="${rule.id}" data-field="threshold"
                               placeholder="e.g., 1000"
                               min="0"
                               required>
                    </div>

                    <div>
                        <label class="block text-xs font-medium theme-text-secondary mb-1.5 uppercase tracking-wider">
                            Time Period
                        </label>
                        <select class="w-full px-3 py-2 border theme-border theme-bg-surface rounded-lg focus:ring-2 focus:ring-blue-500 transition-all text-sm"
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

        // Validate form after rendering
        validatePolicyForm();
    }

    function setupRuleEventHandlers() {
        const container = document.getElementById('policy-rules-container');
        if (!container) return;

        // Remove button handlers are handled inline in the HTML

        // Select handlers
        container.querySelectorAll('select[data-rule-id]').forEach(select => {
            select.addEventListener('change', function() {
                const ruleId = this.getAttribute('data-rule-id');
                const field = this.getAttribute('data-field');
                updateRule(ruleId, field, this.value);
                if (field === 'metric_key') {
                    renderPolicyRules(); // Re-render for validation
                } else {
                    validatePolicyForm(); // Just validate without re-rendering
                }
            });
        });

        // Input handlers with real-time validation
        container.querySelectorAll('input[data-rule-id]').forEach(input => {
            // Add both input and change handlers for better UX
            const handleInput = function() {
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
                validatePolicyForm(); // Validate without re-rendering for smoother UX
            };

            input.addEventListener('input', handleInput);
            input.addEventListener('change', function() {
                handleInput.call(this);
                renderPolicyRules(); // Re-render on change for validation feedback
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
            // Get enforcement mode from radio buttons
            const enforcementMode = document.querySelector('input[name="enforcement-mode"]:checked')?.value || 'block';

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

// Global error handler outside the IIFE to catch any runtime errors
window.addEventListener('error', function(event) {
    console.log('Global error caught:', event.message);

    // Check if it's our specific error
    if (event.message && event.message.includes('is not a function') && event.message.includes('Tab')) {
        console.error('Tab switching error detected. Attempting recovery...');

        // Log all available switch-related functions
        const switchFunctions = Object.keys(window).filter(k => k.toLowerCase().includes('switch'));
        console.log('Available switch functions on window:', switchFunctions);

        // If the error happened on a click event, try to handle it manually
        if (event.error && event.error.stack && event.error.stack.includes('onclick')) {
            event.preventDefault();
            console.log('Prevented default error handling');
        }
    }
}, true);
