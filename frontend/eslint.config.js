/**
 * ============================================================================
 * FILE: eslint.config.js
 * LOCATION: frontend/eslint.config.js
 * ============================================================================
 *
 * PURPOSE:
 *    ESLint configuration for TypeScript React frontend code quality
 *
 * ROLE IN PROJECT:
 *    Enforces code style and best practices for TypeScript and React.
 *    Configures rules for React Hooks and Fast Refresh, extends recommended
 *    TypeScript and React configurations for consistent code quality.
 *
 * KEY COMPONENTS:
 *    - TypeScript rules: ts-eslint recommended type-checked configuration
 *    - React Hooks: eslint-plugin-react-hooks for rules of hooks
 *    - React Refresh: eslint-plugin-react-refresh for hot reload support
 *    - Global ignores: dist/ and coverage/ directories excluded
 *
 * DEPENDENCIES:
 *    - External: @eslint/js, typescript-eslint, eslint-plugin-react-hooks,
 *      eslint-plugin-react-refresh, globals
 *    - Internal: None
 *
 * USAGE:
 *    Run with: npm run lint
 *    Automatically checks TypeScript and TSX files
 * ============================================================================
 */

import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'coverage']),
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      'react-refresh': reactRefresh,
    },
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
    ],
    rules: {
      'react-refresh/only-export-components': ['error', { allowConstantExport: true }],
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])
