import { APIRequestContext, expect } from '@playwright/test';

const API_BASE = 'http://127.0.0.1:8001';

/**
 * API Helper
 * Provides programmatic access to API for test setup/teardown
 * All methods include validation and error handling
 */
export class ApiHelper {
    readonly request: APIRequestContext;

    constructor(request: APIRequestContext) {
        this.request = request;
    }

    // ========== Health Check ==========

    async checkHealth(): Promise<boolean> {
        try {
            const response = await this.request.get(`${API_BASE}/health`);
            return response.ok();
        } catch {
            return false;
        }
    }

    // ========== Departments ==========

    async createDepartment(name: string, code: string = 'TEST'): Promise<string> {
        const response = await this.request.post(`${API_BASE}/api/departments`, {
            data: { name, code }
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.department).toBeDefined();
        expect(data.department.id).toBeDefined();
        return data.department.id;
    }

    async getDepartment(id: string): Promise<any> {
        const response = await this.request.get(`${API_BASE}/api/departments/${id}`);
        if (!response.ok()) return null;
        return await response.json();
    }

    async updateDepartment(id: string, updates: { name?: string; code?: string }): Promise<void> {
        const response = await this.request.put(`${API_BASE}/api/departments/${id}`, {
            data: updates
        });
        expect(response.ok()).toBeTruthy();
    }

    async deleteDepartment(id: string): Promise<void> {
        const response = await this.request.delete(`${API_BASE}/api/departments/${id}`);
        expect(response.ok()).toBeTruthy();
    }

    async getAllDepartments(): Promise<any[]> {
        const response = await this.request.get(`${API_BASE}/departments`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        return data.departments || [];
    }

    // ========== Semesters ==========

    async createSemester(departmentId: string, name: string): Promise<string> {
        const response = await this.request.post(`${API_BASE}/api/semesters`, {
            data: { name, department_id: departmentId }
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.semester).toBeDefined();
        expect(data.semester.id).toBeDefined();
        return data.semester.id;
    }

    async getSemestersByDepartment(departmentId: string): Promise<any[]> {
        const response = await this.request.get(`${API_BASE}/departments/${departmentId}/semesters`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        return data.semesters || [];
    }

    async deleteSemester(id: string): Promise<void> {
        const response = await this.request.delete(`${API_BASE}/api/semesters/${id}`);
        expect(response.ok()).toBeTruthy();
    }

    // ========== Subjects ==========

    async createSubject(semesterId: string, name: string, code: string): Promise<string> {
        const response = await this.request.post(`${API_BASE}/api/subjects`, {
            data: { name, code, semester_id: semesterId }
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.subject).toBeDefined();
        expect(data.subject.id).toBeDefined();
        return data.subject.id;
    }

    async getSubjectsBySemester(semesterId: string): Promise<any[]> {
        const response = await this.request.get(`${API_BASE}/semesters/${semesterId}/subjects`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        return data.subjects || [];
    }

    async deleteSubject(id: string): Promise<void> {
        const response = await this.request.delete(`${API_BASE}/api/subjects/${id}`);
        expect(response.ok()).toBeTruthy();
    }

    // ========== Modules ==========

    async createModule(subjectId: string, name: string): Promise<string> {
        const response = await this.request.post(`${API_BASE}/api/modules`, {
            data: { name, subject_id: subjectId }
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.module).toBeDefined();
        expect(data.module.id).toBeDefined();
        return data.module.id;
    }

    async getModulesBySubject(subjectId: string): Promise<any[]> {
        const response = await this.request.get(`${API_BASE}/subjects/${subjectId}/modules`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        return data.modules || [];
    }

    async deleteModule(id: string): Promise<void> {
        const response = await this.request.delete(`${API_BASE}/api/modules/${id}`);
        expect(response.ok()).toBeTruthy();
    }

    // ========== Notes ==========

    async createNote(moduleId: string, title: string, pdfUrl: string): Promise<string> {
        const response = await this.request.post(`${API_BASE}/notes`, {
            data: { module_id: moduleId, title, pdf_url: pdfUrl }
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.id).toBeDefined();
        return data.id;
    }

    async updateNote(noteId: string, title: string): Promise<void> {
        const response = await this.request.put(`${API_BASE}/api/notes/${noteId}`, {
            data: { title }
        });
        expect(response.ok()).toBeTruthy();
    }

    async deleteNote(noteId: string): Promise<void> {
        const response = await this.request.delete(`${API_BASE}/api/notes/${noteId}`);
        expect(response.ok()).toBeTruthy();
    }

    // ========== Explorer ==========

    async getExplorerTree(): Promise<any[]> {
        const response = await this.request.get(`${API_BASE}/api/explorer/tree`);
        expect(response.ok()).toBeTruthy();
        return await response.json();
    }

    async getExplorerChildren(nodeType: string, nodeId: string): Promise<any[]> {
        const response = await this.request.get(`${API_BASE}/api/explorer/children/${nodeType}/${nodeId}`);
        expect(response.ok()).toBeTruthy();
        return await response.json();
    }

    async moveNode(nodeId: string, nodeType: string, targetParentId: string, targetParentType: string): Promise<any> {
        const response = await this.request.post(`${API_BASE}/api/explorer/move`, {
            data: {
                nodeId,
                nodeType,
                targetParentId,
                targetParentType
            }
        });
        expect(response.ok()).toBeTruthy();
        return await response.json();
    }

    async getNoteStatus(noteId: string): Promise<any> {
        const response = await this.request.get(`${API_BASE}/api/explorer/notes/${noteId}/status`);
        expect(response.ok()).toBeTruthy();
        return await response.json();
    }

    // ========== Audio Processing ==========

    async uploadDocument(moduleId: string, fileBuffer: Buffer, fileName: string, title?: string): Promise<any> {
        const formData = new FormData();
        const blob = new Blob([fileBuffer], { type: 'application/pdf' });
        formData.append('file', blob, fileName);
        formData.append('moduleId', moduleId);
        if (title) formData.append('title', title);

        const response = await this.request.post(`${API_BASE}/api/audio/upload-document`, {
            multipart: formData
        });
        expect(response.ok()).toBeTruthy();
        return await response.json();
    }

    async startAudioPipeline(moduleId: string, fileBuffer: Buffer, fileName: string, topic: string): Promise<string> {
        const formData = new FormData();
        const blob = new Blob([fileBuffer], { type: 'audio/mpeg' });
        formData.append('file', blob, fileName);
        formData.append('moduleId', moduleId);
        formData.append('topic', topic);

        const response = await this.request.post(`${API_BASE}/api/audio/process-pipeline`, {
            multipart: formData
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(data.jobId).toBeDefined();
        return data.jobId;
    }

    async getPipelineStatus(jobId: string): Promise<any> {
        const response = await this.request.get(`${API_BASE}/api/audio/pipeline-status/${jobId}`);
        expect(response.ok()).toBeTruthy();
        return await response.json();
    }

    // ========== Test Utilities ==========

    /**
     * Creates a complete hierarchy for testing
     * Returns all IDs for cleanup
     */
    async createTestHierarchy(): Promise<{
        departmentId: string;
        semesterId: string;
        subjectId: string;
        moduleId: string;
    }> {
        const timestamp = Date.now();
        const deptId = await this.createDepartment(`Test Dept ${timestamp}`, `TST`);
        const semId = await this.createSemester(deptId, `Test Semester ${timestamp}`);
        const subjId = await this.createSubject(semId, `Test Subject ${timestamp}`, `SUBJ${timestamp}`);
        const modId = await this.createModule(subjId, `Test Module ${timestamp}`);

        return {
            departmentId: deptId,
            semesterId: semId,
            subjectId: subjId,
            moduleId: modId
        };
    }

    /**
     * Cleans up a complete hierarchy
     */
    async cleanupHierarchy(ids: {
        departmentId?: string;
        semesterId?: string;
        subjectId?: string;
        moduleId?: string;
    }): Promise<void> {
        // Delete department will cascade delete everything
        if (ids.departmentId) {
            await this.deleteDepartment(ids.departmentId);
        } else if (ids.moduleId) {
            // If only module ID provided, delete it
            await this.deleteModule(ids.moduleId);
        }
    }

    /**
     * Finds a node in the explorer tree by label
     */
    async findNodeByLabel(tree: any[], label: string, type?: string): Promise<any | null> {
        for (const node of tree) {
            if (node.label.includes(label) && (!type || node.type === type)) {
                return node;
            }
            if (node.children) {
                const found = await this.findNodeByLabel(node.children, label, type);
                if (found) return found;
            }
        }
        return null;
    }

    /**
     * Waits for a note to be processed (polling)
     */
    async waitForNoteProcessing(noteId: string, timeout: number = 60000): Promise<any> {
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            const status = await this.getNoteStatus(noteId);
            if (status.status === 'complete' || status.pdfUrl) {
                return status;
            }
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        throw new Error(`Note ${noteId} did not complete processing within ${timeout}ms`);
    }
}
