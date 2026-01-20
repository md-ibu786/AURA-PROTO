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
