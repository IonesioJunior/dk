/**
 * Documents Interface JavaScript
 * Handles the three-pane document management interface (Insights, Documents, Trackers)
 */

// Prevent multiple script executions
if (window.documentsScriptLoaded) {
    console.log('Documents script already loaded, skipping re-execution...');
} else {
    window.documentsScriptLoaded = true;

class DocumentsManager {
    constructor() {
        this.currentTab = 'insights';
        this.documents = [];
        this.trackers = [];
        this.insights = {
            totalDocs: 0,
            avgLength: 0,
            totalSize: 0,
            commonType: 'TXT',
            documentTypes: {}
        };

        this.init();
    }

    init() {
        this.setupSidebarNavigation();
        this.setupDocumentSearch();
        this.setupUploadFunctionality();
        this.setupEventListeners();
        this.setupPreviewPanel();
        this.loadInsights();
        this.loadDocuments();
        this.loadTrackers();

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    setupSidebarNavigation() {
        const navItems = ['insights', 'documents', 'trackers'];

        navItems.forEach(item => {
            const navButton = document.getElementById(`${item}-tab`);
            if (navButton) {
                navButton.addEventListener('click', () => this.switchTab(item));
            }
        });
    }

    switchTab(tabName) {
        console.log('Switching to tab:', tabName);

        // Update active sidebar nav item
        document.querySelectorAll('.sidebar-nav-item').forEach(btn => {
            btn.classList.remove('active');
        });

        const activeNavItem = document.getElementById(`${tabName}-tab`);
        if (activeNavItem) {
            activeNavItem.classList.add('active');
            console.log('Sidebar nav item activated:', tabName);
        } else {
            console.error('Sidebar nav item not found:', `${tabName}-tab`);
        }

        // Show/hide tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });

        const activeSection = document.getElementById(`${tabName}-section`);
        if (activeSection) {
            activeSection.classList.remove('hidden');
            console.log('Tab content shown:', tabName);
        } else {
            console.error('Tab section not found:', `${tabName}-section`);
        }

        this.currentTab = tabName;
    }

    setupDocumentSearch() {
        const searchInput = document.getElementById('document-search');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                // Debounce search to avoid too many API calls
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchDocuments(e.target.value);
                }, 300);
            });
        }
    }

    async loadInsights() {
        try {
            // Check if insights data is already rendered server-side
            const totalDocsElement = document.getElementById('total-docs');
            const avgLengthElement = document.getElementById('avg-length');
            const totalSizeElement = document.getElementById('total-size');
            const commonTypeElement = document.getElementById('common-type');

            // If server-rendered data exists, use it
            if (totalDocsElement && totalDocsElement.textContent && totalDocsElement.textContent !== '0') {
                console.log('Using server-rendered insights data');
                return; // Don't override server data
            }

            // Fallback to API call if no server data
            const response = await fetch('/api/documents-collection/insights');
            if (response.ok) {
                const insights = await response.json();
                this.updateInsightsDisplay({
                    totalDocs: insights.total_documents,
                    avgLength: insights.avg_words,
                    totalSize: insights.size_display,
                    commonType: insights.top_extensions[0]?.[0]?.toUpperCase() || 'N/A',
                    documentTypes: insights.extension_counts
                });
            } else {
                console.error('Failed to load insights from API');
            }
        } catch (error) {
            console.error('Error loading insights:', error);
        }
    }

    updateInsightsDisplay(insights) {
        document.getElementById('total-docs').textContent = insights.totalDocs.toLocaleString();
        document.getElementById('avg-length').textContent = `${insights.avgLength.toLocaleString()} words`;
        document.getElementById('total-size').textContent = `${insights.totalSize} MB`;
        document.getElementById('common-type').textContent = insights.commonType;

        this.renderDocumentTypes(insights.documentTypes);
    }

    // Utility methods for UI state management
    showLoadingState() {
        document.getElementById('documents-loading')?.classList.remove('hidden');
        document.getElementById('documents-list')?.classList.add('hidden');
        document.getElementById('documents-empty')?.classList.add('hidden');
        document.getElementById('documents-error')?.classList.add('hidden');
    }

    hideLoadingState() {
        document.getElementById('documents-loading')?.classList.add('hidden');
        document.getElementById('documents-list')?.classList.remove('hidden');
    }

    showErrorState(message) {
        document.getElementById('documents-error')?.classList.remove('hidden');
        document.getElementById('documents-list')?.classList.add('hidden');
        document.getElementById('documents-empty')?.classList.add('hidden');
        document.getElementById('error-message').textContent = message;
    }

    hideErrorState() {
        document.getElementById('documents-error')?.classList.add('hidden');
    }

    // Utility methods for formatting
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return Math.floor(diffInSeconds / 60) + ' minutes ago';
        if (diffInSeconds < 86400) return Math.floor(diffInSeconds / 3600) + ' hours ago';
        if (diffInSeconds < 2592000) return Math.floor(diffInSeconds / 86400) + ' days ago';
        return Math.floor(diffInSeconds / 2592000) + ' months ago';
    }

    // Event listeners setup
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-documents-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDocuments();
            });
        }

        // Retry button
        const retryBtn = document.getElementById('retry-documents-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.hideErrorState();
                this.loadDocuments();
            });
        }
    }

    // Upload functionality
    setupUploadFunctionality() {
        // Check if UploadComponent is available
        if (typeof UploadComponent === 'undefined') {
            console.warn('UploadComponent not yet available, will retry...');
            // Retry after a short delay
            setTimeout(() => {
                this.setupUploadFunctionality();
            }, 100);
            return;
        }

        // Setup the modular upload component
        const uploadContainer = document.querySelector('.upload-component');
        if (uploadContainer) {
            // Check if already initialized by auto-initialization
            if (uploadContainer.uploadComponent) {
                // Component already initialized, just add our callbacks
                this.uploadComponent = uploadContainer.uploadComponent;

                // Override the callbacks to include our document-specific functionality
                this.uploadComponent.options.onUploadComplete = (files) => {
                    // Refresh documents list and insights after successful upload
                    this.loadDocuments();
                    this.loadInsights();
                    // Note: Success notification is already shown by upload_component.js
                };

                this.uploadComponent.options.onUploadError = (error) => {
                    console.error('Upload error:', error);
                    this.showNotification('Failed to upload documents. Please try again.', 'error');
                };

                this.uploadComponent.options.onUploadProgress = (percentage, completed, total) => {
                    console.log(`Upload progress: ${percentage}% (${completed}/${total} files)`);
                };

                console.log('Using existing upload component instance');
            } else {
                // Initialize the upload component with callbacks
                this.uploadComponent = new UploadComponent(uploadContainer, {
                    apiEndpoint: '/api/documents-collection/bulk',
                    onUploadComplete: (files) => {
                        // Refresh documents list and insights after successful upload
                        this.loadDocuments();
                        this.loadInsights();
                        // Note: Success notification is already shown by upload_component.js
                    },
                    onUploadError: (error) => {
                        console.error('Upload error:', error);
                        this.showNotification('Failed to upload documents. Please try again.', 'error');
                    },
                    onUploadProgress: (percentage, completed, total) => {
                        console.log(`Upload progress: ${percentage}% (${completed}/${total} files)`);
                    }
                });

                console.log('Created new upload component instance');
            }
        } else {
            console.warn('Upload component container not found. Make sure the upload component is included in the HTML.');
        }
    }


    // Notification system
    showNotification(message, type = 'info') {
        // Use Toaster if available
        if (typeof window.Toaster !== 'undefined') {
            switch(type) {
                case 'success':
                    window.Toaster.success(message);
                    break;
                case 'warning':
                    window.Toaster.warning(message);
                    break;
                case 'danger':
                case 'error':
                    window.Toaster.error(message);
                    break;
                default:
                    window.Toaster.info(message);
            }
        } else if (typeof UIkit !== 'undefined') {
            // Fallback to UIkit notification
            UIkit.notification(message, { status: type, pos: 'bottom-right' });
        }
    }

    renderDocumentTypes(types) {
        const container = document.getElementById('document-types');
        if (!container) return;

        // Check if server-rendered content already exists
        if (container.children.length > 0) {
            console.log('Using server-rendered document types');
            return; // Don't override server-rendered content
        }

        const colors = {
            'TXT': { bg: 'rgba(var(--color-primary-rgb, 30, 136, 229), 0.1)', text: 'var(--color-primary)' },
            'MD': { bg: 'rgba(var(--color-success-rgb, 40, 167, 69), 0.1)', text: 'var(--color-success)' },
            'JSON': { bg: 'rgba(var(--color-info-rgb, 23, 162, 184), 0.1)', text: 'var(--color-info)' },
            'PDF': { bg: 'rgba(var(--color-danger-rgb, 220, 53, 69), 0.1)', text: 'var(--color-danger)' }
        };

        container.innerHTML = '';

        Object.entries(types).forEach(([type, count]) => {
            const colorScheme = colors[type] || { bg: 'rgba(var(--color-text-muted-rgb, 173, 181, 189), 0.1)', text: 'var(--color-text-muted)' };
            const typeCard = document.createElement('div');
            typeCard.className = 'text-center p-4 rounded-lg theme-bg-surface theme-border border';
            typeCard.innerHTML = `
                <div class="w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-2" style="background-color: ${colorScheme.bg};">
                    <span class="font-bold text-sm" style="color: ${colorScheme.text};">${type}</span>
                </div>
                <p class="text-lg font-bold theme-text-primary">${count}</p>
                <p class="text-xs theme-text-secondary">documents</p>
            `;
            container.appendChild(typeCard);
        });
    }

    async loadDocuments() {
        this.showLoadingState();

        try {
            const response = await fetch('/api/documents-collection/list', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    include_embeddings: false,
                    limit: 100
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Transform API data to our format
            const documents = data.documents.map(doc => {
                const metadata = doc.metadata || {};
                const extension = metadata.extension || 'unknown';
                const size = this.formatFileSize(metadata.size || 0);
                const createdAt = metadata.created_at ? new Date(metadata.created_at) : new Date();
                const modified = this.formatTimeAgo(createdAt);

                return {
                    id: doc.id,
                    name: metadata.file_name || 'Untitled Document',
                    type: extension.toUpperCase(),
                    size: size,
                    modified: modified,
                    content: doc.content,
                    metadata: metadata
                };
            });

            this.documents = documents;
            this.hideLoadingState();
            this.renderDocuments(documents);

        } catch (error) {
            console.error('Error loading documents:', error);
            this.hideLoadingState();
            this.showErrorState('Failed to load documents. Please try again.');
        }
    }

    renderDocuments(documents) {
        const container = document.getElementById('documents-list');
        const emptyState = document.getElementById('documents-empty');

        if (!container) return;

        if (documents.length === 0) {
            container.innerHTML = '';
            emptyState?.classList.remove('hidden');
            return;
        }

        emptyState?.classList.add('hidden');

        const typeIcons = {
            'TXT': 'file-text',
            'MD': 'file-code',
            'JSON': 'braces',
            'PDF': 'file-type'
        };

        const typeColors = {
            'TXT': { bg: 'rgba(var(--color-primary-rgb, 30, 136, 229), 0.1)', text: 'var(--color-primary)' },
            'MD': { bg: 'rgba(var(--color-success-rgb, 40, 167, 69), 0.1)', text: 'var(--color-success)' },
            'JSON': { bg: 'rgba(var(--color-info-rgb, 23, 162, 184), 0.1)', text: 'var(--color-info)' },
            'PDF': { bg: 'rgba(var(--color-danger-rgb, 220, 53, 69), 0.1)', text: 'var(--color-danger)' }
        };

        container.innerHTML = documents.map(doc => {
            const colorScheme = typeColors[doc.type] || { bg: 'rgba(var(--color-text-muted-rgb, 173, 181, 189), 0.1)', text: 'var(--color-text-muted)' };
            return `
                <div class="theme-bg-surface rounded-xl p-6 shadow-sm theme-border border hover:shadow-md transition-shadow">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center flex-1">
                            <div class="w-12 h-12 rounded-lg flex items-center justify-center mr-4" style="background-color: ${colorScheme.bg};">
                                <i data-lucide="${typeIcons[doc.type] || 'file'}" class="h-6 w-6" style="color: ${colorScheme.text};"></i>
                            </div>
                            <div class="flex-1">
                                <h3 class="text-lg font-semibold theme-text-primary">${doc.name}</h3>
                                <p class="text-sm theme-text-secondary">${doc.type} • ${doc.size} • Modified ${doc.modified}</p>
                            </div>
                        </div>
                        <div class="flex items-center space-x-1 ml-4">
                            <button onclick="documentsManager.previewDocument('${doc.id}')" class="p-2 rounded-lg transition-colors duration-200 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" title="Preview">
                                <i data-lucide="eye" class="h-4 w-4"></i>
                            </button>
                            <button onclick="documentsManager.editDocument('${doc.id}')" class="p-2 rounded-lg transition-colors duration-200 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" title="Edit">
                                <i data-lucide="edit-3" class="h-4 w-4"></i>
                            </button>
                            <button onclick="documentsManager.deleteDocument('${doc.id}')" class="p-2 rounded-lg transition-colors duration-200 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-400 hover:text-red-600 dark:hover:text-red-400" title="Delete">
                                <i data-lucide="trash-2" class="h-4 w-4"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Re-initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    async searchDocuments(query) {
        if (!query.trim()) {
            this.renderDocuments(this.documents);
            return;
        }

        try {
            // First try client-side search for instant results
            const clientFiltered = this.documents.filter(doc =>
                doc.name.toLowerCase().includes(query.toLowerCase()) ||
                doc.type.toLowerCase().includes(query.toLowerCase()) ||
                doc.content.toLowerCase().includes(query.toLowerCase())
            );

            // Show client-side results immediately
            this.renderDocuments(clientFiltered);

            // Then perform server-side semantic search for better results
            const response = await fetch('/api/documents-collection/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    limit: 50,
                    include_embeddings: false
                })
            });

            if (response.ok) {
                const data = await response.json();

                // Transform API data to our format
                const searchResults = data.documents.map(doc => {
                    const metadata = doc.metadata || {};
                    const extension = metadata.extension || 'unknown';
                    const size = this.formatFileSize(metadata.size || 0);
                    const createdAt = metadata.created_at ? new Date(metadata.created_at) : new Date();
                    const modified = this.formatTimeAgo(createdAt);

                    return {
                        id: doc.id,
                        name: metadata.file_name || 'Untitled Document',
                        type: extension.toUpperCase(),
                        size: size,
                        modified: modified,
                        content: doc.content,
                        metadata: metadata,
                        relevance: doc.distance // Lower distance = higher relevance
                    };
                });

                // Sort by relevance (lower distance = better match)
                searchResults.sort((a, b) => a.relevance - b.relevance);

                // Update with semantic search results
                this.renderDocuments(searchResults);
            }
        } catch (error) {
            console.error('Search error:', error);
            // Fall back to client-side search if server search fails
            const filteredDocs = this.documents.filter(doc =>
                doc.name.toLowerCase().includes(query.toLowerCase()) ||
                doc.type.toLowerCase().includes(query.toLowerCase())
            );
            this.renderDocuments(filteredDocs);
        }
    }

    async loadTrackers() {
        try {
            // Mock data - replace with actual API call
            const trackers = [
                {
                    id: 1,
                    name: 'System Monitor',
                    description: 'Monitors system performance and resource usage',
                    version: '2.1.0',
                    enabled: true,
                    status: 'active'
                },
                {
                    id: 2,
                    name: 'File Watcher',
                    description: 'Tracks file system changes and modifications',
                    version: '1.5.3',
                    enabled: false,
                    status: 'inactive'
                },
                {
                    id: 3,
                    name: 'Network Tracker',
                    description: 'Monitors network activity and connections',
                    version: '3.0.1',
                    enabled: true,
                    status: 'active'
                }
            ];

            this.trackers = trackers;
            this.renderTrackers(trackers);
        } catch (error) {
            console.error('Error loading trackers:', error);
        }
    }

    renderTrackers(trackers) {
        const container = document.getElementById('trackers-grid');
        const emptyState = document.getElementById('trackers-empty');

        if (!container) return;

        if (trackers.length === 0) {
            container.innerHTML = '';
            emptyState?.classList.remove('hidden');
            return;
        }

        emptyState?.classList.add('hidden');

        container.innerHTML = trackers.map(tracker => `
            <div class="theme-bg-surface rounded-xl p-6 shadow-sm theme-border border">
                <div class="flex items-start justify-between mb-4">
                    <div class="flex items-center">
                        <div class="w-10 h-10 rounded-lg flex items-center justify-center mr-3" style="background-color: rgba(var(--color-primary-rgb, 30, 136, 229), 0.1);">
                            <i data-lucide="activity" class="h-5 w-5 theme-primary"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold theme-text-primary">${tracker.name}</h3>
                            <p class="text-sm theme-text-secondary">v${tracker.version}</p>
                        </div>
                    </div>
                    <button class="uk-button uk-button-default uk-button-small" onclick="documentsManager.showTrackerOptions(${tracker.id})">
                        <i data-lucide="more-horizontal" class="h-4 w-4"></i>
                    </button>
                </div>

                <p class="theme-text-secondary text-sm mb-4">${tracker.description}</p>

                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <span class="text-sm font-medium theme-text-primary mr-3">Status:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${tracker.enabled ? 'theme-bg-success' : 'theme-border'}" style="background-color: ${tracker.enabled ? 'rgba(var(--color-success-rgb, 40, 167, 69), 0.1)' : 'rgba(var(--color-text-muted-rgb, 173, 181, 189), 0.1)'}; color: ${tracker.enabled ? 'var(--color-success)' : 'var(--color-text-muted)'};">
                            ${tracker.status}
                        </span>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" ${tracker.enabled ? 'checked' : ''} class="sr-only peer" onchange="documentsManager.toggleTracker(${tracker.id})">
                        <div class="w-11 h-6 rounded-full peer transition-colors duration-200" style="background-color: ${tracker.enabled ? 'var(--color-primary)' : 'var(--color-border)'};">
                            <div class="w-5 h-5 bg-white rounded-full shadow-lg transform transition-transform duration-200 ${tracker.enabled ? 'translate-x-5' : 'translate-x-0.5'}" style="margin-top: 2px;"></div>
                        </div>
                    </label>
                </div>
            </div>
        `).join('');

        // Re-initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    editDocument(docId) {
        const doc = this.documents.find(d => d.id === docId);
        if (doc) {
            // For now, show document content in a modal for editing
            this.openEditModal(doc);
        }
    }

    openEditModal(doc) {
        // Create edit modal if it doesn't exist
        let editModal = document.getElementById('edit-modal');
        if (!editModal) {
            editModal = this.createEditModal();
            document.body.appendChild(editModal);
        }

        // Populate modal with document data
        document.getElementById('edit-doc-name').value = doc.name;
        document.getElementById('edit-doc-content').value = doc.content;
        document.getElementById('edit-modal').dataset.docId = doc.id;

        // Show modal
        UIkit.modal(editModal).show();
    }

    createEditModal() {
        const modal = document.createElement('div');
        modal.id = 'edit-modal';
        modal.className = 'uk-modal';
        modal.innerHTML = `
            <div class="uk-modal-dialog uk-modal-body theme-bg-surface rounded-lg" style="width: 80vw; max-width: 900px;">
                <button class="uk-modal-close-default" type="button" uk-close></button>
                <h2 class="uk-modal-title theme-text-primary">Edit Document</h2>

                <form id="edit-form" class="space-y-4">
                    <div class="uk-form-row">
                        <label class="uk-form-label theme-text-primary">Document Name</label>
                        <div class="uk-form-controls">
                            <input type="text" id="edit-doc-name" class="uk-input theme-bg-background theme-border border rounded-lg" required>
                        </div>
                    </div>

                    <div class="uk-form-row">
                        <label class="uk-form-label theme-text-primary">Content</label>
                        <div class="uk-form-controls">
                            <textarea id="edit-doc-content" class="uk-textarea theme-bg-background theme-border border rounded-lg" rows="15" required></textarea>
                        </div>
                    </div>

                    <div class="uk-modal-footer uk-text-right">
                        <button type="button" class="uk-button uk-button-default uk-modal-close">Cancel</button>
                        <button type="submit" class="uk-button uk-button-primary">
                            <span id="edit-btn-text">Save Changes</span>
                            <div id="edit-spinner" class="hidden uk-spinner uk-spinner-small ml-2"></div>
                        </button>
                    </div>
                </form>
            </div>
        `;

        // Add form submit handler
        const form = modal.querySelector('#edit-form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveDocumentEdit();
        });

        return modal;
    }

    async saveDocumentEdit() {
        const modal = document.getElementById('edit-modal');
        const docId = modal.dataset.docId;
        const name = document.getElementById('edit-doc-name').value.trim();
        const content = document.getElementById('edit-doc-content').value;
        const submitBtn = modal.querySelector('button[type="submit"]');
        const btnText = document.getElementById('edit-btn-text');
        const spinner = document.getElementById('edit-spinner');

        if (!name || !content) {
            this.showNotification('Please fill in all fields', 'warning');
            return;
        }

        try {
            // Show saving state
            submitBtn.disabled = true;
            btnText.textContent = 'Saving...';
            spinner?.classList.remove('hidden');

            // Update document
            const response = await fetch(`/api/documents-collection/${docId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    metadata: {
                        file_name: name
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Success - close modal and refresh documents
            UIkit.modal(modal).hide();
            this.showNotification('Document updated successfully!', 'success');
            this.loadDocuments();

        } catch (error) {
            console.error('Edit error:', error);
            this.showNotification('Failed to update document. Please try again.', 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            btnText.textContent = 'Save Changes';
            spinner?.classList.add('hidden');
        }
    }

    previewDocument(docId) {
        const doc = this.documents.find(d => d.id === docId);
        if (doc) {
            // Check screen size - use modal for smaller screens, side panel for larger
            if (window.innerWidth >= 1024) {
                this.openPreviewSidePanel(doc);
            } else {
                this.openPreviewModal(doc);
            }
        }
    }

    openPreviewModal(doc) {
        // Create preview modal if it doesn't exist
        let previewModal = document.getElementById('preview-modal');
        if (!previewModal) {
            previewModal = this.createPreviewModal();
            document.body.appendChild(previewModal);
        }

        // Populate modal with document data
        document.getElementById('preview-doc-title').textContent = doc.name;
        document.getElementById('preview-doc-info').textContent = `${doc.type} • ${doc.size} • Modified ${doc.modified}`;
        previewModal.dataset.docId = doc.id;

        const contentEl = document.getElementById('preview-doc-content');

        // Format content based on file type
        if (doc.type === 'JSON') {
            try {
                const formatted = JSON.stringify(JSON.parse(doc.content), null, 2);
                contentEl.innerHTML = `<pre class="language-json"><code>${this.escapeHtml(formatted)}</code></pre>`;
            } catch (e) {
                contentEl.innerHTML = `<pre><code>${this.escapeHtml(doc.content)}</code></pre>`;
            }
        } else if (doc.type === 'MD') {
            // For markdown, show raw content in a code block
            contentEl.innerHTML = `<pre class="language-markdown"><code>${this.escapeHtml(doc.content)}</code></pre>`;
        } else {
            contentEl.innerHTML = `<pre><code>${this.escapeHtml(doc.content)}</code></pre>`;
        }

        // Show modal
        UIkit.modal(previewModal).show();
    }

    createPreviewModal() {
        const modal = document.createElement('div');
        modal.id = 'preview-modal';
        modal.className = 'uk-modal';
        modal.innerHTML = `
            <div class="uk-modal-dialog theme-bg-surface rounded-lg shadow-2xl" style="width: 90vw; max-width: 1000px; max-height: 90vh; margin: 0; padding: 0;">
                <div class="flex flex-col h-full" style="max-height: 90vh;">
                    <!-- Preview Header -->
                    <div class="flex items-center justify-between p-4 theme-bg-surface theme-border border-b">
                        <div class="flex-1">
                            <h3 id="preview-doc-title" class="text-lg font-semibold theme-text-primary truncate"></h3>
                            <p id="preview-doc-info" class="text-sm theme-text-secondary mt-1"></p>
                        </div>
                        <div class="flex items-center space-x-2 ml-4">
                            <button id="preview-modal-edit-btn" class="p-2 rounded-lg transition-colors duration-200 hover:theme-bg-background theme-text-muted hover:theme-text-primary" title="Edit Document" onclick="documentsManager.editDocument(documentsManager.getCurrentPreviewDocId())">
                                <i data-lucide="edit-3" class="h-4 w-4"></i>
                            </button>
                            <button class="p-2 rounded-lg transition-colors duration-200 hover:theme-bg-background theme-text-muted hover:theme-text-primary uk-modal-close" title="Close Preview">
                                <i data-lucide="x" class="h-4 w-4"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Preview Content -->
                    <div class="flex-1 overflow-y-auto p-4 theme-bg-surface" style="min-height: 0;">
                        <div id="preview-doc-content" class="theme-bg-background rounded-lg p-4 h-full" style="font-family: 'Courier New', monospace; white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.5; min-height: 400px;"></div>
                    </div>
                </div>
            </div>
        `;

        // Add event listener for edit button after modal is created
        modal.addEventListener('shown', () => {
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        });

        return modal;
    }

    getCurrentPreviewDocId() {
        const modal = document.getElementById('preview-modal');
        return modal?.dataset.docId;
    }

    setupPreviewPanel() {
        // Setup close button for side panel
        const closeBtn = document.getElementById('preview-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closePreviewSidePanel());
        }

        // Setup edit button for side panel
        const editBtn = document.getElementById('preview-edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                const docId = this.getCurrentPreviewPanelDocId();
                if (docId) {
                    this.editDocument(docId);
                }
            });
        }

        // Handle window resize to switch between modal and side panel
        window.addEventListener('resize', () => {
            const panel = document.getElementById('document-preview-panel');
            if (panel && panel.classList.contains('preview-panel-open')) {
                if (window.innerWidth < 1024) {
                    // Switch to modal on smaller screens
                    const docId = this.getCurrentPreviewPanelDocId();
                    if (docId) {
                        this.closePreviewSidePanel();
                        const doc = this.documents.find(d => d.id === docId);
                        if (doc) {
                            this.openPreviewModal(doc);
                        }
                    }
                }
            }
        });
    }

    openPreviewSidePanel(doc) {
        const panel = document.getElementById('document-preview-panel');
        const mainContent = document.getElementById('main-content-area');

        if (!panel || !mainContent) return;

        // Populate panel with document data
        document.getElementById('preview-panel-title').textContent = doc.name;
        document.getElementById('preview-panel-info').textContent = `${doc.type} • ${doc.size} • Modified ${doc.modified}`;
        panel.dataset.docId = doc.id;

        const contentEl = document.getElementById('preview-panel-content');

        // Format content based on file type
        if (doc.type === 'JSON') {
            try {
                const formatted = JSON.stringify(JSON.parse(doc.content), null, 2);
                contentEl.innerHTML = `<pre class="language-json"><code>${this.escapeHtml(formatted)}</code></pre>`;
            } catch (e) {
                contentEl.innerHTML = `<pre><code>${this.escapeHtml(doc.content)}</code></pre>`;
            }
        } else if (doc.type === 'MD') {
            // For markdown, show raw content in a code block
            contentEl.innerHTML = `<pre class="language-markdown"><code>${this.escapeHtml(doc.content)}</code></pre>`;
        } else {
            contentEl.innerHTML = `<pre><code>${this.escapeHtml(doc.content)}</code></pre>`;
        }

        // Show panel and shrink main content
        panel.classList.add('preview-panel-open');
        mainContent.classList.add('content-shrunk', 'with-preview');

        // Re-initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    closePreviewSidePanel() {
        const panel = document.getElementById('document-preview-panel');
        const mainContent = document.getElementById('main-content-area');

        if (!panel || !mainContent) return;

        // Hide panel and restore main content
        panel.classList.remove('preview-panel-open');
        mainContent.classList.remove('with-preview');

        // Clear panel data
        panel.dataset.docId = '';
    }

    getCurrentPreviewPanelDocId() {
        const panel = document.getElementById('document-preview-panel');
        return panel?.dataset.docId;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async deleteDocument(docId) {
        const doc = this.documents.find(d => d.id === docId);
        const docName = doc ? doc.name : 'this document';

        if (!confirm(`Are you sure you want to delete "${docName}"? This action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/documents-collection/${docId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Remove from local cache
            this.documents = this.documents.filter(d => d.id !== docId);
            this.renderDocuments(this.documents);

            // Show success message
            this.showNotification('Document deleted successfully', 'success');

            // Reload insights to reflect changes
            this.loadInsights();

        } catch (error) {
            console.error('Error deleting document:', error);
            this.showNotification('Failed to delete document. Please try again.', 'error');
        }
    }

    toggleTracker(trackerId) {
        const tracker = this.trackers.find(t => t.id === trackerId);
        if (tracker) {
            tracker.enabled = !tracker.enabled;
            tracker.status = tracker.enabled ? 'active' : 'inactive';
            console.log(`Tracker ${tracker.name} ${tracker.enabled ? 'enabled' : 'disabled'}`);
            // Here you would typically make an API call to update the tracker status
        }
    }

    showTrackerOptions(trackerId) {
        const tracker = this.trackers.find(t => t.id === trackerId);
        if (tracker) {
            // Implement options dropdown
            const options = ['Configure', 'View Details', 'Delete'];
            console.log('Showing options for tracker:', tracker.name);
            // This could show a dropdown menu with options
        }
    }
}

// Initialize the documents manager
window.initializeDocumentsManager = function initializeDocumentsManager() {
    // Clean up existing instance if it exists
    if (window.documentsManager) {
        console.log('Cleaning up existing Documents Manager...');
        window.documentsManager = null;
    }

    console.log('Initializing Documents Manager...');

    // Check if elements exist
    const insightsNav = document.getElementById('insights-tab');
    const documentsNav = document.getElementById('documents-tab');
    const trackersNav = document.getElementById('trackers-tab');

    console.log('Sidebar nav elements found:', {
        insights: !!insightsNav,
        documents: !!documentsNav,
        trackers: !!trackersNav
    });

    if (insightsNav && documentsNav && trackersNav) {
        window.documentsManager = new DocumentsManager();
        console.log('Documents Manager initialized successfully');
    } else {
        console.error('Required sidebar nav elements not found');
        // Retry after a short delay, but only if we haven't already initialized
        if (!window.documentsManager) {
            setTimeout(window.initializeDocumentsManager, 100);
        }
    }
}

// Initialize immediately if DOM is ready, otherwise wait
// Only add event listener if we haven't already done so
if (!window.documentsManagerEventAdded) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.initializeDocumentsManager);
        window.documentsManagerEventAdded = true;
    } else {
        window.initializeDocumentsManager();
    }
}

} // End of script loading protection
