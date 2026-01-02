/**
 * Audio Processing API functions
 */
import { fetchApi, fetchFormData } from './client';
import type {
    TranscribeResponse,
    RefineRequest,
    RefineResponse,
    SummarizeRequest,
    SummarizeResponse,
    GeneratePdfRequest,
    GeneratePdfResponse,
    PipelineStatus,
} from '../types';

// Transcribe audio file
export async function transcribeAudio(file: File): Promise<TranscribeResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return fetchFormData<TranscribeResponse>('/audio/transcribe', formData);
}

// Refine transcript
export async function refineTranscript(request: RefineRequest): Promise<RefineResponse> {
    return fetchApi<RefineResponse>('/audio/refine', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

// Summarize to notes
export async function summarizeTranscript(request: SummarizeRequest): Promise<SummarizeResponse> {
    return fetchApi<SummarizeResponse>('/audio/summarize', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

// Generate PDF
export async function generatePdf(request: GeneratePdfRequest): Promise<GeneratePdfResponse> {
    return fetchApi<GeneratePdfResponse>('/audio/generate-pdf', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}

// Start full pipeline
export async function startPipeline(
    file: File,
    topic: string,
    moduleId?: number
): Promise<{ jobId: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('topic', topic);
    if (moduleId !== undefined) {
        formData.append('moduleId', moduleId.toString());
    }
    return fetchFormData('/audio/process-pipeline', formData);
}

// Get pipeline status
export async function getPipelineStatus(jobId: string): Promise<PipelineStatus> {
    return fetchApi<PipelineStatus>(`/audio/pipeline-status/${jobId}`);
}
