/**
 * Dashboard Component
 * Handles the dashboard view functionality
 */

const DashboardComponent = {
    init() {
        // Listen for view changes to initialize dashboard when it becomes visible
        document.addEventListener('viewchanged', (event) => {
            if (event.detail.route === 'dashboard') {
                this.loadDashboardData();
            }
        });

        return this;
    },

    async loadDashboardData() {
        const dashboardView = document.getElementById('view-dashboard');
        if (!dashboardView) return;

        // Create loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'uk-flex uk-flex-center uk-margin';
        loadingDiv.innerHTML = '<div uk-spinner="ratio: 1"></div>';

        // Add to dashboard view
        dashboardView.querySelector('.uk-alert-primary').after(loadingDiv);

        try {
            // Simulate API call - in real app, use ApiService
            // const data = await ApiService.get('dashboard/stats');

            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Sample data for demo
            const data = {
                stats: [
                    { label: 'Users', value: 1243, icon: 'users', color: 'theme-primary' },
                    { label: 'Revenue', value: '$5,243', icon: 'dollar-sign', color: 'theme-success' },
                    { label: 'Tasks', value: 24, icon: 'check-square', color: 'theme-warning' },
                    { label: 'Messages', value: 7, icon: 'mail', color: 'theme-info' }
                ],
                recentActivity: [
                    { user: 'John Doe', action: 'Created a new task', time: '2 hours ago' },
                    { user: 'Jane Smith', action: 'Completed project milestone', time: '4 hours ago' },
                    { user: 'Mike Johnson', action: 'Added new comment', time: '1 day ago' }
                ]
            };

            // Generate dashboard content
            const statsHtml = this.generateStatsCards(data.stats);
            const activityHtml = this.generateActivityList(data.recentActivity);

            // Create dashboard content
            const dashboardContent = document.createElement('div');
            dashboardContent.innerHTML = `
                <div class="uk-margin-medium-top">
                    <h2 class="uk-heading-line uk-text-center"><span>Dashboard Overview</span></h2>
                    <div class="uk-grid-small uk-child-width-1-2@s uk-child-width-1-4@l" uk-grid>
                        ${statsHtml}
                    </div>

                    <h2 class="uk-heading-line uk-text-center uk-margin-medium-top"><span>Recent Activity</span></h2>
                    <div class="uk-card uk-card-default uk-card-body uk-margin">
                        <ul class="uk-list uk-list-divider">
                            ${activityHtml}
                        </ul>
                    </div>
                </div>
            `;

            // Remove loading indicator and append content
            loadingDiv.remove();
            dashboardView.appendChild(dashboardContent);

            // Initialize any new icons
            lucide.createIcons(dashboardView);

        } catch (error) {
            console.error('Failed to load dashboard data:', error);

            // Show error message
            loadingDiv.innerHTML = `
                <div class="uk-alert-danger" uk-alert>
                    <p>Failed to load dashboard data. Please try again later.</p>
                </div>
            `;
        }
    },

    generateStatsCards(stats) {
        return stats.map(stat => `
            <div>
                <div class="uk-card uk-card-default uk-card-body uk-text-center">
                    <i data-lucide="${stat.icon}" class="h-10 w-10 mx-auto mb-3 ${stat.color}"></i>
                    <h3 class="uk-card-title">${stat.value}</h3>
                    <p class="uk-text-meta">${stat.label}</p>
                </div>
            </div>
        `).join('');
    },

    generateActivityList(activities) {
        return activities.map(activity => `
            <li>
                <div class="uk-grid-small" uk-grid>
                    <div class="uk-width-expand">
                        <strong>${activity.user}</strong> ${activity.action}
                    </div>
                    <div class="uk-width-auto uk-text-muted uk-text-small">
                        ${activity.time}
                    </div>
                </div>
            </li>
        `).join('');
    }
};

// Initialize the component
document.addEventListener('DOMContentLoaded', () => {
    DashboardComponent.init();
});
