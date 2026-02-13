/**
 * ============================================================================
 * FILE: firestore.rules.test.ts
 * LOCATION: frontend/src/tests/firestore.rules.test.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Validate Firestore Security Rules for RBAC with the local emulator.
 *
 * ROLE IN PROJECT:
 *    Provides unit-level coverage for rules enforcement across collections
 *    and edge cases before deployment to production.
 *
 * KEY COMPONENTS:
 *    - Test environment setup: Firebase Emulator rules harness
 *    - Seed helpers: Create baseline users and hierarchy documents
 *    - Collection tests: Users, hierarchy, modules, notes, edge cases
 *
 * DEPENDENCIES:
 *    - External: @firebase/rules-unit-testing, firebase/firestore
 *    - Internal: firestore.rules
 *
 * USAGE:
 *    npm run test:rules
 * ============================================================================
 */

import { assertFails, assertSucceeds, initializeTestEnvironment } from '@firebase/rules-unit-testing';
import type { RulesTestEnvironment } from '@firebase/rules-unit-testing';
import { readFileSync } from 'node:fs';
import * as path from 'node:path';
import {
    collection,
    deleteDoc,
    doc,
    getDoc,
    getDocs,
    query,
    setDoc,
    updateDoc,
    where
} from 'firebase/firestore';
import type { Firestore } from 'firebase/firestore';

type UserRole = 'admin' | 'staff' | 'student';
type UserStatus = 'active' | 'disabled';

type AuthClaims = {
    role: UserRole;
    status: UserStatus;
};

type UserDoc = {
    uid: string;
    email: string;
    displayName?: string;
    role: UserRole;
    status: UserStatus;
    departmentId?: string | null;
    subjectIds?: string[];
    createdAt: string;
    updatedAt: string;
    _v: number;
};

const PROJECT_ID = 'aura-rules-test';
const DEFAULT_TIMESTAMP = '2026-02-05T00:00:00.000Z';

const USERS = {
    admin: 'admin-uid',
    staff: 'staff-uid',
    staffOther: 'staff-other-uid',
    staffNoSubjects: 'staff-nosubjects-uid',
    student: 'student-uid',
    studentOther: 'student-other-uid',
    disabled: 'disabled-uid'
};

const IDS = {
    departmentA: 'dept-a',
    departmentB: 'dept-b',
    semesterA: 'sem-a',
    semesterB: 'sem-b',
    subjectA: 'sub-a',
    subjectB: 'sub-b',
    moduleA: 'mod-a',
    moduleB: 'mod-b',
    noteA: 'note-a',
    noteB: 'note-b'
};

const CLAIMS = {
    admin: { role: 'admin', status: 'active' } satisfies AuthClaims,
    staff: { role: 'staff', status: 'active' } satisfies AuthClaims,
    student: { role: 'student', status: 'active' } satisfies AuthClaims,
    disabled: { role: 'student', status: 'disabled' } satisfies AuthClaims
};

let testEnv: RulesTestEnvironment;

function rulesFilePath(): string {
    return path.resolve(process.cwd(), '..', 'firestore.rules');
}

function userPath(uid: string): string {
    return `users/${uid}`;
}

function departmentPath(departmentId: string): string {
    return `departments/${departmentId}`;
}

function semesterPath(departmentId: string, semesterId: string): string {
    return `${departmentPath(departmentId)}/semesters/${semesterId}`;
}

function subjectPath(
    departmentId: string,
    semesterId: string,
    subjectId: string
): string {
    return `${semesterPath(departmentId, semesterId)}/subjects/${subjectId}`;
}

function modulePath(
    departmentId: string,
    semesterId: string,
    subjectId: string,
    moduleId: string
): string {
    return `${subjectPath(departmentId, semesterId, subjectId)}/modules/${moduleId}`;
}

function notesCollectionPath(
    departmentId: string,
    semesterId: string,
    subjectId: string,
    moduleId: string
): string {
    return `${modulePath(departmentId, semesterId, subjectId, moduleId)}/notes`;
}

function notePath(
    departmentId: string,
    semesterId: string,
    subjectId: string,
    moduleId: string,
    noteId: string
): string {
    return `${notesCollectionPath(departmentId, semesterId, subjectId, moduleId)}/${noteId}`;
}

function getFirestore(uid: string, claims: AuthClaims): Firestore {
    return testEnv.authenticatedContext(uid, claims).firestore();
}

function getAdminFirestore(): Firestore {
    return getFirestore(USERS.admin, CLAIMS.admin);
}

function getStaffFirestore(): Firestore {
    return getFirestore(USERS.staff, CLAIMS.staff);
}

function getOtherStaffFirestore(): Firestore {
    return getFirestore(USERS.staffOther, CLAIMS.staff);
}

function getStudentFirestore(): Firestore {
    return getFirestore(USERS.student, CLAIMS.student);
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function getOtherStudentFirestore(): Firestore {
    return getFirestore(USERS.studentOther, CLAIMS.student);
}

function getDisabledFirestore(): Firestore {
    return getFirestore(USERS.disabled, CLAIMS.disabled);
}

function getUnauthenticatedFirestore(): Firestore {
    return testEnv.unauthenticatedContext().firestore();
}

function buildUserDoc(params: {
    uid: string;
    role: UserRole;
    status: UserStatus;
    departmentId?: string | null;
    subjectIds?: string[];
}): UserDoc {
    return {
        uid: params.uid,
        email: `${params.uid}@example.com`,
        displayName: `User ${params.uid}`,
        role: params.role,
        status: params.status,
        departmentId: params.departmentId ?? null,
        subjectIds: params.subjectIds ?? [],
        createdAt: DEFAULT_TIMESTAMP,
        updatedAt: DEFAULT_TIMESTAMP,
        _v: 1
    };
}

async function seedBaseData(): Promise<void> {
    await testEnv.withSecurityRulesDisabled(async context => {
        const db = context.firestore();

        await setDoc(doc(db, departmentPath(IDS.departmentA)), {
            name: 'Engineering',
            code: 'ENG'
        });
        await setDoc(doc(db, departmentPath(IDS.departmentB)), {
            name: 'Science',
            code: 'SCI'
        });

        await setDoc(doc(db, semesterPath(IDS.departmentA, IDS.semesterA)), {
            name: 'Semester 1',
            semesterNumber: 1
        });
        await setDoc(doc(db, semesterPath(IDS.departmentB, IDS.semesterB)), {
            name: 'Semester 1',
            semesterNumber: 1
        });

        await setDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA)), {
            name: 'Mathematics',
            code: 'MATH-101'
        });
        await setDoc(doc(db, subjectPath(IDS.departmentB, IDS.semesterB, IDS.subjectB)), {
            name: 'Chemistry',
            code: 'CHEM-101'
        });

        await setDoc(
            doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)),
            {
                name: 'Module 1',
                moduleNumber: 1
            }
        );
        await setDoc(
            doc(db, modulePath(IDS.departmentB, IDS.semesterB, IDS.subjectB, IDS.moduleB)),
            {
                name: 'Module 1',
                moduleNumber: 1
            }
        );

        await setDoc(
            doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
            {
                title: 'Intro Note',
                module_id: IDS.moduleA,
                created_at: DEFAULT_TIMESTAMP,
                subjectId: IDS.subjectA,
                departmentId: IDS.departmentA
            }
        );
        await setDoc(
            doc(db, notePath(IDS.departmentB, IDS.semesterB, IDS.subjectB, IDS.moduleB, IDS.noteB)),
            {
                title: 'Other Note',
                module_id: IDS.moduleB,
                created_at: DEFAULT_TIMESTAMP,
                subjectId: IDS.subjectB,
                departmentId: IDS.departmentB
            }
        );

        await setDoc(
            doc(db, userPath(USERS.admin)),
            buildUserDoc({ uid: USERS.admin, role: 'admin', status: 'active' })
        );
        await setDoc(
            doc(db, userPath(USERS.staff)),
            buildUserDoc({
                uid: USERS.staff,
                role: 'staff',
                status: 'active',
                departmentId: IDS.departmentA,
                subjectIds: [IDS.subjectA]
            })
        );
        await setDoc(
            doc(db, userPath(USERS.staffOther)),
            buildUserDoc({
                uid: USERS.staffOther,
                role: 'staff',
                status: 'active',
                departmentId: IDS.departmentB,
                subjectIds: [IDS.subjectB]
            })
        );
        await setDoc(
            doc(db, userPath(USERS.staffNoSubjects)),
            buildUserDoc({
                uid: USERS.staffNoSubjects,
                role: 'staff',
                status: 'active',
                departmentId: IDS.departmentA,
                subjectIds: []
            })
        );
        await setDoc(
            doc(db, userPath(USERS.student)),
            buildUserDoc({
                uid: USERS.student,
                role: 'student',
                status: 'active',
                departmentId: IDS.departmentA,
                subjectIds: []
            })
        );
        await setDoc(
            doc(db, userPath(USERS.studentOther)),
            buildUserDoc({
                uid: USERS.studentOther,
                role: 'student',
                status: 'active',
                departmentId: IDS.departmentB,
                subjectIds: []
            })
        );
        await setDoc(
            doc(db, userPath(USERS.disabled)),
            buildUserDoc({
                uid: USERS.disabled,
                role: 'student',
                status: 'disabled',
                departmentId: IDS.departmentA,
                subjectIds: []
            })
        );
    });
}

beforeAll(async () => {
    const rules = readFileSync(rulesFilePath(), 'utf8');
    testEnv = await initializeTestEnvironment({
        projectId: PROJECT_ID,
        firestore: {
            rules
        }
    });
});

beforeEach(async () => {
    await testEnv.clearFirestore();
    await seedBaseData();
});

afterAll(async () => {
    await testEnv.cleanup();
});

describe('users collection rules', () => {
    it('allows users to read their own document', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(getDoc(doc(db, userPath(USERS.student))));
    });

    it('denies users from reading other users', async () => {
        const db = getStudentFirestore();
        await assertFails(getDoc(doc(db, userPath(USERS.staff))));
    });

    it('allows admins to read any user document', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(getDoc(doc(db, userPath(USERS.student))));
    });

    it('denies non-admins from creating user documents', async () => {
        const db = getStaffFirestore();
        const newUserId = 'new-user-1';
        await assertFails(
            setDoc(
                doc(db, userPath(newUserId)),
                buildUserDoc({
                    uid: newUserId,
                    role: 'student',
                    status: 'active',
                    departmentId: IDS.departmentA,
                    subjectIds: []
                })
            )
        );
    });

    it('allows admins to create user documents', async () => {
        const db = getAdminFirestore();
        const newUserId = 'new-user-2';
        await assertSucceeds(
            setDoc(
                doc(db, userPath(newUserId)),
                buildUserDoc({
                    uid: newUserId,
                    role: 'student',
                    status: 'active',
                    departmentId: IDS.departmentA,
                    subjectIds: []
                })
            )
        );
    });

    it('denies non-admins from updating user documents', async () => {
        const db = getStaffFirestore();
        await assertFails(updateDoc(doc(db, userPath(USERS.student)), { displayName: 'Nope' }));
    });

    it('allows admins to update user documents', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(updateDoc(doc(db, userPath(USERS.student)), { displayName: 'Updated' }));
    });

    it('denies non-admins from deleting user documents', async () => {
        const db = getStaffFirestore();
        await assertFails(deleteDoc(doc(db, userPath(USERS.student))));
    });

    it('allows admins to delete user documents', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(deleteDoc(doc(db, userPath(USERS.studentOther))));
    });
});

describe('department rules', () => {
    it('allows authenticated users to read departments', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(getDoc(doc(db, departmentPath(IDS.departmentA))));
    });

    it('denies unauthenticated users from reading departments', async () => {
        const db = getUnauthenticatedFirestore();
        await assertFails(getDoc(doc(db, departmentPath(IDS.departmentA))));
    });

    it('allows admins to create departments', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            setDoc(doc(db, departmentPath('dept-new')), {
                name: 'Business',
                code: 'BUS'
            })
        );
    });

    it('denies staff from creating departments', async () => {
        const db = getStaffFirestore();
        await assertFails(
            setDoc(doc(db, departmentPath('dept-new')), {
                name: 'Business',
                code: 'BUS'
            })
        );
    });

    it('allows admins to update departments', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(updateDoc(doc(db, departmentPath(IDS.departmentA)), { name: 'Eng' }));
    });

    it('denies staff from updating departments', async () => {
        const db = getStaffFirestore();
        await assertFails(updateDoc(doc(db, departmentPath(IDS.departmentA)), { name: 'Eng' }));
    });
});

describe('semester rules', () => {
    it('allows authenticated users to read semesters', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(getDoc(doc(db, semesterPath(IDS.departmentA, IDS.semesterA))));
    });

    it('denies unauthenticated users from reading semesters', async () => {
        const db = getUnauthenticatedFirestore();
        await assertFails(getDoc(doc(db, semesterPath(IDS.departmentA, IDS.semesterA))));
    });

    it('allows admins to create semesters', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            setDoc(doc(db, semesterPath(IDS.departmentA, 'sem-new')), {
                name: 'Semester 2',
                semesterNumber: 2
            })
        );
    });

    it('denies staff from creating semesters', async () => {
        const db = getStaffFirestore();
        await assertFails(
            setDoc(doc(db, semesterPath(IDS.departmentA, 'sem-new')), {
                name: 'Semester 2',
                semesterNumber: 2
            })
        );
    });

    it('allows admins to update semesters', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            updateDoc(doc(db, semesterPath(IDS.departmentA, IDS.semesterA)), { name: 'Sem 1' })
        );
    });

    it('denies staff from updating semesters', async () => {
        const db = getStaffFirestore();
        await assertFails(
            updateDoc(doc(db, semesterPath(IDS.departmentA, IDS.semesterA)), { name: 'Sem 1' })
        );
    });
});

describe('subject rules', () => {
    it('allows authenticated users to read subjects', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(getDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA))));
    });

    it('denies unauthenticated users from reading subjects', async () => {
        const db = getUnauthenticatedFirestore();
        await assertFails(getDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA))));
    });

    it('allows admins to create subjects', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            setDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, 'sub-new')), {
                name: 'Physics',
                code: 'PHY-101'
            })
        );
    });

    it('denies staff from creating subjects', async () => {
        const db = getStaffFirestore();
        await assertFails(
            setDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, 'sub-new')), {
                name: 'Physics',
                code: 'PHY-101'
            })
        );
    });

    it('allows admins to update subjects', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            updateDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA)), {
                name: 'Advanced Math'
            })
        );
    });

    it('allows staff to update assigned subjects', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            updateDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA)), {
                name: 'Updated Math'
            })
        );
    });

    it('denies staff from updating unassigned subjects', async () => {
        const db = getOtherStaffFirestore();
        await assertFails(
            updateDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA)), {
                name: 'No Access'
            })
        );
    });

    it('denies students from updating subjects', async () => {
        const db = getStudentFirestore();
        await assertFails(
            updateDoc(doc(db, subjectPath(IDS.departmentA, IDS.semesterA, IDS.subjectA)), {
                name: 'No Access'
            })
        );
    });
});

describe('module rules', () => {
    it('allows authenticated users to read modules', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(
            getDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)))
        );
    });

    it('denies unauthenticated users from reading modules', async () => {
        const db = getUnauthenticatedFirestore();
        await assertFails(
            getDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)))
        );
    });

    it('allows staff to create modules in assigned subjects', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            setDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, 'mod-new')), {
                name: 'Module 2',
                moduleNumber: 2
            })
        );
    });

    it('denies staff from creating modules in unassigned subjects', async () => {
        const db = getOtherStaffFirestore();
        await assertFails(
            setDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, 'mod-new')), {
                name: 'Module 2',
                moduleNumber: 2
            })
        );
    });

    it('denies admins from creating modules', async () => {
        const db = getAdminFirestore();
        await assertFails(
            setDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, 'mod-new')), {
                name: 'Module 2',
                moduleNumber: 2
            })
        );
    });

    it('denies students from creating modules', async () => {
        const db = getStudentFirestore();
        await assertFails(
            setDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, 'mod-new')), {
                name: 'Module 2',
                moduleNumber: 2
            })
        );
    });

    it('allows staff to update modules in assigned subjects', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            updateDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)), {
                name: 'Module 1 Updated'
            })
        );
    });

    it('denies staff from updating modules in unassigned subjects', async () => {
        const db = getOtherStaffFirestore();
        await assertFails(
            updateDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)), {
                name: 'Module 1 Updated'
            })
        );
    });

    it('denies admins from updating modules', async () => {
        const db = getAdminFirestore();
        await assertFails(
            updateDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)), {
                name: 'Module 1 Updated'
            })
        );
    });

    it('allows admins to delete modules', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            deleteDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)))
        );
    });

    it('denies staff from deleting modules', async () => {
        const db = getStaffFirestore();
        await assertFails(
            deleteDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)))
        );
    });
});

describe('notes rules', () => {
    it('allows admins to read any notes', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            getDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)))
        );
    });

    it('allows staff to read notes in assigned subjects', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            getDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)))
        );
    });

    it('allows students to read notes in their department', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(
            getDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)))
        );
    });

    it('denies students from reading notes outside their department', async () => {
        const db = getStudentFirestore();
        await assertFails(
            getDoc(doc(db, notePath(IDS.departmentB, IDS.semesterB, IDS.subjectB, IDS.moduleB, IDS.noteB)))
        );
    });

    it('allows staff to create notes in assigned subjects', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            setDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, 'note-new')), {
                title: 'New Note',
                module_id: IDS.moduleA,
                created_at: DEFAULT_TIMESTAMP,
                subjectId: IDS.subjectA,
                departmentId: IDS.departmentA
            })
        );
    });

    it('denies staff from creating notes in unassigned subjects', async () => {
        const db = getOtherStaffFirestore();
        await assertFails(
            setDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, 'note-new')), {
                title: 'New Note',
                module_id: IDS.moduleA,
                created_at: DEFAULT_TIMESTAMP,
                subjectId: IDS.subjectA,
                departmentId: IDS.departmentA
            })
        );
    });

    it('denies admins from creating notes', async () => {
        const db = getAdminFirestore();
        await assertFails(
            setDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, 'note-new')), {
                title: 'New Note',
                module_id: IDS.moduleA,
                created_at: DEFAULT_TIMESTAMP,
                subjectId: IDS.subjectA,
                departmentId: IDS.departmentA
            })
        );
    });

    it('denies students from creating notes', async () => {
        const db = getStudentFirestore();
        await assertFails(
            setDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, 'note-new')), {
                title: 'New Note',
                module_id: IDS.moduleA,
                created_at: DEFAULT_TIMESTAMP,
                subjectId: IDS.subjectA,
                departmentId: IDS.departmentA
            })
        );
    });

    it('allows staff to update notes in assigned subjects', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            updateDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
                { title: 'Updated Note' }
            )
        );
    });

    it('denies staff from updating notes in unassigned subjects', async () => {
        const db = getOtherStaffFirestore();
        await assertFails(
            updateDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
                { title: 'Updated Note' }
            )
        );
    });

    it('denies admins from updating notes', async () => {
        const db = getAdminFirestore();
        await assertFails(
            updateDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
                { title: 'Updated Note' }
            )
        );
    });

    it('allows admins to delete notes', async () => {
        const db = getAdminFirestore();
        await assertSucceeds(
            deleteDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA))
            )
        );
    });

    it('denies staff from deleting notes', async () => {
        const db = getStaffFirestore();
        await assertFails(
            deleteDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA))
            )
        );
    });
});

describe('edge cases and validation', () => {
    it('denies disabled users from reading data', async () => {
        const db = getDisabledFirestore();
        await assertFails(getDoc(doc(db, departmentPath(IDS.departmentA))));
    });

    it('denies disabled users from writing data', async () => {
        const db = getDisabledFirestore();
        await assertFails(
            setDoc(doc(db, departmentPath('dept-disabled')), {
                name: 'Disabled Dept',
                code: 'DIS'
            })
        );
    });

    it('denies staff without subjectIds from writing modules', async () => {
        const db = getFirestore(USERS.staffNoSubjects, CLAIMS.staff);
        await assertFails(
            setDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, 'mod-new')), {
                name: 'Module 2',
                moduleNumber: 2
            })
        );
    });

    it('allows users without departmentId to read departments', async () => {
        const db = getFirestore('staff-nodept', CLAIMS.staff);
        await testEnv.withSecurityRulesDisabled(async context => {
            await setDoc(
                doc(context.firestore(), userPath('staff-nodept')),
                buildUserDoc({
                    uid: 'staff-nodept',
                    role: 'staff',
                    status: 'active',
                    departmentId: null,
                    subjectIds: []
                })
            );
        });
        await assertSucceeds(getDoc(doc(db, departmentPath(IDS.departmentA))));
    });

    it('rejects invalid department data', async () => {
        const db = getAdminFirestore();
        await assertFails(
            setDoc(doc(db, departmentPath('dept-invalid')), {
                code: 'BAD'
            })
        );
    });

    it('rejects invalid module data types', async () => {
        const db = getStaffFirestore();
        await assertFails(
            setDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, 'mod-bad')), {
                name: 'Bad Module',
                moduleNumber: 'one'
            })
        );
    });

    it('rejects notes missing required fields', async () => {
        const db = getStaffFirestore();
        await assertFails(
            setDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, 'note-bad')), {
                title: 'Incomplete Note',
                module_id: IDS.moduleA
            })
        );
    });

    it('rejects notes with invalid field types', async () => {
        const db = getStaffFirestore();
        await assertFails(
            setDoc(doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, 'note-bad')), {
                title: 'Bad Note',
                module_id: IDS.moduleA,
                created_at: 123
            })
        );
    });

    it('fails queries for notes outside the user department', async () => {
        const db = getStudentFirestore();
        await assertFails(
            getDocs(
                collection(
                    db,
                    notesCollectionPath(
                        IDS.departmentB,
                        IDS.semesterB,
                        IDS.subjectB,
                        IDS.moduleB
                    )
                )
            )
        );
    });

    it('allows queries for notes in the user department', async () => {
        const db = getStudentFirestore();
        const scopedQuery = query(
            collection(db, notesCollectionPath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)),
            where('departmentId', '==', IDS.departmentA)
        );
        await assertSucceeds(getDocs(scopedQuery));
    });

    it('denies staff from updating notes in another subject', async () => {
        const db = getOtherStaffFirestore();
        await assertFails(
            updateDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
                { title: 'Not Allowed' }
            )
        );
    });

    it('allows staff to update notes in assigned subject', async () => {
        const db = getStaffFirestore();
        await assertSucceeds(
            updateDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
                { title: 'Allowed Update' }
            )
        );
    });

    it('denies unauthenticated users from reading users list', async () => {
        const db = getUnauthenticatedFirestore();
        const usersCollection = collection(db, 'users');
        await assertFails(getDocs(usersCollection));
    });

    it('allows admins to list users', async () => {
        const db = getAdminFirestore();
        const usersCollection = collection(db, 'users');
        await assertSucceeds(getDocs(usersCollection));
    });

    it('denies students from listing users', async () => {
        const db = getStudentFirestore();
        const usersCollection = collection(db, 'users');
        await assertFails(getDocs(usersCollection));
    });

    it('allows staff to read their own user document even without departmentId', async () => {
        const db = getFirestore('staff-nodept', CLAIMS.staff);
        await assertSucceeds(getDoc(doc(db, userPath('staff-nodept'))));
    });

    it('denies staff without subject access from updating modules', async () => {
        const db = getFirestore(USERS.staffNoSubjects, CLAIMS.staff);
        await assertFails(
            updateDoc(doc(db, modulePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA)), {
                name: 'No Access'
            })
        );
    });

    it('denies staff without subject access from updating notes', async () => {
        const db = getFirestore(USERS.staffNoSubjects, CLAIMS.staff);
        await assertFails(
            updateDoc(
                doc(db, notePath(IDS.departmentA, IDS.semesterA, IDS.subjectA, IDS.moduleA, IDS.noteA)),
                { title: 'No Access' }
            )
        );
    });

    it('denies unauthenticated users from listing departments', async () => {
        const db = getUnauthenticatedFirestore();
        await assertFails(getDocs(collection(db, 'departments')));
    });

    it('allows authenticated users to list departments', async () => {
        const db = getStudentFirestore();
        await assertSucceeds(getDocs(collection(db, 'departments')));
    });
});
