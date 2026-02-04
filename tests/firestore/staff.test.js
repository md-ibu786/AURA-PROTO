/**
 * ============================================================================
 * FILE: staff.test.js
 * LOCATION: tests/firestore/staff.test.js
 * ============================================================================
 *
 * PURPOSE:
 *    Test staff role permissions with subject access control
 * ============================================================================
 */

const { assertFails, assertSucceeds } = require('@firebase/rules-unit-testing');
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

describe('Staff Role', () => {
  const staffUid = 'staff-123';
  const staffSubjectId = 'sub-math-101';
  const otherSubjectId = 'sub-physics-101';
  const staffDeptId = 'dept-math';

  let testEnv;
  let staffContext;
  let staffDb;

  beforeAll(async () => {
    testEnv = await initTestEnvironment();
  });

  beforeEach(async () => {
    testEnv = await initTestEnvironment();
    await testEnv.clearFirestore();

    await testEnv.withSecurityRulesDisabled(async (context) => {
      const db = context.firestore();
      await seedDocument(db, 'users', 'admin-123', createUserData({
        uid: 'admin-123',
        role: 'admin',
        departmentId: null,
        subjectIds: [],
      }));
      await seedDocument(db, 'users', staffUid, createUserData({
        uid: staffUid,
        role: 'staff',
        subjectIds: [staffSubjectId],
        departmentId: staffDeptId,
      }));
    });

    staffContext = createAuthContext(staffUid, { role: 'staff' });
    staffDb = staffContext.firestore();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('User Management', () => {
    test('staff can read their own user document', async () => {
      await assertSucceeds(staffDb.collection('users').doc(staffUid).get());
    });

    test('staff cannot list all users', async () => {
      await assertFails(staffDb.collection('users').get());
    });

    test('staff cannot create users', async () => {
      await assertFails(
        staffDb.collection('users').doc('new-user').set(createUserData())
      );
    });

    test('staff cannot update other users', async () => {
      await testEnv.withSecurityRulesDisabled(async (context) => {
        await seedDocument(context.firestore(), 'users', 'other-user', createUserData({
          uid: 'other-user',
        }));
      });

      await assertFails(
        staffDb.collection('users').doc('other-user').update({ status: 'disabled' })
      );
    });
  });

  describe('Notes - Assigned Subjects', () => {
    test('staff can read notes in assigned subjects', async () => {
      const notePath = noteDoc(staffDb, {
        departmentId: staffDeptId,
        semesterId: 'sem-1',
        subjectId: staffSubjectId,
        moduleId: 'mod-1',
        noteId: 'note-1',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(notePath).set(createNoteData({
          subjectId: staffSubjectId,
          departmentId: staffDeptId,
        }));
      });

      await assertSucceeds(staffDb.doc(notePath).get());
    });

    test('staff can create notes in assigned subjects', async () => {
      const noteData = createNoteData({
        subjectId: staffSubjectId,
        departmentId: staffDeptId,
      });

      await assertSucceeds(
        noteDoc(staffDb, {
          departmentId: staffDeptId,
          semesterId: 'sem-1',
          subjectId: staffSubjectId,
          moduleId: 'mod-1',
          noteId: 'note-1',
        }).set(noteData)
      );
    });

    test('staff can update notes in assigned subjects', async () => {
      const notePath = noteDoc(staffDb, {
        departmentId: staffDeptId,
        semesterId: 'sem-1',
        subjectId: staffSubjectId,
        moduleId: 'mod-1',
        noteId: 'note-1',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(notePath).set(createNoteData({
          subjectId: staffSubjectId,
          departmentId: staffDeptId,
        }));
      });

      await assertSucceeds(
        staffDb.doc(notePath).update({ title: 'Updated' })
      );
    });
  });

  describe('Notes - Other Subjects', () => {
    test('staff cannot read notes in unassigned subjects', async () => {
      const otherNotePath = noteDoc(staffDb, {
        departmentId: 'dept-physics',
        semesterId: 'sem-1',
        subjectId: otherSubjectId,
        moduleId: 'mod-1',
        noteId: 'note-2',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(otherNotePath).set(createNoteData({
          subjectId: otherSubjectId,
          departmentId: 'dept-physics',
        }));
      });

      await assertFails(staffDb.doc(otherNotePath).get());
    });

    test('staff cannot create notes in unassigned subjects', async () => {
      const noteData = createNoteData({
        subjectId: otherSubjectId,
        departmentId: 'dept-physics',
      });

      await assertFails(
        noteDoc(staffDb, {
          departmentId: 'dept-physics',
          semesterId: 'sem-1',
          subjectId: otherSubjectId,
          moduleId: 'mod-1',
          noteId: 'note-2',
        }).set(noteData)
      );
    });
  });

  describe('Departments', () => {
    test('staff can read departments', async () => {
      await assertSucceeds(staffDb.collection('departments').get());
    });

    test('staff cannot modify departments', async () => {
      await assertFails(
        staffDb.collection('departments').doc('dept-new').set({ name: 'New' })
      );
    });
  });
});
