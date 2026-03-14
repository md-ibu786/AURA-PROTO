/**
 * ============================================================================
 * FILE: setup.js
 * LOCATION: tests/firestore/setup.js
 * ============================================================================
 *
 * PURPOSE:
 *    Jest setup file for Firestore security rules test configuration
 *
 * ROLE IN PROJECT:
 *    Initializes test environment before Firestore security rules tests run.
 *    Configures extended timeout to accommodate Firestore emulator
 *    connection and initialization delays.
 *
 * KEY COMPONENTS:
 *    - jest.setTimeout: Sets 30-second timeout for async emulator operations
 *
 * DEPENDENCIES:
 *    - External: jest (global test framework)
 *    - Internal: Referenced by jest.config.js as setupFilesAfterEnv
 *
 * USAGE:
 *    Automatically loaded by Jest before running Firestore tests.
 *    Configured in: jest.config.js
 * ============================================================================
 */

// Increase timeout for Firestore emulator operations
jest.setTimeout(30000);
