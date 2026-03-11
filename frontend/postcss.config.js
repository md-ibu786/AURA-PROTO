// postcss.config.js
// PostCSS configuration for Tailwind CSS v4

// Configures PostCSS to process Tailwind CSS with autoprefixer
// Tailwind v4 uses the @tailwindcss/postcss plugin for CSS processing

// @see: src/styles/index.css - CSS entry point with Tailwind directives
// @note: Tailwind v4 uses CSS-based configuration via @theme in index.css

/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {},
  },
};

export default config;
