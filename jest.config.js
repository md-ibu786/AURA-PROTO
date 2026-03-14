/**
 * ============================================================================
 * FILE: jest.config.js
 * LOCATION: jest.config.js
 * ============================================================================
 *
 * PURPOSE:
 *    Jest configuration for Firestore security rules testing
 *
 * ROLE IN PROJECT:
 *    Configures Jest test runner specifically for Firestore emulator tests.
 *    Runs security rules tests against Firebase emulator to validate
 *    database access controls and permissions.
 *
 * KEY COMPONENTS:
 *    - testEnvironment: Node.js environment for Firestore testing
 *    - testMatch: Pattern to match Firestore test files
 *    - setupFilesAfterEnv: Setup script for test environment preparation
 *    - maxWorkers: Single worker to prevent emulator conflicts
 *
 * DEPENDENCIES:
 *    - External: jest, @firebase/rules-unit-testing
 *    - Internal: tests/firestore/setup.js (test setup and configuration)
 *
 * USAGE:
 *    Run with: npm test -- tests/firestore/
 *    Or: jest tests/firestore/
 * ============================================================================
 */

module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/tests/firestore/**/*.test.js'],
  setupFilesAfterEnv: ['./tests/firestore/setup.js'],
  testTimeout: 30000,
  maxWorkers: 1,
};
