/**
 * Prompt History Interface JavaScript
 * Handles the prompt history management interface
 */

// Prevent multiple script executions
if (window.promptHistoryScriptLoaded) {
    console.log('Prompt history script already loaded, skipping re-execution...');
} else {
    window.promptHistoryScriptLoaded = true;

class PromptHistoryManager {
    constructor() {
        this.currentTab = 'overview';
        this.prompts = [];
        this.filteredPrompts = [];
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.stats = {
            totalPrompts: 0,
            totalConversations: 0,
            avgResponseLength: 0,
            todayPrompts: 0
        };

        this.init();
    }

    init() {
        this.setupSidebarNavigation();
        this.setupSearchAndFilters();
        this.setupEventListeners();
        this.setupPreviewPanel();
        this.loadPromptHistory();

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    setupSidebarNavigation() {
        const navItems = ['overview', 'history'];

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
        }

        // Show/hide tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });

        const activeSection = document.getElementById(`${tabName}-section`);
        if (activeSection) {
            activeSection.classList.remove('hidden');
        }

        this.currentTab = tabName;
    }

    setupSearchAndFilters() {
        // Search input
        const searchInput = document.getElementById('prompt-search');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchQuery = e.target.value;
                    this.applyFilters();
                }, 300);
            });
        }

        // Filter dropdown
        const filterDropdown = document.getElementById('filter-dropdown');
        if (filterDropdown) {
            filterDropdown.addEventListener('change', (e) => {
                this.currentFilter = e.target.value;
                this.applyFilters();
            });
        }
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-history-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadPromptHistory();
            });
        }

        // Retry button
        const retryBtn = document.getElementById('retry-history-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.hideErrorState();
                this.loadPromptHistory();
            });
        }

        // Export button
        const exportBtn = document.getElementById('export-history-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportHistory();
            });
        }
    }

    setupPreviewPanel() {
        // Close button
        const closeBtn = document.getElementById('preview-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closePreviewPanel());
        }

        // Copy button
        const copyBtn = document.getElementById('preview-copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyConversation());
        }
    }

    // Utility methods for UI state management
    showLoadingState() {
        document.getElementById('history-loading')?.classList.remove('hidden');
        document.getElementById('history-list')?.classList.add('hidden');
        document.getElementById('history-empty')?.classList.add('hidden');
        document.getElementById('history-error')?.classList.add('hidden');
    }

    hideLoadingState() {
        document.getElementById('history-loading')?.classList.add('hidden');
        document.getElementById('history-list')?.classList.remove('hidden');
    }

    showErrorState(message) {
        document.getElementById('history-error')?.classList.remove('hidden');
        document.getElementById('history-list')?.classList.add('hidden');
        document.getElementById('history-empty')?.classList.add('hidden');
        document.getElementById('error-message').textContent = message;
    }

    hideErrorState() {
        document.getElementById('history-error')?.classList.add('hidden');
    }

    showEmptyState() {
        document.getElementById('history-empty')?.classList.remove('hidden');
        document.getElementById('history-list')?.classList.add('hidden');
    }

    // Load prompt history from API
    async loadPromptHistory() {
        this.showLoadingState();

        try {
            const response = await fetch('/api/prompt-history');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.prompts = data.prompts || [];

            // Calculate statistics
            this.calculateStats();

            // Update UI
            this.updateOverviewStats();
            this.updateRecentActivity();
            this.applyFilters();

            this.hideLoadingState();

        } catch (error) {
            console.error('Error loading prompt history:', error);
            this.hideLoadingState();
            this.showErrorState('Failed to load prompt history. Please try again.');
        }
    }

    calculateStats() {
        const now = new Date();
        const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        // Total prompts
        this.stats.totalPrompts = this.prompts.length;

        // Total conversations (unique conversation IDs)
        const uniqueConversations = new Set(this.prompts.map(p => p.conversation_id));
        this.stats.totalConversations = uniqueConversations.size;

        // Average response length
        if (this.prompts.length > 0) {
            const totalWords = this.prompts.reduce((sum, p) => {
                return sum + (p.response ? p.response.split(/\s+/).length : 0);
            }, 0);
            this.stats.avgResponseLength = Math.round(totalWords / this.prompts.length);
        }

        // Today's prompts
        this.stats.todayPrompts = this.prompts.filter(p => {
            if (!p.timestamp) return false;
            const promptDate = new Date(p.timestamp);
            return promptDate >= startOfDay;
        }).length;
    }

    updateOverviewStats() {
        document.getElementById('total-prompts').textContent = this.stats.totalPrompts;
        document.getElementById('total-conversations').textContent = this.stats.totalConversations;
        document.getElementById('avg-response').textContent = `${this.stats.avgResponseLength} words`;
        document.getElementById('today-prompts').textContent = this.stats.todayPrompts;
    }

    updateRecentActivity() {
        const container = document.getElementById('recent-activity');
        if (!container) return;

        // Get last 5 prompts
        const recentPrompts = this.prompts.slice(0, 5);

        if (recentPrompts.length === 0) {
            container.innerHTML = '<p class="theme-text-muted text-center py-4">No recent activity</p>';
            return;
        }

        container.innerHTML = recentPrompts.map(prompt => {
            const truncatedPrompt = this.truncateText(prompt.prompt, 100);
            const timeAgo = this.formatTimeAgo(prompt.timestamp);

            return `
                <div class="flex items-start space-x-3 p-3 rounded-lg theme-bg-background hover:theme-bg-surface transition-colors cursor-pointer" onclick="promptHistoryManager.previewPrompt('${prompt.id}')">
                    <div class="flex-shrink-0 p-2 rounded-lg" style="background-color: rgba(var(--color-primary-rgb, 30, 136, 229), 0.1);">
                        <i data-lucide="message-square" class="h-4 w-4 theme-primary"></i>
                    </div>
                    <div class="flex-1">
                        <p class="theme-text-primary text-sm">${this.escapeHtml(truncatedPrompt)}</p>
                        <p class="theme-text-muted text-xs mt-1">${timeAgo}</p>
                    </div>
                </div>
            `;
        }).join('');

        // Re-initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    applyFilters() {
        // Start with all prompts
        this.filteredPrompts = [...this.prompts];

        // Apply time filter
        if (this.currentFilter !== 'all') {
            const now = new Date();
            let filterDate;

            switch (this.currentFilter) {
                case 'today':
                    filterDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                    break;
                case 'week':
                    filterDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case 'month':
                    filterDate = new Date(now.getFullYear(), now.getMonth(), 1);
                    break;
            }

            this.filteredPrompts = this.filteredPrompts.filter(prompt => {
                if (!prompt.timestamp) return false;
                return new Date(prompt.timestamp) >= filterDate;
            });
        }

        // Apply search filter
        if (this.searchQuery.trim()) {
            const query = this.searchQuery.toLowerCase();
            this.filteredPrompts = this.filteredPrompts.filter(prompt =>
                prompt.prompt.toLowerCase().includes(query) ||
                prompt.response.toLowerCase().includes(query)
            );
        }

        // Render filtered results
        this.renderPromptHistory();
    }

    renderPromptHistory() {
        const container = document.getElementById('history-list');
        if (!container) return;

        if (this.filteredPrompts.length === 0) {
            this.showEmptyState();
            return;
        }

        document.getElementById('history-empty')?.classList.add('hidden');

        container.innerHTML = this.filteredPrompts.map(prompt => {
            const truncatedPrompt = this.truncateText(prompt.prompt, 150);
            const truncatedResponse = this.truncateText(prompt.response, 150);
            const timeAgo = this.formatTimeAgo(prompt.timestamp);

            const peerCount = prompt.peer_count || 0;
            const peersText = peerCount > 0 ? `${peerCount} peer${peerCount > 1 ? 's' : ''}` : 'Peers';

            return `
                <div class="theme-bg-surface rounded-xl p-6 shadow-sm theme-border border hover:shadow-md transition-shadow cursor-pointer" onclick="promptHistoryManager.previewPrompt('${prompt.id}')">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center mb-2">
                                <i data-lucide="send" class="h-4 w-4 theme-text-muted mr-2"></i>
                                <h3 class="text-sm font-semibold theme-text-primary">Your Query</h3>
                                <span class="theme-text-muted text-xs ml-auto">${timeAgo}</span>
                            </div>
                            <p class="theme-text-secondary text-sm mb-4">${this.escapeHtml(truncatedPrompt)}</p>

                            <div class="flex items-center mb-2">
                                <i data-lucide="users" class="h-4 w-4 theme-text-muted mr-2"></i>
                                <h3 class="text-sm font-semibold theme-text-primary">${peersText} Responded</h3>
                            </div>
                            <p class="theme-text-secondary text-sm">${this.escapeHtml(truncatedResponse)}</p>
                        </div>
                        <div class="flex items-center space-x-1 ml-4">
                            <button onclick="event.stopPropagation(); promptHistoryManager.copyPrompt('${prompt.id}')" class="p-2 rounded-lg transition-colors duration-200 hover:theme-bg-background theme-text-muted hover:theme-text-primary" title="Copy">
                                <i data-lucide="copy" class="h-4 w-4"></i>
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

    previewPrompt(promptId) {
        const prompt = this.prompts.find(p => p.id === promptId);
        if (!prompt) return;

        // Update preview panel content
        document.getElementById('preview-panel-info').textContent = this.formatTimeAgo(prompt.timestamp);
        document.getElementById('preview-prompt-content').textContent = prompt.prompt;

        // Format responses for peer queries
        if (prompt.responses && prompt.responses.length > 0) {
            const responseContainer = document.getElementById('preview-response-content');
            responseContainer.innerHTML = '';

            prompt.responses.forEach(resp => {
                const peerDiv = document.createElement('div');
                peerDiv.className = 'mb-4 p-3 theme-bg-surface rounded-lg';

                const peerName = document.createElement('h5');
                peerName.className = 'font-semibold theme-text-primary mb-2';
                peerName.textContent = resp.peer;

                const peerResponse = document.createElement('p');
                peerResponse.className = 'theme-text-secondary whitespace-pre-wrap';
                peerResponse.textContent = resp.response || resp.error || 'No response';

                peerDiv.appendChild(peerName);
                peerDiv.appendChild(peerResponse);
                responseContainer.appendChild(peerDiv);
            });
        } else {
            document.getElementById('preview-response-content').textContent = prompt.response;
        }

        // Store current prompt for copy functionality
        this.currentPreviewPrompt = prompt;

        // Open preview panel
        this.openPreviewPanel();
    }

    openPreviewPanel() {
        const panel = document.getElementById('prompt-preview-panel');
        const mainContent = document.getElementById('main-content-area');

        if (!panel || !mainContent) return;

        panel.classList.add('preview-panel-open');
        mainContent.classList.add('content-shrunk', 'with-preview');
    }

    closePreviewPanel() {
        const panel = document.getElementById('prompt-preview-panel');
        const mainContent = document.getElementById('main-content-area');

        if (!panel || !mainContent) return;

        panel.classList.remove('preview-panel-open');
        mainContent.classList.remove('with-preview');
    }

    async copyPrompt(promptId) {
        const prompt = this.prompts.find(p => p.id === promptId);
        if (!prompt) return;

        const text = `Prompt: ${prompt.prompt}\n\nResponse: ${prompt.response}`;

        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            this.showNotification('Failed to copy to clipboard', 'error');
        }
    }

    async copyConversation() {
        if (!this.currentPreviewPrompt) return;

        const text = `Prompt: ${this.currentPreviewPrompt.prompt}\n\nResponse: ${this.currentPreviewPrompt.response}`;

        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            this.showNotification('Failed to copy to clipboard', 'error');
        }
    }

    exportHistory() {
        // Create CSV content
        const csvContent = this.createCSVContent();

        // Create blob and download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);

        link.setAttribute('href', url);
        link.setAttribute('download', `prompt_history_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        this.showNotification('History exported successfully!', 'success');
    }

    createCSVContent() {
        const headers = ['Timestamp', 'Prompt', 'Response', 'Conversation ID'];
        const rows = this.prompts.map(p => [
            p.timestamp || '',
            `"${p.prompt.replace(/"/g, '""')}"`,
            `"${p.response.replace(/"/g, '""')}"`,
            p.conversation_id
        ]);

        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }

    // Utility methods
    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return 'Unknown time';

        const date = new Date(timestamp);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return Math.floor(diffInSeconds / 60) + ' minutes ago';
        if (diffInSeconds < 86400) return Math.floor(diffInSeconds / 3600) + ' hours ago';
        if (diffInSeconds < 2592000) return Math.floor(diffInSeconds / 86400) + ' days ago';
        return Math.floor(diffInSeconds / 2592000) + ' months ago';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

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
}

// Initialize the prompt history manager
window.initializePromptHistoryManager = function initializePromptHistoryManager() {
    // Clean up existing instance if it exists
    if (window.promptHistoryManager) {
        console.log('Cleaning up existing Prompt History Manager...');
        window.promptHistoryManager = null;
    }

    console.log('Initializing Prompt History Manager...');

    // Check if elements exist
    const overviewNav = document.getElementById('overview-tab');
    const historyNav = document.getElementById('history-tab');

    if (overviewNav && historyNav) {
        window.promptHistoryManager = new PromptHistoryManager();
        console.log('Prompt History Manager initialized successfully');
    } else {
        console.error('Required navigation elements not found');
        // Retry after a short delay
        if (!window.promptHistoryManager) {
            setTimeout(window.initializePromptHistoryManager, 100);
        }
    }
}

// Initialize immediately if DOM is ready, otherwise wait
if (!window.promptHistoryManagerEventAdded) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.initializePromptHistoryManager);
        window.promptHistoryManagerEventAdded = true;
    } else {
        window.initializePromptHistoryManager();
    }
}

} // End of script loading protection
