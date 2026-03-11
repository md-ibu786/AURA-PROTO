// postcss.config.js
// PostCSS configuration for Tailwind CSS v4

// Configures PostCSS with autoprefixer for vendor prefixing
// Tailwind CSS v4 is now handled by the @tailwindcss/vite plugin
// See vite.config.ts for Tailwind plugin configuration

// @see: vite.config.ts - Tailwind Vite plugin configuration
// @see: src/styles/index.css - CSS entry point with Tailwind directives
// @note: Tailwind v4 uses CSS-based configuration via @theme in index.css

/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    autoprefixer: {},
  },
};

export default config;
