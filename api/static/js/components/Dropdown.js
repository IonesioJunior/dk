/**
 * Dropdown Component
 * A wrapper around UIkit dropdown with additional functionality
 */

const Dropdown = {
    /**
     * Initialize dropdown functionality
     * @param {string|HTMLElement} selector - CSS selector or element for the dropdown container
     * @param {Object} options - Configuration options
     * @returns {Object} - The Dropdown component instance
     */
    init(selector, options = {}) {
        console.log('Initializing Dropdown component...');

        // Normalize selector to element
        const container = typeof selector === 'string'
            ? document.querySelector(selector)
            : selector;

        if (!container) {
            console.warn(`Dropdown: No element found with selector "${selector}"`);
            return this;
        }

        // Store options and elements
        this.options = Object.assign({
            onChange: null,           // Callback for item selection
            closeOnSelect: true,      // Auto-close dropdown after selection
            closeOnOutsideClick: true // Close dropdown when clicking outside
        }, options);

        // Store elements
        this.container = container;
        this.id = container.id.replace('-container', '');
        this.toggle = document.getElementById(`${this.id}-toggle`);
        this.content = document.getElementById(`${this.id}-content`);

        if (!this.toggle || !this.content) {
            console.warn(`Dropdown: Missing toggle or content elements for "${this.id}"`);
            return this;
        }

        // Set up additional event handlers
        this._setupEventHandlers();

        console.log(`Dropdown component initialized for ${this.id}`);
        return this;
    },

    /**
     * Set up event handlers for dropdown interactions
     * @private
     */
    _setupEventHandlers() {
        // Get all clickable items in the dropdown
        const items = this.content.querySelectorAll('[data-dropdown-item]');

        // Add event listeners to items
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                const value = item.getAttribute('data-value');
                const text = item.textContent.trim();

                // Call onChange handler if provided
                if (typeof this.options.onChange === 'function') {
                    this.options.onChange({
                        value,
                        text,
                        element: item,
                        event: e
                    });
                }

                // Close dropdown if configured to do so
                if (this.options.closeOnSelect) {
                    this.hide();
                }
            });
        });

        // Close on outside click if configured
        if (this.options.closeOnOutsideClick) {
            document.addEventListener('click', (e) => {
                // Check if click is outside dropdown
                if (!this.container.contains(e.target) && UIkit.dropdown(this.content).isActive()) {
                    this.hide();
                }
            });
        }
    },

    /**
     * Show the dropdown
     * @returns {Object} - The Dropdown component instance
     */
    show() {
        if (UIkit.dropdown && this.content) {
            UIkit.dropdown(this.content).show();
        }
        return this;
    },

    /**
     * Hide the dropdown
     * @returns {Object} - The Dropdown component instance
     */
    hide() {
        if (UIkit.dropdown && this.content) {
            UIkit.dropdown(this.content).hide();
        }
        return this;
    },

    /**
     * Toggle the dropdown visibility
     * @returns {Object} - The Dropdown component instance
     */
    toggle() {
        if (UIkit.dropdown && this.content) {
            const dropdown = UIkit.dropdown(this.content);
            dropdown.isActive() ? dropdown.hide() : dropdown.show();
        }
        return this;
    },

    /**
     * Set the selected item and update the toggle text
     * @param {string} value - The value of the item to select
     * @param {boolean} updateToggle - Whether to update the toggle button text
     * @returns {Object} - The Dropdown component instance
     */
    select(value, updateToggle = true) {
        // Find the item with matching value
        const item = this.content.querySelector(`[data-dropdown-item][data-value="${value}"]`);

        if (!item) {
            console.warn(`Dropdown: No item found with value "${value}"`);
            return this;
        }

        // Remove selected class from all items
        this.content.querySelectorAll('[data-dropdown-item]').forEach(el => {
            el.classList.remove('uk-active', 'selected', 'theme-bg-primary');
        });

        // Add selected class to this item
        item.classList.add('uk-active', 'selected', 'theme-bg-primary');

        // Update toggle text if needed
        if (updateToggle && this.toggle) {
            // Get the spans in the toggle, assuming the first one is the text
            const toggleText = this.toggle.querySelector('span');
            if (toggleText) {
                toggleText.textContent = item.textContent.trim();
            }
        }

        return this;
    },

    /**
     * Get the currently selected item value
     * @returns {string|null} - The selected value or null if none selected
     */
    getSelected() {
        const selectedItem = this.content.querySelector('[data-dropdown-item].selected, [data-dropdown-item].uk-active');
        return selectedItem ? selectedItem.getAttribute('data-value') : null;
    },

    /**
     * Create and insert a dropdown into a container
     * @param {string|HTMLElement} container - Container selector or element
     * @param {Object} options - Configuration options
     * @param {string} options.id - Unique ID for the dropdown (required)
     * @param {string} options.toggleText - Text to display in toggle button
     * @param {string} options.toggleIcon - Lucide icon name
     * @param {string} options.toggleClass - Additional classes for toggle button
     * @param {string} options.dropdownClass - Additional classes for dropdown content
     * @param {string} options.dropdownMode - Trigger mode (click, hover)
     * @param {string} options.dropdownPos - Position (bottom-left, bottom-right, etc.)
     * @param {string} options.dropdownOffset - Offset from toggle
     * @param {Array} options.items - Array of items to populate dropdown with
     * @returns {Object} - The created Dropdown instance
     */
    create(container, options) {
        // Validate required options
        if (!options.id) {
            console.error('Dropdown: ID is required when creating a dropdown');
            return null;
        }

        // Get container element
        const containerEl = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        if (!containerEl) {
            console.warn(`Dropdown: Container "${container}" not found`);
            return null;
        }

        // Default options
        const {
            id,
            toggleText = 'Select',
            toggleIcon = '',
            toggleClass = '',
            dropdownClass = '',
            dropdownMode = 'click',
            dropdownPos = 'bottom-left',
            dropdownOffset = null,
            items = []
        } = options;

        // Generate items HTML
        let itemsHtml = '';
        if (items.length > 0) {
            itemsHtml = '<ul class="uk-nav uk-dropdown-nav">';
            items.forEach(item => {
                const icon = item.icon ? `<i data-lucide="${item.icon}" class="h-4 w-4 mr-2"></i>` : '';
                itemsHtml += `
                    <li>
                        <a href="${item.href || '#'}" data-dropdown-item data-value="${item.value || ''}">
                            ${icon}<span>${item.text}</span>
                        </a>
                    </li>
                `;
            });
            itemsHtml += '</ul>';
        }

        // Create dropdown HTML
        const dropdownHtml = `
            <div class="uk-inline dropdown-component" id="${id}-container">
                <button id="${id}-toggle" class="uk-button uk-button-default flex items-center ${toggleClass}" type="button">
                    ${toggleIcon ? `<i data-lucide="${toggleIcon}" class="h-5 w-5 ${toggleText ? 'mr-2' : ''}"></i>` : ''}
                    ${toggleText ? `<span>${toggleText}</span>` : ''}
                    ${!toggleIcon ? '<i data-lucide="chevron-down" class="h-4 w-4 ml-1"></i>' : ''}
                </button>

                <div id="${id}-content"
                     uk-dropdown="mode: ${dropdownMode}; pos: ${dropdownPos}${dropdownOffset ? `; offset: ${dropdownOffset}` : ''}"
                     class="theme-bg-surface ${dropdownClass}">
                    ${itemsHtml || '<div class="uk-padding-small">No items</div>'}
                </div>
            </div>
        `;

        // Insert the dropdown HTML
        containerEl.insertAdjacentHTML('beforeend', dropdownHtml);

        // Initialize icons if Lucide is available
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons(containerEl);
        }

        // Initialize and return the dropdown
        return this.init(`#${id}-container`, options);
    }
};

// Export to window for global access
window.Dropdown = Dropdown;

// Auto-initialize dropdowns with data-auto-init attribute
document.addEventListener('DOMContentLoaded', () => {
    const autoInitDropdowns = document.querySelectorAll('.dropdown-component[data-auto-init]');
    autoInitDropdowns.forEach(container => {
        Dropdown.init(container);
    });
});
