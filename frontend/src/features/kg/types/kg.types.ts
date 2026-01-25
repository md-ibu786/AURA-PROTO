/**
 * ============================================================================
 * FILE: kg.types.ts
 * LOCATION: frontend/src/features/kg/types/kg.types.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TypeScript type definitions for the Knowledge Graph (KG) processing
 *    feature. Defines interfaces for document status, processing requests,
 *    batch responses, queue items, and task status.
 *
 * ROLE IN PROJECT:
 *    Central type definitions for KG processing operations. Used by:
 *    - useKGProcessing hook for React Query queries/mutations
 *    - ProcessDialog component for dialog state
 *    - ProcessingQueue component for queue display
 *    - explorerApi.ts for API request/response typing
 *
 * KEY TYPES:
 *    - KGDocumentStatus: 'pending' | 'processing' | 'ready' | 'failed'
 *    - KGStatusResponse: Single document status from API
 *    - ProcessingRequest: Batch processing request
 *    - BatchProcessingResponse: Batch processing result
 *    - ProcessingQueueItem: Queue item with progress
 *    - TaskStatusResponse: Celery task status
 *
 * DEPENDENCIES:
 *    - External: None (pure TypeScript)
 *    - Internal: None
 *
 * @see: hooks/useKGProcessing.ts - React Query hooks using these types
 * @see: components/ProcessDialog.tsx - Dialog using these types
 * @see: components/ProcessingQueue.tsx - Queue display using these types
 */
export type KGDocumentStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface KGStatusResponse {
    document_id: string;
    module_id: string;
    file_name: string;
    kg_status: KGDocumentStatus;
    kg_processed_at?: string;
    kg_error?: string;
    chunk_count?: number;
    entity_count?: number;
}

export interface ProcessingRequest {
    file_ids: string[];
    module_id: string;
}

export interface BatchProcessingResponse {
    task_id: string;
    status_url: string;
    documents_queued: number;
    documents_skipped: number;
    message: string;
}

export interface ProcessingQueueItem {
    document_id: string;
    module_id: string;
    file_name: string;
    status: KGDocumentStatus;
    progress: number;
    step: string;
    started_at: string;
    error?: string;
}

export interface TaskStatusResponse {
    task_id: string;
    status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED';
    progress?: {
        current: number;
        total: number;
        percent: number;
        message: string;
    };
    result?: unknown;
    error?: string;
}


// ============================================================================
// KG DELETION TYPES
// ============================================================================

export interface DeleteBatchRequest {
    file_ids: string[];
    module_id: string;
}

export interface DeleteBatchResponse {
    deleted_count: number;
    failed: string[];
    message: string;
}
