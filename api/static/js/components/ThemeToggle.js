/**
 * Theme Toggle Component
 * Provides theme toggle functionality for the application
 */

const ThemeToggle = {
    /**
     * Initialize the theme toggle component
     * @param {string} selector - CSS selector for the theme toggle button
     * @returns {Object} - The ThemeToggle object
     */
    init(selector = '#theme-toggle') {
        console.log('Initializing Theme Toggle component...');

        // Check if appTheme is available
        if (!window.appTheme) {
            console.error('Theme Toggle requires window.appTheme to be available');
            return this;
        }

        // Get the toggle button
        const toggleButton = document.querySelector(selector);
        if (!toggleButton) {
            console.warn(`Theme Toggle: No element found with selector "${selector}"`);
            return this;
        }

        // Initialize the button icon based on current theme
        this.updateButtonIcon(toggleButton);

        // Add click event listener
        toggleButton.addEventListener('click', () => {
            console.log('Theme toggle clicked');

            // Toggle the theme
            if (typeof window.appTheme.toggleMode === 'function') {
                window.appTheme.toggleMode();
                this.updateButtonIcon(toggleButton);
            } else {
                console.error('appTheme.toggleMode is not a function');
            }
        });

        // Listen for theme changes from other sources
        window.addEventListener('themechange', () => {
            this.updateButtonIcon(toggleButton);
        });

        console.log('Theme Toggle component initialized');
        return this;
    },

    /**
     * Update the button icon based on the current theme
     * @param {HTMLElement} button - The theme toggle button element
     */
    updateButtonIcon(button) {
        if (!button) return;

        // Get the icon element
        const iconElement = button.querySelector('[data-lucide]');
        if (!iconElement) return;

        // Determine icon based on current theme
        const isDark = window.appTheme && window.appTheme.currentMode === 'dark';
        const iconName = isDark ? 'sun' : 'moon';

        // Update icon
        if (iconElement.getAttribute('data-lucide') !== iconName) {
            iconElement.setAttribute('data-lucide', iconName);

            // Refresh the icon if Lucide is available
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons(button);
            }
        }
    },

    /**
     * Create and insert a theme toggle button into a container
     * @param {string|HTMLElement} container - Container selector or element where the button should be inserted
     * @param {string} [position='beforeend'] - InsertAdjacentHTML position
     * @param {Object} [options] - Options for customizing the button
     * @param {string} [options.id='theme-toggle'] - Button ID
     * @param {string} [options.btnClass='uk-button uk-button-default flex items-center'] - Button CSS classes
     * @param {string} [options.iconClass='h-5 w-5 mr-1'] - Icon CSS classes
     * @param {boolean} [options.showText=true] - Whether to show "Theme" text
     * @returns {HTMLElement|null} - The created button or null if container not found
     */
    createButton(container, position = 'beforeend', options = {}) {
        // Default options
        const {
            id = 'theme-toggle',
            btnClass = 'uk-button uk-button-default flex items-center',
            iconClass = 'h-5 w-5 mr-1',
            showText = true
        } = options;

        // Get container element
        const containerEl = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        if (!containerEl) {
            console.warn(`Theme Toggle: Container "${container}" not found`);
            return null;
        }

        // Create button HTML
        const isDark = window.appTheme && window.appTheme.currentMode === 'dark';
        const iconName = isDark ? 'sun' : 'moon';

        const buttonHtml = `
            <button id="${id}" class="${btnClass}">
                <i data-lucide="${iconName}" class="${iconClass}"></i>
                ${showText ? '<span>Theme</span>' : ''}
            </button>
        `;

        // Insert the button
        containerEl.insertAdjacentHTML(position, buttonHtml);

        // Get the inserted button
        const button = document.getElementById(id);

        // Initialize the button
        if (button) {
            // Add click event listener
            button.addEventListener('click', () => {
                if (typeof window.appTheme.toggleMode === 'function') {
                    window.appTheme.toggleMode();
                    this.updateButtonIcon(button);
                }
            });

            // Refresh icon if Lucide is available
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons(button);
            }
        }

        return button;
    }
};

// Export to window for global access
window.ThemeToggle = ThemeToggle;

// Auto-initialize on DOMContentLoaded, but only if element exists
document.addEventListener('DOMContentLoaded', () => {
    // Check if the theme toggle element exists before initializing
    if (document.querySelector('#theme-toggle')) {
        ThemeToggle.init();
    } else {
        // Create a hidden theme toggle element if not found
        const hiddenToggle = document.createElement('div');
        hiddenToggle.style.display = 'none';
        hiddenToggle.innerHTML = '<button id="theme-toggle" aria-hidden="true"></button>';
        document.body.appendChild(hiddenToggle);

        // Now initialize with the hidden element
        ThemeToggle.init();
    }
});
