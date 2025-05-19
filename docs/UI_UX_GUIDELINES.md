# UI/UX Design Guidelines

This document outlines the design patterns, components, and principles used throughout the Syft Agent UI. It serves as a reference for maintaining design consistency across the application.

## Table of Contents

- [Color Palette](#color-palette)
- [Typography](#typography)
- [Spacing and Layout](#spacing-and-layout)
- [Components](#components)
  - [Sidebar](#sidebar)
  - [World Map](#world-map)
  - [Locations View](#locations-view)
  - [Database View](#database-view)
  - [Search View](#search-view)
- [Responsive Design](#responsive-design)
- [Accessibility](#accessibility)
- [Theme Switching](#theme-switching)

## Color Palette

The application uses a cohesive color palette that adapts between dark and light themes.

### Dark Theme (Default)

- **Background Colors**
  - Primary Background: `#111` (near black)
  - Card/Container Background: `rgba(45, 45, 45, 0.7)` (semi-transparent dark gray)
  - Sidebar Background: `rgba(30, 30, 30, 0.85)` (semi-transparent darker gray with blur)
  - Secondary Elements: `rgba(60, 60, 60, 0.7)` (lighter dark gray)
  - Hover States: `rgba(255, 255, 255, 0.1)` (subtle white)
  - Active States: `rgba(255, 255, 255, 0.2)` (slightly brighter white)

- **Text Colors**
  - Primary Text: `#e0e0e0` (off-white)
  - Secondary Text: `#a0a0a0` (medium gray)
  - Tertiary Text: `#808080` (darker gray)

- **Border Colors**
  - Primary Border: `rgba(80, 80, 80, 0.3)` (semi-transparent gray)
  - Dividers: `#444` (medium-dark gray)

- **Map Colors**
  - Country Fill: `#3a3a3a` (medium-dark gray)
  - Country Stroke: `#555` (medium gray)

### Light Theme

- **Background Colors**
  - Primary Background: `#f0f0f0` (light gray)
  - Card/Container Background: `rgba(255, 255, 255, 0.8)` (semi-transparent white)
  - Secondary Elements: `rgba(240, 240, 240, 0.8)` (light gray)
  - Hover States: `rgba(0, 0, 0, 0.05)` (subtle dark)
  - Active States: `rgba(0, 0, 0, 0.1)` (slightly darker)

- **Text Colors**
  - Primary Text: `#333333` (dark gray)
  - Secondary Text: `#666666` (medium gray)
  - Tertiary Text: `#888888` (lighter gray)

- **Border Colors**
  - Primary Border: `rgba(200, 200, 200, 0.5)` (semi-transparent light gray)
  - Dividers: `#ddd` (very light gray)

- **Map Colors**
  - Country Fill: `#d0d0d0` (light gray)
  - Country Stroke: `#999` (medium gray)

## Typography

The UI follows a consistent typographic hierarchy:

- **Font Family**: System font stack defaulting to sans-serif fonts
  ```css
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  ```

- **Font Sizes**:
  - Page Titles: `1.8rem` (28.8px)
  - Section Headers: `1.2rem` (19.2px)
  - Card Titles: `1.1rem` (17.6px)
  - Body Text: `1rem` (16px)
  - Secondary Text: `0.95rem` (15.2px)
  - Metadata/Small Text: `0.85rem` (13.6px)

- **Font Weights**:
  - Headers: `500` or `600`
  - Body Text: `400`
  - Emphasis/Highlights: `500`

- **Line Heights**:
  - Headers: `1.2`
  - Body Text: `1.5`

## Spacing and Layout

Consistent spacing creates visual harmony throughout the interface:

- **Base Spacing Unit**: `0.25rem` (4px)

- **Spacing Scale**:
  - Extra Small: `0.25rem` (4px)
  - Small: `0.5rem` (8px)
  - Medium: `1rem` (16px)
  - Large: `1.5rem` (24px)
  - Extra Large: `2rem` (32px)
  - Double Extra Large: `2.5rem` (40px)

- **Container Padding**:
  - Main Content: `2rem` (32px)
  - Cards: `1.5rem` (24px)
  - Sidebar: `15px 0`

- **Grid Layout**:
  - Card Grid: `grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))`
  - Gap: `1.5rem` (24px)

- **Vertical Rhythm**:
  - Section Margins: `2rem` (32px)
  - Card Margins: `1.5rem` (24px)
  - Element Margins: `0.75rem` (12px)

## Components

### Sidebar

The sidebar serves as the primary navigation method for the application.

- **Dimensions**:
  - Width: `60px`
  - Height: `100vh` (full height)
  - Icon Size: `40px` × `40px`

- **Styling**:
  - Background: `rgba(30, 30, 30, 0.85)` with `backdrop-filter: blur(5px)`
  - Box Shadow: `0 0 10px rgba(0, 0, 0, 0.5)`
  - Border Radius (icons): `50%` (circular)

- **States**:
  - Default: Transparent background
  - Hover: `rgba(255, 255, 255, 0.1)` background
  - Active: `rgba(255, 255, 255, 0.2)` background, slightly brighter icon color

- **Interaction**:
  - Click on icon to switch views
  - Transitions: `0.2s ease` for all state changes

### World Map

A minimalist vector map serving as the primary visual backdrop.

- **Styling**:
  - Projection: Natural Earth (compromise projection balancing size and shape)
  - Country Stroke Width: `0.5px`
  - Full-Screen Display

- **Tech Stack**:
  - D3.js for map rendering
  - TopoJSON for geographical data

- **Performance Considerations**:
  - Uses lightweight country boundaries (110m resolution)
  - Handles window resizing efficiently

### Locations View

A card-based view for displaying geographical locations.

- **Card Design**:
  - Background: Semi-transparent (card-bg variable)
  - Border Radius: `8px`
  - Padding: `1rem`
  - Box Shadow on Hover: `0 4px 12px rgba(0, 0, 0, 0.15)`
  - Transform on Hover: `translateY(-3px)`

- **Layout**:
  - Grid: Responsive columns with minimum width of 300px
  - Icon Size: `40px`
  - Icon Background: Circle with accent color

- **Typography**:
  - Location Name: `1.1rem`, regular weight
  - Location Details: `0.9rem`, secondary text color

### Database View

A data-focused view with statistics and tabular information.

- **Card Design**:
  - Statistic Cards: Horizontal layout with icon and text
  - Table Container: Full-width with rounded corners
  - Table Header: Slightly darker background than table body
  - Table Rows: Bottom border separating rows

- **Statistics Display**:
  - Icon Container: `50px` square with rounded corners
  - Value: `1.5rem`, bold
  - Label: `0.9rem`, secondary color

- **Table Design**:
  - Full Width: `100%`
  - Cell Padding: `1rem 1.5rem`
  - Header: Slightly emphasized with background color
  - Alternating Rows: Subtle background difference (in light theme)

- **Action Buttons**:
  - Primary Actions: Filled background with text and icon
  - Icon-Only Actions: `32px` square, transparent background with hover state
  - Spacing Between Actions: `0.75rem`

### Search View

A search-focused view with filters and results.

- **Search Box**:
  - Large, prominent input field
  - Border Radius: `8px`
  - Height: Approximately `56px` including padding
  - Left Icon: Search icon
  - Right Button: Action button with arrow

- **Filters**:
  - Pills Design: Rounded capsules (`border-radius: 20px`)
  - Horizontal Layout: Flexible row with appropriate spacing
  - States: Default, Hover, Active
  - Padding: `0.5rem 1rem`

- **Search Results**:
  - Container: Card-like with rounded corners
  - Item Spacing: Consistent padding of `1.25rem`
  - Item Border: Bottom border except for last item
  - Hover State: Subtle background change

## Responsive Design

The interface adapts to different screen sizes with these guidelines:

- **Sidebar**: Remains fixed at 60px width
- **Content Area**: Fills remaining space
- **Card Grids**: Responsive with auto-fill and minimum widths
- **Typography**: Uses relative units (`rem`) for scalability
- **Map**: Resizes with window and updates projections

## Accessibility

The design follows these accessibility principles:

- **Color Contrast**: Maintains 4.5:1 contrast ratio for text
- **Focus States**: Visible indicators for keyboard navigation
- **Semantic Structure**: Proper heading hierarchy (h2 → h3 → h4)
- **Readable Text**: Maintains minimum text size of 16px for body content
- **Icon Labels**: All icons have accompanying text or aria-labels

## Theme Switching

The application supports seamless switching between dark and light themes:

- **Implementation**:
  - CSS Variables for all theme-dependent properties
  - JavaScript toggles between predefined theme sets
  - Transition duration of 0.3s for smooth theme changes

- **Theme Persistence**:
  - Default: Dark theme
  - Toggle: Moon/Sun icon in sidebar

- **Consistent Visual Hierarchy**:
  - Both themes maintain the same visual hierarchy and importance
  - Color relationships (primary/secondary/tertiary) are preserved

---

This guide serves as the foundation for consistent, aesthetically pleasing, and functional UI development across the Syft Agent application. All new features and components should adhere to these guidelines to maintain design coherence.