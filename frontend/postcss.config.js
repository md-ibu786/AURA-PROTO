/**
 * ============================================================================
 * FILE: postcss.config.js
 * LOCATION: frontend/postcss.config.js
 * ============================================================================
 *
 * PURPOSE:
 *    PostCSS configuration file for Tailwind CSS v4 with autoprefixer
 *
 * ROLE IN PROJECT:
 *    Configures PostCSS processing pipeline for the frontend build system.
 *    Works alongside Vite's Tailwind plugin to process CSS with vendor
 *    prefixing via autoprefixer.
 *
 * KEY COMPONENTS:
 *    - autoprefixer: Adds vendor prefixes to CSS for browser compatibility
 *
 * DEPENDENCIES:
 *    - External: autoprefixer (PostCSS plugin)
 *    - Internal: vite.config.ts (Tailwind Vite plugin configuration)
 *
 * USAGE:
 *    Automatically used by Vite during build process. No manual usage needed.
 *    See vite.config.ts for Tailwind plugin configuration.
 * ============================================================================
 */

/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    autoprefixer: {},
  },
};

export default config;
