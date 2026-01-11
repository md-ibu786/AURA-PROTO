/**
 * ============================================================================
 * FILE: client.ts
 * LOCATION: frontend/src/api/client.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Centralized HTTP client for all backend API calls. Provides typed fetch
 *    wrappers with consistent error handling, JSON parsing, and support for
 *    both JSON and FormData requests.
 *
 * ROLE IN PROJECT:
 *    Foundation layer for all API communication. Used by:
 *    - explorerApi.ts (hierarchy CRUD, tree fetching)
 *    - audioApi.ts (transcription, pipeline, uploads)
 *
 * KEY COMPONENTS:
 *    - API_BASE: Base URL for all API calls ('/api')
 *    - DuplicateError: Custom error class for 409 conflicts (duplicate names)
 *    - fetchApi<T>: Generic typed fetch for JSON requests
 *    - fetchFormData<T>: Fetch wrapper for file uploads (FormData)
 *
 * ERROR HANDLING:
 *    - 409 responses with DUPLICATE_NAME code throw DuplicateError
 *    - Other errors throw standard Error with detail message
 *    - Network errors return generic 'Network error' message
 *
 * DEPENDENCIES:
 *    - External: None (uses native fetch)
 *    - Internal: None
 *
 * USAGE:
 *    import { fetchApi, fetchFormData, DuplicateError } from './client';
 *
 *    // JSON request
 *    const data = await fetchApi<MyType>('/endpoint', { method: 'POST', body: JSON.stringify(payload) });
 *
 *    // File upload
 *    const result = await fetchFormData<ResponseType>('/upload', formData);
 * ============================================================================
 */

const API_BASE = '/api';

export class DuplicateError extends Error {
    code: string;

    constructor(message: string, code: string) {
        super(message);
        this.name = 'DuplicateError';
        this.code = code;
    }
}

// Generic fetch wrapper with error handling
async function fetchApi<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Network error' }));

        if (response.status === 409) {
            const detail = error.detail;
            if (detail && typeof detail === 'object' && detail.code === 'DUPLICATE_NAME') {
                throw new DuplicateError(detail.message, detail.code);
            }
        }

        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// Fetch wrapper for FormData (no Content-Type header)
async function fetchFormData<T>(
    endpoint: string,
    formData: FormData
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const response = await fetch(url, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Network error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

export { fetchApi, fetchFormData, API_BASE };
