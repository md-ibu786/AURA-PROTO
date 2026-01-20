/**
 * ============================================================================
 * FILE: FileSystemNode.ts
 * LOCATION: frontend/src/types/FileSystemNode.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Core TypeScript type definitions for the AURA-PROTO frontend.
 *    Defines interfaces that mirror backend Pydantic models, ensuring
 *    type-safe API communication between React and FastAPI.
 *
 * ROLE IN PROJECT:
 *    Central type definition file used throughout the frontend:
 *    - Components rely on these types for props and state
 *    - API functions use these for request/response typing
 *    - Zustand store uses FileSystemNode for tree state
 *
 * KEY TYPES:
 *    Hierarchy Types:
 *    - HierarchyType: Union type for node types (department|semester|subject|module|note)
 *    - FileSystemNode: Main tree node structure with children and metadata
 *    - FileSystemNodeMeta: Additional metadata (noteCount, pdfFilename, etc.)
 *    - MoveRequest/MoveResponse: For drag-drop node moves
 *    - CreateNodeRequest: For creating new hierarchy items
 *
 *    Audio Processing Types:
 *    - TranscribeResponse: Deepgram transcription result
 *    - RefineRequest/Response: Transcript cleaning
 *    - SummarizeRequest/Response: Note generation
 *    - GeneratePdfRequest/Response: PDF creation
 *    - PipelineStatus: Async pipeline status with progress
 *
 * DEPENDENCIES:
 *    - External: None (pure TypeScript)
 *    - Internal: None
 *
 * USAGE:
 *    import type { FileSystemNode, HierarchyType, PipelineStatus } from '../types';
 * ============================================================================
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

    // KG Processing Fields
    kg_status?: 'pending' | 'processing' | 'ready' | 'failed';
    kg_processed_at?: string;
    kg_error?: string;
    module_id?: string;
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
