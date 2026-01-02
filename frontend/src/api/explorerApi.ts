/**
 * Explorer API functions
 */
import { fetchApi } from './client';
import type {
    FileSystemNode,
    HierarchyType,
    MoveRequest,
    MoveResponse
} from '../types';

// Get full hierarchy tree
export async function getExplorerTree(depth: number = 5): Promise<FileSystemNode[]> {
    return fetchApi<FileSystemNode[]>(`/explorer/tree?depth=${depth}`);
}

// Get children of a specific node (for lazy loading)
export async function getNodeChildren(
    nodeType: HierarchyType,
    nodeId: number
): Promise<FileSystemNode[]> {
    return fetchApi<FileSystemNode[]>(`/explorer/children/${nodeType}/${nodeId}`);
}

// Move a node to a new parent
export async function moveNode(request: MoveRequest): Promise<MoveResponse> {
    return fetchApi<MoveResponse>('/explorer/move', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

// Get note status
export async function getNoteStatus(noteId: number): Promise<{
    id: number;
    title: string;
    status: string;
    pdfUrl?: string;
    createdAt?: string;
}> {
    return fetchApi(`/explorer/notes/${noteId}/status`);
}

// CRUD operations (using existing endpoints)
export async function createDepartment(name: string, code: string) {
    return fetchApi('/departments', {
        method: 'POST',
        body: JSON.stringify({ name, code }),
    });
}

export async function createSemester(departmentId: number, semesterNumber: number, name: string) {
    return fetchApi('/semesters', {
        method: 'POST',
        body: JSON.stringify({ department_id: departmentId, semester_number: semesterNumber, name }),
    });
}

export async function createSubject(semesterId: number, name: string, code: string) {
    return fetchApi('/subjects', {
        method: 'POST',
        body: JSON.stringify({ semester_id: semesterId, name, code }),
    });
}

export async function createModule(subjectId: number, moduleNumber: number, name: string) {
    return fetchApi('/modules', {
        method: 'POST',
        body: JSON.stringify({ subject_id: subjectId, module_number: moduleNumber, name }),
    });
}

export async function updateDepartment(id: number, data: { name?: string; code?: string }) {
    return fetchApi(`/departments/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateSemester(id: number, data: { name?: string; semester_number?: number }) {
    return fetchApi(`/semesters/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateSubject(id: number, data: { name?: string; code?: string }) {
    return fetchApi(`/subjects/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateModule(id: number, data: { name?: string; module_number?: number }) {
    return fetchApi(`/modules/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateNote(id: number, title: string) {
    return fetchApi(`/notes/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ title }),
    });
}

export async function deleteDepartment(id: number) {
    return fetchApi(`/departments/${id}`, { method: 'DELETE' });
}

export async function deleteSemester(id: number) {
    return fetchApi(`/semesters/${id}`, { method: 'DELETE' });
}

export async function deleteSubject(id: number) {
    return fetchApi(`/subjects/${id}`, { method: 'DELETE' });
}

export async function deleteModule(id: number) {
    return fetchApi(`/modules/${id}`, { method: 'DELETE' });
}

export async function deleteNote(id: number) {
    return fetchApi(`/notes/${id}`, { method: 'DELETE' });
}

// Unified rename function
export async function renameNode(type: HierarchyType, id: number, name: string) {
    switch (type) {
        case 'department':
            return updateDepartment(id, { name });
        case 'semester':
            return updateSemester(id, { name });
        case 'subject':
            return updateSubject(id, { name });
        case 'module':
            return updateModule(id, { name });
        case 'note':
            return updateNote(id, name);
        default:
            throw new Error(`Unknown type: ${type}`);
    }
}
