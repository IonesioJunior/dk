/**
 * Theme Configuration
 *
 * This file serves as a central place to store theme settings including
 * color palettes, typography, spacing, and other design tokens.
 * Works with both Tailwind CSS and UIkit.
 */

// Initialize theme object
const theme = {
  // Current theme mode
  currentMode: localStorage.getItem('themeMode') || 'light',

  // Color palettes
  colors: {
    light: {
      primary: '#1e88e5',       // Blue
      secondary: '#6c757d',     // Gray
      success: '#28a745',       // Green
      danger: '#dc3545',        // Red
      warning: '#ffc107',       // Yellow
      info: '#17a2b8',          // Teal
      background: '#f8f9fa',    // Light gray
      surface: '#ffffff',       // White
      text: {
        primary: '#212529',     // Near black
        secondary: '#6c757d',   // Medium gray
        muted: '#adb5bd',       // Light gray
      },
      border: '#dee2e6',        // Light gray
    },
    dark: {
      primary: '#90caf9',       // Light blue
      secondary: '#adb5bd',     // Light gray
      success: '#4caf50',       // Green
      danger: '#f44336',        // Red
      warning: '#ffeb3b',       // Yellow
      info: '#4dd0e1',          // Light teal
      background: '#121212',    // Very dark gray
      surface: '#1e1e1e',       // Dark gray
      text: {
        primary: '#f8f9fa',     // Near white
        secondary: '#ced4da',   // Light gray
        muted: '#6c757d',       // Medium gray
      },
      border: '#343a40',        // Dark gray
    }
  },

  // Typography
  typography: {
    fontFamily: {
      base: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      heading: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      mono: 'SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    },
    fontSize: {
      xs: '0.75rem',     // 12px
      sm: '0.875rem',    // 14px
      base: '1rem',      // 16px
      lg: '1.125rem',    // 18px
      xl: '1.25rem',     // 20px
      '2xl': '1.5rem',   // 24px
      '3xl': '1.875rem', // 30px
      '4xl': '2.25rem',  // 36px
      '5xl': '3rem',     // 48px
    },
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      none: 1,
      tight: 1.25,
      snug: 1.375,
      normal: 1.5,
      relaxed: 1.625,
      loose: 2,
    }
  },

  // Spacing scale (rems)
  spacing: {
    '0': '0',
    '1': '0.25rem',
    '2': '0.5rem',
    '3': '0.75rem',
    '4': '1rem',
    '5': '1.25rem',
    '6': '1.5rem',
    '8': '2rem',
    '10': '2.5rem',
    '12': '3rem',
    '16': '4rem',
    '20': '5rem',
    '24': '6rem',
    '32': '8rem',
    '40': '10rem',
    '48': '12rem',
    '56': '14rem',
    '64': '16rem',
  },

  // Border radius
  borderRadius: {
    'none': '0',
    'sm': '0.125rem',
    'default': '0.25rem',
    'md': '0.375rem',
    'lg': '0.5rem',
    'xl': '0.75rem',
    '2xl': '1rem',
    'full': '9999px',
  },

  // Box shadows
  boxShadow: {
    'none': 'none',
    'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    'default': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    'inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
  },

  // Animation timing
  animation: {
    fastest: '100ms',
    faster: '200ms',
    fast: '300ms',
    normal: '400ms',
    slow: '500ms',
    slower: '600ms',
    slowest: '1000ms',
  },

  // Z-index scale
  zIndex: {
    'auto': 'auto',
    '0': '0',
    '10': '10',
    '20': '20',
    '30': '30',
    '40': '40',
    '50': '50',
    'modal': '1000',
    'toast': '2000',
    'tooltip': '3000',
  },

  // Get the current theme colors
  getCurrentColors() {
    return this.colors[this.currentMode];
  },

  // Toggle between light and dark modes
  toggleMode() {
    this.currentMode = this.currentMode === 'light' ? 'dark' : 'light';
    localStorage.setItem('themeMode', this.currentMode);
    this.applyTheme();
    return this.currentMode;
  },

  // Set specific theme mode
  setMode(mode) {
    if (mode !== 'light' && mode !== 'dark') {
      return;
    }
    this.currentMode = mode;
    localStorage.setItem('themeMode', mode);
    this.applyTheme();
  },

  // Apply current theme to the document
  applyTheme() {
    const colors = this.getCurrentColors();
    const isDark = this.currentMode === 'dark';

    // Set data attribute on document for CSS selectors
    document.documentElement.setAttribute('data-theme', this.currentMode);

    // Apply colors to document root for CSS variables
    document.documentElement.style.setProperty('--color-primary', colors.primary);
    document.documentElement.style.setProperty('--color-secondary', colors.secondary);
    document.documentElement.style.setProperty('--color-success', colors.success);
    document.documentElement.style.setProperty('--color-danger', colors.danger);
    document.documentElement.style.setProperty('--color-warning', colors.warning);
    document.documentElement.style.setProperty('--color-info', colors.info);
    document.documentElement.style.setProperty('--color-background', colors.background);
    document.documentElement.style.setProperty('--color-surface', colors.surface);
    document.documentElement.style.setProperty('--color-text-primary', colors.text.primary);
    document.documentElement.style.setProperty('--color-text-secondary', colors.text.secondary);
    document.documentElement.style.setProperty('--color-text-muted', colors.text.muted);
    document.documentElement.style.setProperty('--color-border', colors.border);

    // Apply body class for UIkit
    document.body.classList.toggle('uk-light', !isDark);
    document.body.classList.toggle('uk-dark', isDark);

    // Apply background color to body
    document.body.style.backgroundColor = colors.background;
    document.body.style.color = colors.text.primary;

    // Apply text color to inputs and textareas
    const inputs = document.querySelectorAll('input, textarea');
    inputs.forEach(input => {
      input.style.color = colors.text.primary;
    });

    // Dispatch theme change event
    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { mode: this.currentMode, colors }
    }));
  },

  // Initialize theme
  init() {
    // Apply theme on load
    this.applyTheme();

    // Set up tailwind config if tailwind is available
    this.configureTailwind();

    // Configure system preference listener
    try {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      // Use the appropriate event listener method (some browsers use different methods)
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', e => {
          if (localStorage.getItem('themeMode') === null) {
            this.setMode(e.matches ? 'dark' : 'light');
          }
        });
      } else if (mediaQuery.addListener) {
        // For older browsers
        mediaQuery.addListener(e => {
          if (localStorage.getItem('themeMode') === null) {
            this.setMode(e.matches ? 'dark' : 'light');
          }
        });
      }
    } catch (error) {
      // Error setting up media query listener
    }

    return this;
  },

  // Configure Tailwind with current theme
  configureTailwind() {
    try {
      if (window.tailwind) {
        const colors = this.getCurrentColors();
        window.tailwind.config = {
          darkMode: 'class',
          theme: {
            extend: {
              colors: {
                primary: colors.primary,
                secondary: colors.secondary,
                success: colors.success,
                danger: colors.danger,
                warning: colors.warning,
                info: colors.info,
                background: colors.background,
                surface: colors.surface,
              },
              fontFamily: this.typography.fontFamily,
              fontSize: this.typography.fontSize,
              fontWeight: this.typography.fontWeight,
              lineHeight: this.typography.lineHeight,
              spacing: this.spacing,
              borderRadius: this.borderRadius,
              boxShadow: this.boxShadow,
            }
          }
        };
      }
    } catch (error) {
      // Error configuring Tailwind
    }
  }
};

// Export theme object to window immediately
window.appTheme = theme;

// Auto-initialize theme when script loads or is parsed
(function() {
  // Check if document is already loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    // Document already loaded, initialize immediately
    initTheme();
  }

  function initTheme() {
    try {
      window.appTheme.init();

      // Note: Theme toggle button listener is now handled by ThemeToggle component

    } catch (error) {
      // Error initializing theme
    }
  }
})();
