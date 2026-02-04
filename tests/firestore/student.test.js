/**
 * ============================================================================
 * FILE: student.test.js
 * LOCATION: tests/firestore/student.test.js
 * ============================================================================
 *
 * PURPOSE:
 *    Test student role permissions (read-only, department-based)
 *    and edge cases
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

function subjectsCollection(db, { departmentId, semesterId }) {
  return db
    .collection('departments')
    .doc(departmentId)
    .collection('semesters')
    .doc(semesterId)
    .collection('subjects');
}

describe('Student Role', () => {
  const studentUid = 'student-123';
  const studentDeptId = 'dept-cs';
  const otherDeptId = 'dept-math';

  let testEnv;
  let studentContext;
  let studentDb;

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
      await seedDocument(db, 'users', studentUid, createUserData({
        uid: studentUid,
        role: 'student',
        departmentId: studentDeptId,
        subjectIds: [],
      }));
    });

    studentContext = createAuthContext(studentUid, { role: 'student' });
    studentDb = studentContext.firestore();
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  describe('Read Access', () => {
    test('student can read notes in their department', async () => {
      const notePath = noteDoc(studentDb, {
        departmentId: studentDeptId,
        semesterId: 'sem-1',
        subjectId: 'sub-cs-101',
        moduleId: 'mod-1',
        noteId: 'note-1',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(notePath).set(createNoteData({
          departmentId: studentDeptId,
          subjectId: 'sub-cs-101',
        }));
      });

      await assertSucceeds(studentDb.doc(notePath).get());
    });

    test('student can read departments', async () => {
      await assertSucceeds(studentDb.collection('departments').get());
    });

    test('student can read subjects', async () => {
      await assertSucceeds(subjectsCollection(studentDb, {
        departmentId: studentDeptId,
        semesterId: 'sem-1',
      }).get());
    });
  });

  describe('Cross-Department Access Denied', () => {
    test('student cannot read notes from other departments', async () => {
      const notePath = noteDoc(studentDb, {
        departmentId: otherDeptId,
        semesterId: 'sem-1',
        subjectId: 'sub-math-101',
        moduleId: 'mod-1',
        noteId: 'note-2',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(notePath).set(createNoteData({
          departmentId: otherDeptId,
          subjectId: 'sub-math-101',
        }));
      });

      await assertFails(studentDb.doc(notePath).get());
    });
  });

  describe('Write Access Denied', () => {
    test('student cannot create notes', async () => {
      await assertFails(
        noteDoc(studentDb, {
          departmentId: studentDeptId,
          semesterId: 'sem-1',
          subjectId: 'sub-cs-101',
          moduleId: 'mod-1',
          noteId: 'note-new',
        }).set(createNoteData({
          departmentId: studentDeptId,
          subjectId: 'sub-cs-101',
        }))
      );
    });

    test('student cannot update notes', async () => {
      const notePath = noteDoc(studentDb, {
        departmentId: studentDeptId,
        semesterId: 'sem-1',
        subjectId: 'sub-cs-101',
        moduleId: 'mod-1',
        noteId: 'note-1',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(notePath).set(createNoteData({
          departmentId: studentDeptId,
          subjectId: 'sub-cs-101',
        }));
      });

      await assertFails(
        studentDb.doc(notePath).update({ title: 'Hacked' })
      );
    });

    test('student cannot delete notes', async () => {
      const notePath = noteDoc(studentDb, {
        departmentId: studentDeptId,
        semesterId: 'sem-1',
        subjectId: 'sub-cs-101',
        moduleId: 'mod-1',
        noteId: 'note-1',
      }).path;

      await testEnv.withSecurityRulesDisabled(async (context) => {
        await context.firestore().doc(notePath).set(createNoteData({
          departmentId: studentDeptId,
          subjectId: 'sub-cs-101',
        }));
      });

      await assertFails(studentDb.doc(notePath).delete());
    });

    test('student cannot modify departments', async () => {
      await assertFails(
        studentDb.collection('departments').doc('dept-cs').update({ name: 'Hacked' })
      );
    });
  });
});

describe('Edge Cases', () => {
  let testEnv;

  beforeAll(async () => {
    testEnv = await initTestEnvironment();
  });

  beforeEach(async () => {
    testEnv = await initTestEnvironment();
    await testEnv.clearFirestore();

    await testEnv.withSecurityRulesDisabled(async (context) => {
      await seedDocument(context.firestore(), 'users', 'admin-123', createUserData({
        uid: 'admin-123',
        role: 'admin',
        departmentId: null,
        subjectIds: [],
      }));
    });
  });

  afterAll(async () => {
    await cleanupTestEnvironment();
  });

  test('disabled user cannot access data', async () => {
    await testEnv.withSecurityRulesDisabled(async (context) => {
      await seedDocument(context.firestore(), 'users', 'disabled-user', createUserData({
        uid: 'disabled-user',
        role: 'student',
        status: 'disabled',
        departmentId: 'dept-cs',
        subjectIds: [],
      }));
    });

    const disabledContext = createAuthContext('disabled-user', {
      role: 'student',
      status: 'disabled',
    });
    const disabledDb = disabledContext.firestore();

    await assertFails(disabledDb.collection('departments').get());
  });

  test('user without role claim cannot access admin data', async () => {
    await testEnv.withSecurityRulesDisabled(async (context) => {
      await seedDocument(context.firestore(), 'users', 'user-no-role', createUserData({
        uid: 'user-no-role',
        role: 'student',
        departmentId: 'dept-cs',
        subjectIds: [],
      }));
    });

    const noRoleContext = createAuthContext('user-no-role', {});
    const noRoleDb = noRoleContext.firestore();

    await assertFails(noRoleDb.collection('users').get());
  });
});
