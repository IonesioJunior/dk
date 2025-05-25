window.Toaster = {
    defaultOptions: {
        position: 'bottom-right',
        timeout: 5000,
        closeButton: true,
        animation: 'slide'
    },

    activeToasts: new Set(),

    init: function() {
        // Prevent double initialization
        if (this._initialized) {
            return;
        }

        console.log('Toaster component initialized');

        window.addEventListener('error', (event) => {
            this.error(`Error: ${event.message}`);
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.error(`Unhandled Promise Rejection: ${event.reason}`);
        });

        this.injectStyles();

        this._initialized = true;
    },

    injectStyles: function() {
        if (!document.getElementById('toaster-styles')) {
            const link = document.createElement('link');
            link.id = 'toaster-styles';
            link.rel = 'stylesheet';
            link.href = '/static/css/toaster.css';
            document.head.appendChild(link);
        }
    },


    info: function(message, options = {}) {
        return this.show('primary', message, options);
    },

    success: function(message, options = {}) {
        return this.show('success', message, options);
    },

    warning: function(message, options = {}) {
        return this.show('warning', message, options);
    },

    error: function(message, options = {}) {
        return this.show('danger', message, options);
    },

    cta: function(message, action, options = {}) {
        const config = Object.assign({}, this.defaultOptions, options, {
            persist: true,
            timeout: 0
        });

        const notification = this.createCTANotification(message, action, config);
        return notification;
    },

    warningCta: function(message, action, options = {}) {
        const config = Object.assign({}, this.defaultOptions, options, {
            persist: true,
            timeout: 0,
            status: 'warning'
        });

        const notification = this.createCTANotification(message, action, config);
        return notification;
    },

    show: function(type, message, options = {}) {
        const config = Object.assign({}, this.defaultOptions, options);

        const mappedType = {
            'error': 'danger',
            'info': 'primary'
        };

        const notificationType = mappedType[type] || type;

        const notification = UIkit.notification({
            message: this.formatMessage(message, type),
            status: notificationType,
            pos: config.position,
            timeout: config.persist ? 0 : config.timeout
        });

        this.activeToasts.add(notification);

        if (config.timeout && config.timeout > 0) {
            setTimeout(() => {
                this.activeToasts.delete(notification);
            }, config.timeout);
        }

        return notification;
    },

    createCTANotification: function(message, action, options) {
        const id = `toaster-cta-${Date.now()}`;
        const dismissText = action.dismissText || 'Dismiss';
        const actionText = action.text || 'Action';
        const icon = action.icon || this.getIconForType('cta');

        const html = `
            <div class="toaster-cta" id="${id}">
                <div class="toaster-content">
                    ${icon ? `<span class="toaster-icon" uk-icon="icon: ${icon}"></span>` : ''}
                    <span class="toaster-message">${message}</span>
                </div>
                <div class="toaster-actions">
                    <button class="uk-button uk-button-small uk-button-default toaster-dismiss">${dismissText}</button>
                    <button class="uk-button uk-button-small uk-button-primary toaster-action">${actionText}</button>
                </div>
            </div>
        `;

        const notification = UIkit.notification({
            message: html,
            status: options.status || 'primary',
            pos: options.position,
            timeout: 0
        });

        setTimeout(() => {
            const element = document.getElementById(id);
            if (element) {
                const dismissBtn = element.querySelector('.toaster-dismiss');
                const actionBtn = element.querySelector('.toaster-action');

                dismissBtn.addEventListener('click', () => {
                    notification.close();
                    this.activeToasts.delete(notification);
                });

                actionBtn.addEventListener('click', () => {
                    if (action.callback && typeof action.callback === 'function') {
                        action.callback();
                    }
                    notification.close();
                    this.activeToasts.delete(notification);
                });
            }
        }, 100);

        this.activeToasts.add(notification);
        return notification;
    },

    formatMessage: function(message, type) {
        const icon = this.getIconForType(type);
        if (icon) {
            return `<span uk-icon="icon: ${icon}; ratio: 0.8" class="toaster-type-icon"></span> ${message}`;
        }
        return message;
    },

    getIconForType: function(type) {
        const icons = {
            'success': 'check',
            'error': 'warning',
            'danger': 'warning',
            'warning': 'info',
            'info': 'info',
            'primary': 'info',
            'cta': 'bell'
        };
        return icons[type] || null;
    },

    clear: function() {
        this.activeToasts.forEach(notification => {
            if (notification && notification.close) {
                notification.close();
            }
        });
        this.activeToasts.clear();
    },

    clearByType: function(type) {
        const elements = document.querySelectorAll(`.uk-notification-message-${type}`);
        elements.forEach(el => {
            const notification = el.closest('.uk-notification');
            if (notification) {
                UIkit.notification.close(notification);
            }
        });
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Toaster.init());
} else {
    Toaster.init();
}
