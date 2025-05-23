/**
 * Main application script for the SPA
 */

// Initialize the application when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize app modules
    // Note: ThemeManager is now managed by theme.js directly
    Router.init();

    // Initialize Lucide icons
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        lucide.createIcons();
    }

    // Add theme toggle functionality to the menu item
    const themeToggleMenu = document.getElementById('theme-toggle-menu');
    if (themeToggleMenu) {
        themeToggleMenu.addEventListener('click', (e) => {
            e.preventDefault();
            if (window.appTheme) {
                const newMode = window.appTheme.toggleMode();
                // Update icon based on theme
                const icon = themeToggleMenu.querySelector('i');
                if (icon) {
                    icon.setAttribute('data-lucide', newMode === 'dark' ? 'sun' : 'moon');
                    if (window.lucide) lucide.createIcons();
                }
            }
        });
    }
});

/**
 * Theme Manager reference
 * This section is commented out as it's been moved to theme.js
 * Left here for reference only
 */
// const ThemeManager = { /* moved to theme.js */ };

/**
 * SPA Router - Handles navigation between views
 */
const Router = {
    routes: ['home', 'dashboard', 'settings', 'about'],
    currentRoute: null,

    init() {
        // Set initial route from hash or default to home
        const initialRoute = window.location.hash.substring(1) || 'home';
        this.navigate(initialRoute);

        // Listen for hash changes
        window.addEventListener('hashchange', () => {
            const route = window.location.hash.substring(1) || 'home';
            this.navigate(route);
        });

        // Set up navigation clicks
        document.querySelectorAll('#app-navigation li').forEach(item => {
            item.addEventListener('click', (e) => {
                const route = item.getAttribute('data-route');
                window.location.hash = route;
            });
        });

        return this;
    },

    navigate(route) {
        if (!this.routes.includes(route)) {
            route = 'home'; // Default to home for unknown routes
        }

        this.currentRoute = route;

        // Show loading spinner (could be used for async content)
        const spinner = document.getElementById('loading-spinner');
        spinner.removeAttribute('hidden');

        // Update navigation state
        document.querySelectorAll('#app-navigation li').forEach(item => {
            if (item.getAttribute('data-route') === route) {
                item.classList.add('uk-active');
            } else {
                item.classList.remove('uk-active');
            }
        });

        // Hide all views
        document.querySelectorAll('.app-view').forEach(view => {
            view.setAttribute('hidden', '');
        });

        // Simulate loading delay for demonstration (remove in production)
        setTimeout(() => {
            // Show the selected view
            const viewElement = document.getElementById(`view-${route}`);
            if (viewElement) {
                viewElement.removeAttribute('hidden');

                // Dispatch a view changed event for components to react to
                document.dispatchEvent(new CustomEvent('viewchanged', {
                    detail: { route: route, element: viewElement }
                }));
            }

            // Hide loading spinner
            spinner.setAttribute('hidden', '');
        }, 300);

        return route;
    }
};

/**
 * API Service - Handles communication with backend API
 */
const ApiService = {
    baseUrl: '/api',

    async get(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}/${endpoint}`);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            throw error;
        }
    },

    async post(endpoint, data) {
        try {
            const response = await fetch(`${this.baseUrl}/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            throw error;
        }
    }
};
