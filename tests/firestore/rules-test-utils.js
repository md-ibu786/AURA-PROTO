/**
 * ============================================================================
 * FILE: rules-test-utils.js
 * LOCATION: tests/firestore/rules-test-utils.js
 * ============================================================================
 *
 * PURPOSE:
 *    Shared utilities for Firestore security rules tests
 *
 * ROLE IN PROJECT:
 *    Provides helper functions to create authenticated contexts,
 *    seed test data, and clean up between tests
 *
 * DEPENDENCIES:
 *    - @firebase/rules-unit-testing
 *    - firebase
 * ============================================================================
 */

const { initializeTestEnvironment } = require('@firebase/rules-unit-testing');
const fs = require('fs');
const path = require('path');

const RULES_FILE_PATH = path.join(__dirname, '..', '..', 'firestore.rules');
const FIREBASE_RC_PATH = path.join(__dirname, '..', '..', '.firebaserc');

function resolveProjectId() {
  if (process.env.GCLOUD_PROJECT) {
    return process.env.GCLOUD_PROJECT;
  }
  if (process.env.FIREBASE_PROJECT) {
    return process.env.FIREBASE_PROJECT;
  }
  if (fs.existsSync(FIREBASE_RC_PATH)) {
    try {
      const firebaseRc = JSON.parse(fs.readFileSync(FIREBASE_RC_PATH, 'utf8'));
      if (firebaseRc.projects && firebaseRc.projects.default) {
        return firebaseRc.projects.default;
      }
    } catch (error) {
      // Ignore malformed .firebaserc and fall back to default.
    }
  }
  return 'demo-aura-notes-manager';
}

const PROJECT_ID = resolveProjectId();

let testEnv = null;

/**
 * Initialize the test environment with Firestore rules
 */
async function initTestEnvironment() {
  if (!testEnv) {
    testEnv = await initializeTestEnvironment({
        projectId: PROJECT_ID,
      firestore: {
        rules: fs.readFileSync(RULES_FILE_PATH, 'utf8'),
      },
    });
  }
  return testEnv;
}

/**
 * Clean up the test environment
 */
async function cleanupTestEnvironment() {
  if (testEnv) {
    await testEnv.cleanup();
    testEnv = null;
  }
}

/**
 * Create an authenticated context for a user
 * @param {string} uid - User ID
 * @param {Object} token - Custom claims (role, etc.)
 * @returns {Object} Authenticated context with firestore()
 */
function createAuthContext(uid, token = {}) {
  return testEnv.authenticatedContext(uid, { status: 'active', ...token });
}

/**
 * Create an unauthenticated context
 * @returns {Object} Unauthenticated context with firestore()
 */
function createUnauthContext() {
  return testEnv.unauthenticatedContext();
}

/**
 * Create test user data
 * @param {Object} overrides - Override default values
 */
function createUserData(overrides = {}) {
  return {
    uid: 'test-user-123',
    email: 'test@aura.edu',
    displayName: 'Test User',
    role: 'student',
    status: 'active',
    departmentId: 'dept-cs',
    subjectIds: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    _v: 0,
    ...overrides,
  };
}

/**
 * Create test note data
 * @param {Object} overrides - Override default values
 */
function createNoteData(overrides = {}) {
  return {
    title: 'Test Note',
    content: 'Test content',
    subjectId: 'sub-math-101',
    departmentId: 'dept-math',
    createdBy: 'test-user-123',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Seed test data into Firestore
 * @param {Object} db - Firestore instance
 * @param {string} collection - Collection name
 * @param {string} docId - Document ID
 * @param {Object} data - Document data
 */
async function seedDocument(db, collection, docId, data) {
  await db.collection(collection).doc(docId).set(data);
}

module.exports = {
  initTestEnvironment,
  cleanupTestEnvironment,
  createAuthContext,
  createUnauthContext,
  createUserData,
  createNoteData,
  seedDocument,
};
