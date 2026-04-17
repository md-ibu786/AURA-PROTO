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
 *    - fetchApi<T>: Generic typed fetch for JSON requests with auth retry
 *    - fetchBlob: Fetch wrapper for binary downloads (Blob responses)
 *    - fetchFormData<T>: Fetch wrapper for file uploads (FormData)
 *    - executeWithRetry: Shared 401 retry logic for all fetch functions
 *    - getAuthHeader: Authentication header helper with explicit error handling
 *
 * ERROR HANDLING:
 *    - 409 responses with DUPLICATE_NAME code throw DuplicateError
 *    - Auth token failures throw AuthError (explicit failure mode)
 *    - Network failures throw NetworkError
 *    - Other errors throw standard Error with detail message
 *
 * DEPENDENCIES:
 *    - External: None (uses native fetch)
 *    - Internal: ../stores/useAuthStore (auth state), ./errors (error classes)
 *
 * USAGE:
 *    import { fetchApi, fetchFormData, DuplicateError, AuthError } from './client';
 *
 *    // JSON request
 *    const data = await fetchApi<MyType>('/endpoint', { method: 'POST', body: JSON.stringify(payload) });
 *
 *    // File upload
 *    const result = await fetchFormData<ResponseType>('/upload', formData);
 *
 *    // Error handling
 *    try {
 *        await fetchApi(...)
 *    } catch (e) {
 *        if (e instanceof AuthError) { ... }
 *        else if (e instanceof DuplicateError) { ... }
 *    }
 * ============================================================================
 */

import { useAuthStore } from '../stores/useAuthStore';
import { DuplicateError, AuthError } from './errors';

const API_BASE = '/api';

// Shared token refresh promise to prevent concurrent refresh race conditions
let tokenRefreshPromise: Promise<string | null> | null = null;

export interface BlobResponse {
    blob: Blob;
    filename: string | null;
}

/**
 * Get authentication header for API requests.
 * Throws AuthError if token retrieval fails unexpectedly.
 * Returns empty object if no token is available (expected for unauthenticated routes).
 */
async function getAuthHeader(): Promise<Record<string, string>> {
    try {
        const token = await useAuthStore.getState().getIdToken();
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
        // No token available - expected for unauthenticated routes
        return {};
    } catch (e) {
        // Token retrieval failed - this is unexpected
        console.error('Auth token retrieval failed:', e);
        throw new AuthError('Failed to retrieve authentication token', e);
    }
}

/**
 * Execute a fetch with 401 retry logic.
 * If initial response is 401, attempts token refresh and retries once.
 * Throws AuthError if token refresh fails during retry.
 */
async function executeWithRetry(
    url: string,
    options: RequestInit
): Promise<Response> {
    let response = await fetch(url, options);

    if (response.status === 401 && import.meta.env.VITE_USE_MOCK_AUTH !== 'true') {
        try {
            // Use shared refresh promise if one is already in progress
            if (!tokenRefreshPromise) {
                tokenRefreshPromise = useAuthStore.getState().getIdToken(true)
                    .finally(() => {
                        tokenRefreshPromise = null;
                    });
            }
            const newToken = await tokenRefreshPromise;
            if (newToken) {
                const retryHeaders = {
                    ...options.headers,
                    'Authorization': `Bearer ${newToken}`,
                };
                response = await fetch(url, {
                    ...options,
                    headers: retryHeaders,
                });
            }
        } catch (e) {
            console.error('Token refresh failed', e);
            throw new AuthError('Token refresh failed during retry', e);
        }
    }

    return response;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null;
}

function extractFilename(contentDisposition: string | null): string | null {
    if (!contentDisposition) return null;

    const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utfMatch && utfMatch[1]) {
        try {
            return decodeURIComponent(utfMatch[1]);
        } catch {
            return utfMatch[1];
        }
    }

    const basicMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    return basicMatch ? basicMatch[1] : null;
}

async function parseErrorMessage(response: Response): Promise<string> {
    const fallback = `HTTP ${response.status}`;
    const bodyText = await response.text().catch(() => '');

    if (!bodyText) {
        return fallback;
    }

    try {
        const parsed = JSON.parse(bodyText);
        if (isRecord(parsed) && typeof parsed.detail === 'string') {
            return parsed.detail;
        }
    } catch {
        // Ignore JSON parse errors and fall back to raw text.
    }

    return bodyText;
}

// Generic fetch wrapper with error handling
async function fetchApi<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const authHeaders = await getAuthHeader();

    const response = await executeWithRetry(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch((e) => {
            console.warn('Failed to parse error response:', e);
            return { detail: 'Network error' };
        });

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

// Fetch wrapper for Blob responses (downloads)
async function fetchBlob(
    endpoint: string,
    options?: RequestInit
): Promise<BlobResponse> {
    const url = `${API_BASE}${endpoint}`;
    const authHeaders = await getAuthHeader();

    const response = await executeWithRetry(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const message = await parseErrorMessage(response);
        throw new Error(message);
    }

    const blob = await response.blob();
    const filename = extractFilename(
        response.headers.get('Content-Disposition')
    );

    return { blob, filename };
}

// Fetch wrapper for FormData (no Content-Type header)
async function fetchFormData<T>(
    endpoint: string,
    formData: FormData
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const authHeaders = await getAuthHeader();

    const response = await executeWithRetry(url, {
        method: 'POST',
        headers: {
            ...authHeaders,
        },
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch((e) => {
            console.warn('Failed to parse error response:', e);
            return { detail: 'Network error' };
        });
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

/**
 * Fetch helper for auth store usage where token is already available.
 * Unlike fetchApi, this accepts an explicit token parameter rather than
 * calling getAuthHeader(), avoiding circular dependency during auth flows.
 *
 * Does NOT include 401 retry logic - auth store handles its own retry.
 */
export async function fetchAuthApi<T>(
    endpoint: string,
    options: RequestInit,
    token: string
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch((e) => {
            console.warn('Failed to parse error response:', e);
            return { detail: 'Network error' };
        });
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// Health check response type
export interface ChatHealthStatus {
    status: string;
    version: string;
    neo4j_connected: boolean;
    redis_connected: boolean;
    firestore_connected: boolean;
    services_ready: boolean;
    semantic_router: string;
    timestamp: string;
}

export interface HealthStatus {
    // Notes Manager specific
    status: string;
    version: string;
    neo4j_connected: boolean; // Misnamed Redis check in ANM
    services_ready: boolean;  // Firestore check in ANM

    // Chat specific
    chat?: ChatHealthStatus;
}

/**
 * checkHealth
 * Checks backend health by querying /health and /chat-api/health.
 * Used by SettingsPage for real-time system monitoring with auto-refresh.
 *
 * @see: api/main.py - Health check endpoint definitions for ANM
 * @see: AURA-CHAT/server/routers/health.py - Health check endpoint for Chat
 */
export async function checkHealth(): Promise<HealthStatus> {
    let status = 'healthy';
    let version = 'unknown';
    let neo4jConnected = false;
    let servicesReady = false;
    let chatStatus: ChatHealthStatus | undefined = undefined;

    // Helper to fetch without /api prefix (health endpoints are at root)
    const fetchHealth = async (endpoint: string): Promise<Response | null> => {
        try {
            const authHeaders = await getAuthHeader();
            return fetch(endpoint, {
                headers: authHeaders,
            });
        } catch (e) {
            console.warn('Health check auth failed:', e);
            return null;
        }
    };

    // 1. Check Notes Manager health
    try {
        const response = await fetchHealth('/health');
        if (response && response.ok) {
            const healthData = await response.json() as { status: string; version: string };
            version = healthData.version;
        } else {
            status = 'degraded';
        }
    } catch {
        status = 'degraded';
    }

    try {
        const response = await fetchHealth('/ready');
        if (response && response.ok) {
            const readyData = await response.json() as { status: string; database: string };
            servicesReady = readyData.status === 'ready';
        } else {
            servicesReady = false;
            status = 'degraded';
        }
    } catch {
        servicesReady = false;
        status = 'degraded';
    }

    try {
        const response = await fetchHealth('/health/redis');
        if (response && response.ok) {
            const redisData = await response.json() as { status: string };
            neo4jConnected = redisData.status === 'healthy';
        } else {
            neo4jConnected = false;
        }
    } catch {
        neo4jConnected = false;
    }

    // 2. Check Chat health via proxy
    try {
        const response = await fetch('/chat-api/health');
        if (response.ok) {
            chatStatus = await response.json() as ChatHealthStatus;
        }
    } catch (e) {
        console.warn('Failed to fetch Chat status', e);
    }

    return {
        status,
        version,
        neo4j_connected: neo4jConnected,
        services_ready: servicesReady,
        chat: chatStatus,
    };
}

// Re-export error classes for backward compatibility and convenience
export { DuplicateError, AuthError } from './errors';
export { fetchApi, fetchBlob, fetchFormData, API_BASE };
// fetchAuthApi is already exported as an async function above
