/**
 * File System Node Types
 * Mirrors the backend ExplorerNode model
 */

export type HierarchyType = 'department' | 'semester' | 'subject' | 'module' | 'note';

export interface FileSystemNodeMeta {
    noteCount?: number;
    hasChildren?: boolean;
    ordering?: number;
    pdfFilename?: string | null;
    createdAt?: string;
    updatedAt?: string;
    processing?: boolean;
    code?: string;
}

export interface FileSystemNode {
    id: string;
    type: HierarchyType;
    label: string;
    parentId: string | null;
    children?: FileSystemNode[];
    meta?: FileSystemNodeMeta;
}

// API Request/Response types
export interface MoveRequest {
    nodeId: string;
    nodeType: HierarchyType;
    targetParentId: string;
    targetParentType: HierarchyType;
}

export interface MoveResponse {
    success: boolean;
    message: string;
    node?: FileSystemNode;
}

export interface CreateNodeRequest {
    name: string;
    code?: string;
    parentId?: string;
}

// Audio processing types
export interface TranscribeResponse {
    success: boolean;
    transcript?: string;
    error?: string;
}

export interface RefineRequest {
    topic: string;
    transcript: string;
}

export interface RefineResponse {
    success: boolean;
    refinedTranscript?: string;
    error?: string;
}

export interface SummarizeRequest {
    topic: string;
    refinedTranscript: string;
}

export interface SummarizeResponse {
    success: boolean;
    notes?: string;
    error?: string;
}

export interface GeneratePdfRequest {
    title: string;
    notes: string;
    moduleId?: string;
}

export interface GeneratePdfResponse {
    success: boolean;
    pdfUrl?: string;
    noteId?: string;
    error?: string;
}

export interface PipelineStatus {
    jobId: string;
    status: 'pending' | 'transcribing' | 'refining' | 'summarizing' | 'generating_pdf' | 'complete' | 'error';
    progress: number;
    message?: string;
    result?: {
        transcript: string;
        refinedTranscript: string;
        notes: string;
        pdfUrl: string;
        noteId?: string;
    };
}
