/**
 * ============================================================================
 * FILE: explorerApi.ts
 * LOCATION: frontend/src/api/explorerApi.ts
 * ============================================================================
 *
 * PURPOSE:
 *    API functions for the file explorer interface. Provides typed methods
 *    for fetching the hierarchy tree, lazy-loading children, and performing
 *    CRUD operations on all hierarchy entities.
 *
 * ROLE IN PROJECT:
 *    Primary API layer for the ExplorerPage. Called by:
 *    - useExplorerStore (React Query integration)
 *    - ContextMenu (rename, delete operations)
 *    - SidebarTree (tree data fetching)
 *
 * KEY FUNCTIONS:
 *    Tree Operations:
 *    - getExplorerTree(depth): Fetch full hierarchy tree
 *    - getNodeChildren(type, id): Lazy-load children for a node
 *    - moveNode(request): Move node to new parent
 *    - getNoteStatus(noteId): Get processing status for a note
 *    - downloadNotesZip(filenames): Download selected notes as a zip archive
 *
 *    CRUD - Create:
 *    - createDepartment, createSemester, createSubject, createModule
 *
 *    CRUD - Update:
 *    - updateDepartment, updateSemester, updateSubject, updateModule, updateNote
 *    - renameNode(type, id, name): Unified rename for any node type
 *
 *    CRUD - Delete:
 *    - deleteDepartment, deleteSemester, deleteSubject, deleteModule, deleteNote
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./client.ts (fetchApi), ../types (TypeScript interfaces)
 *
 * USAGE:
 *    import { getExplorerTree, createModule, renameNode } from './explorerApi';
 *
 *    const tree = await getExplorerTree(5);
 *    await renameNode('module', moduleId, 'New Name');
 * ============================================================================
 */
import { fetchApi, fetchBlob, type BlobResponse } from './client';
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
    nodeId: string
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
export async function getNoteStatus(noteId: string): Promise<{
    id: string;
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

export async function createSemester(departmentId: string, semesterNumber: number, name: string) {
    return fetchApi('/semesters', {
        method: 'POST',
        body: JSON.stringify({ department_id: departmentId, semester_number: semesterNumber, name }),
    });
}

export async function createSubject(semesterId: string, name: string, code: string) {
    return fetchApi('/subjects', {
        method: 'POST',
        body: JSON.stringify({ semester_id: semesterId, name, code }),
    });
}

export async function createModule(subjectId: string, moduleNumber: number, name: string) {
    return fetchApi('/modules', {
        method: 'POST',
        body: JSON.stringify({ subject_id: subjectId, module_number: moduleNumber, name }),
    });
}

export async function updateDepartment(id: string, data: { name?: string; code?: string }) {
    return fetchApi(`/departments/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateSemester(id: string, data: { name?: string; semester_number?: number }) {
    return fetchApi(`/semesters/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateSubject(id: string, data: { name?: string; code?: string }) {
    return fetchApi(`/subjects/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateModule(id: string, data: { name?: string; module_number?: number }) {
    return fetchApi(`/modules/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function updateNote(id: string, title: string) {
    return fetchApi(`/notes/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ title }),
    });
}

export async function deleteDepartment(id: string) {
    return fetchApi(`/departments/${id}`, { method: 'DELETE' });
}

export async function deleteSemester(id: string) {
    return fetchApi(`/semesters/${id}`, { method: 'DELETE' });
}

export async function deleteSubject(id: string) {
    return fetchApi(`/subjects/${id}`, { method: 'DELETE' });
}

export async function deleteModule(id: string) {
    return fetchApi(`/modules/${id}`, { method: 'DELETE' });
}

export async function deleteNote(id: string) {
    return fetchApi(`/notes/${id}`, { method: 'DELETE' });
}

export async function deleteNoteCascade(id: string): Promise<{
    message: string;
    note_id: string;
    cascade_status: 'complete' | 'document_only' | 'kg_failed';
    kg_deletion_status: string;
    pdf_deleted: boolean;
    document_deleted: boolean;
}> {
    return fetchApi(`/notes/${id}/cascade`, { method: 'DELETE' });
}

export async function downloadNotesZip(
    filenames: string[],
    subjectName?: string,
    moduleName?: string
): Promise<BlobResponse> {
    return fetchBlob('/pdfs/zip', {
        method: 'POST',
        body: JSON.stringify({
            filenames,
            subject_name: subjectName,
            module_name: moduleName,
        }),
    });
}

// Unified rename function
export async function renameNode(type: HierarchyType, id: string, name: string) {
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

// ============================================================================
// KG Processing API
// ============================================================================

import type {
    KGStatusResponse,
    ProcessingRequest,
    BatchProcessingResponse,
    ProcessingQueueItem,
    TaskStatusResponse,
    DeleteBatchRequest,
    DeleteBatchResponse
} from '../features/kg/types/kg.types';

export async function getKGDocumentStatus(documentId: string): Promise<KGStatusResponse> {
    return fetchApi<KGStatusResponse>(`/v1/kg/documents/${documentId}/status`);
}

export async function processKGBatch(request: ProcessingRequest): Promise<BatchProcessingResponse> {
    return fetchApi<BatchProcessingResponse>('/v1/kg/process-batch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });
}

export async function getKGProcessingQueue(): Promise<ProcessingQueueItem[]> {
    return fetchApi<ProcessingQueueItem[]>('/v1/kg/processing-queue');
}

export async function getKGTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return fetchApi<TaskStatusResponse>(`/v1/kg/tasks/${taskId}/status`);
}

export async function deleteKGBatch(request: DeleteBatchRequest): Promise<DeleteBatchResponse> {
    return fetchApi<DeleteBatchResponse>('/v1/kg/delete-batch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });
}
