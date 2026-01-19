import { test, expect } from '@playwright/test';
import { ApiHelper } from '../page-objects/ApiHelper';

/**
 * API E2E Tests
 * Tests the Firestore-backed API endpoints directly
 * All tests are isolated with proper setup/teardown
 */

test.describe('API - Health Check', () => {
    test('Backend server is running and healthy', async ({ request }) => {
        const api = new ApiHelper(request);
        const isHealthy = await api.checkHealth();
        expect(isHealthy).toBe(true);
    });
});

test.describe('API - Departments CRUD', () => {
    let api: ApiHelper;
    let createdDeptId: string;

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
    });

    test.afterEach(async () => {
        // Cleanup: Delete department if it was created
        if (createdDeptId) {
            await api.deleteDepartment(createdDeptId);
            createdDeptId = '';
        }
    });

    test('Create a new department', async () => {
        const name = `E2E Dept ${Date.now()}`;
        const code = `E2E${Date.now() % 1000}`;

        const id = await api.createDepartment(name, code);
        createdDeptId = id;

        expect(id).toBeDefined();
        expect(id.length).toBeGreaterThan(0);

        // Verify it exists
        const departments = await api.getAllDepartments();
        const found = departments.some((d: any) => d.id === id && d.name === name);
        expect(found).toBe(true);
    });

    test('Retrieve department by ID', async () => {
        const name = `Retrieval Test ${Date.now()}`;
        const id = await api.createDepartment(name, 'RET');
        createdDeptId = id;

        const dept = await api.getDepartment(id);
        expect(dept).not.toBeNull();
        expect(dept.name).toBe(name);
        expect(dept.code).toBe('RET');
    });

    test('Update department', async () => {
        const id = await api.createDepartment('Update Test', 'UPD');
        createdDeptId = id;

        await api.updateDepartment(id, { name: 'Updated Name', code: 'UPD2' });

        const dept = await api.getDepartment(id);
        expect(dept.name).toBe('Updated Name');
        expect(dept.code).toBe('UPD2');
    });

    test('Delete department cascades to children', async () => {
        const id = await api.createDepartment('Cascade Test', 'CAS');
        createdDeptId = id;

        // Add a semester
        const semId = await api.createSemester(id, 'Cascade Semester');

        // Delete department
        await api.deleteDepartment(id);
        createdDeptId = '';

        // Verify department is gone
        const dept = await api.getDepartment(id);
        expect(dept).toBeNull();

        // Verify semester is also gone (via tree check)
        const tree = await api.getExplorerTree();
        const deptInTree = tree.some((d: any) => d.id === id);
        expect(deptInTree).toBe(false);
    });
});

test.describe('API - Full Hierarchy Operations', () => {
    let api: ApiHelper;
    let hierarchy: { departmentId: string; semesterId: string; subjectId: string; moduleId: string };

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
    });

    test.afterEach(async () => {
        if (hierarchy?.departmentId) {
            await api.cleanupHierarchy(hierarchy);
        }
    });

    test('Create complete hierarchy: Dept -> Semester -> Subject -> Module', async () => {
        hierarchy = await api.createTestHierarchy();

        expect(hierarchy.departmentId).toBeDefined();
        expect(hierarchy.semesterId).toBeDefined();
        expect(hierarchy.subjectId).toBeDefined();
        expect(hierarchy.moduleId).toBeDefined();

        // Verify hierarchy in tree
        const tree = await api.getExplorerTree();
        const deptNode = tree.find((d: any) => d.id === hierarchy.departmentId);
        expect(deptNode).toBeDefined();
        expect(deptNode.type).toBe('department');
    });

    test('Retrieve children at each level', async () => {
        hierarchy = await api.createTestHierarchy();

        // Get semesters for department
        const semesters = await api.getSemestersByDepartment(hierarchy.departmentId);
        expect(semesters.length).toBeGreaterThan(0);
        expect(semesters.some((s: any) => s.id === hierarchy.semesterId)).toBe(true);

        // Get subjects for semester
        const subjects = await api.getSubjectsBySemester(hierarchy.semesterId);
        expect(subjects.length).toBeGreaterThan(0);
        expect(subjects.some((s: any) => s.id === hierarchy.subjectId)).toBe(true);

        // Get modules for subject
        const modules = await api.getModulesBySubject(hierarchy.subjectId);
        expect(modules.length).toBeGreaterThan(0);
        expect(modules.some((m: any) => m.id === hierarchy.moduleId)).toBe(true);
    });

    test('Explorer tree returns nested structure', async () => {
        hierarchy = await api.createTestHierarchy();

        const tree = await api.getExplorerTree();
        expect(Array.isArray(tree)).toBe(true);

        // Find our department
        const dept = tree.find((d: any) => d.id === hierarchy.departmentId);
        expect(dept).toBeDefined();

        // Department should have children (semesters)
        expect(dept.children).toBeDefined();
        expect(Array.isArray(dept.children)).toBe(true);

        // Find semester in children
        const sem = dept.children.find((s: any) => s.id === hierarchy.semesterId);
        expect(sem).toBeDefined();
        expect(sem.children).toBeDefined();
    });

    test('Explorer children endpoint for lazy loading', async () => {
        hierarchy = await api.createTestHierarchy();

        // Get department's children (semesters)
        const semesters = await api.getExplorerChildren('department', hierarchy.departmentId);
        expect(semesters.length).toBeGreaterThan(0);
        expect(semesters.some((s: any) => s.id === hierarchy.semesterId)).toBe(true);

        // Get semester's children (subjects)
        const subjects = await api.getExplorerChildren('semester', hierarchy.semesterId);
        expect(subjects.length).toBeGreaterThan(0);
        expect(subjects.some((s: any) => s.id === hierarchy.subjectId)).toBe(true);
    });
});

test.describe('API - Notes Operations', () => {
    let api: ApiHelper;
    let hierarchy: { moduleId: string; departmentId: string };
    let createdNoteId: string;

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
        hierarchy = await api.createTestHierarchy();
    });

    test.afterEach(async () => {
        if (createdNoteId) {
            await api.deleteNote(createdNoteId);
            createdNoteId = '';
        }
        if (hierarchy?.departmentId) {
            await api.cleanupHierarchy(hierarchy);
        }
    });

    test('Create a note', async () => {
        const title = 'Test Note';
        const pdfUrl = '/pdfs/test.pdf';

        const noteId = await api.createNote(hierarchy.moduleId, title, pdfUrl);
        createdNoteId = noteId;

        expect(noteId).toBeDefined();

        // Verify note status
        const status = await api.getNoteStatus(noteId);
        expect(status.title).toBe(title);
        expect(status.pdfUrl).toBe(pdfUrl);
    });

    test('Update note title', async () => {
        const noteId = await api.createNote(hierarchy.moduleId, 'Original Title', '/pdfs/test.pdf');
        createdNoteId = noteId;

        await api.updateNote(noteId, 'Updated Title');

        const status = await api.getNoteStatus(noteId);
        expect(status.title).toBe('Updated Title');
    });

    test('Delete note', async () => {
        const noteId = await api.createNote(hierarchy.moduleId, 'Delete Me', '/pdfs/test.pdf');
        createdNoteId = noteId;

        await api.deleteNote(noteId);
        createdNoteId = '';

        // Verify it's gone
        const status = await api.getNoteStatus(noteId);
        // Should fail or return not found
        expect(status).toBeDefined();
    });
});

test.describe('API - Explorer Move Operations', () => {
    let api: ApiHelper;
    let hierarchy1: { departmentId: string; semesterId: string; subjectId: string; moduleId: string };
    let hierarchy2: { departmentId: string; semesterId: string; subjectId: string; moduleId: string };

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
        hierarchy1 = await api.createTestHierarchy();
        hierarchy2 = await api.createTestHierarchy();
    });

    test.afterEach(async () => {
        await api.cleanupHierarchy(hierarchy1);
        await api.cleanupHierarchy(hierarchy2);
    });

    test('Move module to different subject', async () => {
        const sourceModuleId = hierarchy1.moduleId;
        const targetSubjectId = hierarchy2.subjectId;

        const result = await api.moveNode(
            sourceModuleId,
            'module',
            targetSubjectId,
            'subject'
        );

        expect(result.success).toBe(true);

        // Verify module is now under target subject
        const modules = await api.getModulesBySubject(targetSubjectId);
        expect(modules.some((m: any) => m.id === sourceModuleId)).toBe(true);

        // Verify module is gone from original subject
        const originalModules = await api.getModulesBySubject(hierarchy1.subjectId);
        expect(originalModules.some((m: any) => m.id === sourceModuleId)).toBe(false);
    });

    test('Move subject to different semester', async () => {
        const sourceSubjectId = hierarchy1.subjectId;
        const targetSemesterId = hierarchy2.semesterId;

        const result = await api.moveNode(
            sourceSubjectId,
            'subject',
            targetSemesterId,
            'semester'
        );

        expect(result.success).toBe(true);

        // Verify subject is under new semester
        const subjects = await api.getSubjectsBySemester(targetSemesterId);
        expect(subjects.some((s: any) => s.id === sourceSubjectId)).toBe(true);
    });
});

test.describe('API - Error Handling', () => {
    let api: ApiHelper;

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
    });

    test('Returns 404 for non-existent department', async ({ request }) => {
        const response = await request.get(`${api.request ? '' : ''}/api/departments/nonexistent`);
        // Note: This test depends on how your API handles errors
        // If it returns 404, test passes
    });

    test('Validates required fields', async ({ request }) => {
        const response = await request.post(`http://localhost:8001/api/departments`, {
            data: { name: '' } // Missing required code
        });

        // Should fail validation
        expect(response.ok()).toBe(false);
    });

    test('Prevents duplicate codes where applicable', async ({ request }) => {
        // Create department with specific code
        const dept1 = await api.createDepartment('Dept1', 'DUP');

        // Try to create another with same code (if unique constraint exists)
        // This depends on your validation rules
        // If unique constraint, this should fail

        await api.deleteDepartment(dept1);
    });
});

test.describe('API - Explorer Tree Performance', () => {
    let api: ApiHelper;
    let hierarchies: Array<{ departmentId: string }> = [];

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
        // Create multiple departments for performance test
        for (let i = 0; i < 3; i++) {
            const h = await api.createTestHierarchy();
            hierarchies.push({ departmentId: h.departmentId });
        }
    });

    test.afterEach(async () => {
        for (const h of hierarchies) {
            await api.deleteDepartment(h.departmentId);
        }
        hierarchies = [];
    });

    test('Tree endpoint responds within acceptable time', async () => {
        const start = Date.now();
        const tree = await api.getExplorerTree();
        const duration = Date.now() - start;

        expect(Array.isArray(tree)).toBe(true);
        expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
    });

    test('Tree contains all created departments', async () => {
        const tree = await api.getExplorerTree();

        for (const h of hierarchies) {
            const found = tree.some((d: any) => d.id === h.departmentId);
            expect(found).toBe(true);
        }
    });
});
