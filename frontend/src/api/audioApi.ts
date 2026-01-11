/**
 * ============================================================================
 * FILE: audioApi.ts
 * LOCATION: frontend/src/api/audioApi.ts
 * ============================================================================
 *
 * PURPOSE:
 *    API functions for the AI Note Generator feature. Provides typed methods
 *    for audio transcription, transcript refinement, note summarization,
 *    and PDF generation pipeline.
 *
 * ROLE IN PROJECT:
 *    Backend integration layer for the UploadDialog component.
 *    Enables the audio-to-notes workflow:
 *    Audio File → Transcribe → Refine → Summarize → Generate PDF
 *
 * KEY FUNCTIONS:
 *    Individual Pipeline Steps (for debugging/manual control):
 *    - transcribeAudio(file): Upload audio, get transcript from Deepgram
 *    - refineTranscript(request): Clean transcript with AI
 *    - summarizeTranscript(request): Generate structured notes
 *    - generatePdf(request): Create PDF from notes
 *
 *    Full Pipeline:
 *    - startPipeline(file, topic, moduleId): Start async processing job
 *    - getPipelineStatus(jobId): Poll for job status and results
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./client.ts (fetchApi, fetchFormData), ../types (interfaces)
 *
 * USAGE:
 *    import { startPipeline, getPipelineStatus } from './audioApi';
 *
 *    const { jobId } = await startPipeline(audioFile, 'Lecture 1', moduleId);
 *    const status = await getPipelineStatus(jobId);
 *    if (status.status === 'complete') {
 *        console.log(status.result.pdfUrl);
 *    }
 * ============================================================================
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
