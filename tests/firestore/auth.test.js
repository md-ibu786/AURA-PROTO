/**
 * ============================================================================
 * FILE: auth.test.js
 * LOCATION: tests/firestore/auth.test.js
 * ============================================================================
 *
 * PURPOSE:
 *    Test authentication requirements for Firestore access
 *
 * ROLE IN PROJECT:
 *    Verifies that unauthenticated users cannot access any data
 * ============================================================================
 */

const { assertFails, assertSucceeds } = require('@firebase/rules-unit-testing');
const {
  initTestEnvironment,
  cleanupTestEnvironment,
  createAuthContext,
  createUnauthContext,
  createUserData,
} = require('./rules-test-utils');

function notesCollection(db) {
  return db
    .collection('departments')
    .doc('dept-cs')
    .collection('semesters')
    .doc('sem-1')
    .collection('subjects')
    .doc('sub-cs-101')
    .collection('modules')
    .doc('mod-1')
    .collection('notes');
}

function subjectsCollection(db) {
  return db
    .collection('departments')
    .doc('dept-cs')
    .collection('semesters')
    .doc('sem-1')
    .collection('subjects');
}

describe('Authentication', () => {
  beforeAll(async () => {
    await initTestEnvironment();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  beforeEach(async () => {
    const env = await initTestEnvironment();
    await env.clearFirestore();

    await env.withSecurityRulesDisabled(async (context) => {
      await context.firestore().collection('users').doc('user-123').set(
        createUserData({
          uid: 'user-123',
          role: 'student',
        })
      );
    });
  });

  test('unauthenticated users cannot read users collection', async () => {
    const unauth = createUnauthContext();
    const db = unauth.firestore();

    await assertFails(db.collection('users').get());
  });

  test('unauthenticated users cannot read departments', async () => {
    const unauth = createUnauthContext();
    const db = unauth.firestore();

    await assertFails(db.collection('departments').get());
  });

  test('unauthenticated users cannot read notes', async () => {
    const unauth = createUnauthContext();
    const db = unauth.firestore();

    await assertFails(notesCollection(db).get());
  });

  test('authenticated users can read departments', async () => {
    const auth = createAuthContext('user-123', { role: 'student' });
    const db = auth.firestore();

    await assertSucceeds(db.collection('departments').get());
  });

  test('authenticated users can read subjects', async () => {
    const auth = createAuthContext('user-123', { role: 'student' });
    const db = auth.firestore();

    await assertSucceeds(subjectsCollection(db).get());
  });
});
