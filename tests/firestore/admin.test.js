/**
 * ============================================================================
 * FILE: admin.test.js
 * LOCATION: tests/firestore/admin.test.js
 * ============================================================================
 *
 * PURPOSE:
 *    Test admin role permissions across all collections
 * ============================================================================
 */

const { assertSucceeds } = require('@firebase/rules-unit-testing');
const {
  initTestEnvironment,
  cleanupTestEnvironment,
  createAuthContext,
  createUserData,
  createNoteData,
  seedDocument,
} = require('./rules-test-utils');

function noteDoc(db, { departmentId, semesterId, subjectId, moduleId, noteId }) {
  return db
    .collection('departments')
    .doc(departmentId)
    .collection('semesters')
    .doc(semesterId)
    .collection('subjects')
    .doc(subjectId)
    .collection('modules')
    .doc(moduleId)
    .collection('notes')
    .doc(noteId);
}

describe('Admin Role', () => {
  let adminContext;
  let adminDb;

  beforeAll(async () => {
    await initTestEnvironment();
    adminContext = createAuthContext('admin-123', { role: 'admin' });
    adminDb = adminContext.firestore();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  beforeEach(async () => {
    const env = await initTestEnvironment();
    await env.clearFirestore();

    await env.withSecurityRulesDisabled(async (context) => {
      await context.firestore().collection('users').doc('admin-123').set(
        createUserData({
          uid: 'admin-123',
          role: 'admin',
          departmentId: null,
          subjectIds: [],
        })
      );
    });
  });

  describe('Users Collection', () => {
    test('admin can list all users', async () => {
      await assertSucceeds(adminDb.collection('users').get());
    });

    test('admin can create users', async () => {
      const userData = createUserData({
        uid: 'new-user-456',
        email: 'new@aura.edu',
        role: 'staff',
        subjectIds: ['sub-math-101'],
      });

      await assertSucceeds(
        adminDb.collection('users').doc('new-user-456').set(userData)
      );
    });

    test('admin can update any user', async () => {
      await seedDocument(adminDb, 'users', 'user-456', createUserData({
        uid: 'user-456',
        status: 'active',
      }));

      await assertSucceeds(
        adminDb.collection('users').doc('user-456').update({ status: 'disabled' })
      );
    });

    test('admin can delete users', async () => {
      await seedDocument(adminDb, 'users', 'user-456', createUserData({
        uid: 'user-456',
      }));

      await assertSucceeds(
        adminDb.collection('users').doc('user-456').delete()
      );
    });
  });

  describe('Notes Collection', () => {
    test('admin can read all notes', async () => {
      const notes = noteDoc(adminDb, {
        departmentId: 'dept-math',
        semesterId: 'sem-1',
        subjectId: 'sub-math-101',
        moduleId: 'mod-1',
        noteId: 'note-1',
      }).parent;

      await assertSucceeds(notes.get());
    });

    test('admin can create notes in any department', async () => {
      const noteData = createNoteData({
        departmentId: 'dept-math',
        subjectId: 'sub-math-101',
      });

      await assertSucceeds(
        noteDoc(adminDb, {
          departmentId: 'dept-math',
          semesterId: 'sem-1',
          subjectId: 'sub-math-101',
          moduleId: 'mod-1',
          noteId: 'note-1',
        }).set(noteData)
      );
    });

    test('admin can update any note', async () => {
      const noteRef = noteDoc(adminDb, {
        departmentId: 'dept-math',
        semesterId: 'sem-1',
        subjectId: 'sub-math-101',
        moduleId: 'mod-1',
        noteId: 'note-1',
      });

      await noteRef.set(createNoteData({
        departmentId: 'dept-math',
        subjectId: 'sub-math-101',
      }));

      await assertSucceeds(noteRef.update({ title: 'Updated' }));
    });

    test('admin can delete any note', async () => {
      const noteRef = noteDoc(adminDb, {
        departmentId: 'dept-math',
        semesterId: 'sem-1',
        subjectId: 'sub-math-101',
        moduleId: 'mod-1',
        noteId: 'note-1',
      });

      await noteRef.set(createNoteData({
        departmentId: 'dept-math',
        subjectId: 'sub-math-101',
      }));

      await assertSucceeds(noteRef.delete());
    });
  });

  describe('Departments Collection', () => {
    test('admin can CRUD departments', async () => {
      await assertSucceeds(
        adminDb.collection('departments').doc('dept-new').set({
          name: 'New Department',
          code: 'NEW',
        })
      );

      await assertSucceeds(
        adminDb.collection('departments').doc('dept-new').update({ name: 'Updated' })
      );

      await assertSucceeds(
        adminDb.collection('departments').doc('dept-new').delete()
      );
    });
  });
});
