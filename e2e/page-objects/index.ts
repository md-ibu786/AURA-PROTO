export { ExplorerPage } from './ExplorerPage';
export { ApiHelper } from './ApiHelper';

/**
 * Test Utilities and Fixtures
 * Common helpers for e2e tests
 */

/**
 * Generates unique test data to avoid conflicts
 */
export function generateUniqueTestData(prefix: string = 'test'): { name: string; code: string } {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 1000);
    return {
        name: `${prefix}-${timestamp}-${random}`,
        code: `${prefix.substring(0, 3).toUpperCase()}-${timestamp % 10000}`
    };
}

/**
 * Delays execution for specified milliseconds
 */
export async function delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retries a function until it succeeds or times out
 */
export async function retry<T>(
    fn: () => Promise<T>,
    options: { maxRetries?: number; delayMs?: number; timeout?: number } = {}
): Promise<T> {
    const { maxRetries = 5, delayMs = 1000, timeout = 30000 } = options;
    const startTime = Date.now();

    let lastError: any;
    for (let i = 0; i <= maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;
            if (Date.now() - startTime > timeout) {
                throw new Error(`Operation timed out after ${timeout}ms. Last error: ${error}`);
            }
            if (i < maxRetries) {
                await delay(delayMs * (i + 1));
            }
        }
    }
    throw lastError;
}

/**
 * Creates a test PDF buffer
 */
export function createTestPdfBuffer(title: string = 'Test Document'): Buffer {
    const pdfContent = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length ${title.length + 50} >>
stream
BT /F1 12 Tf 72 720 Td (${title}) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000203 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
297
%%EOF`;
    return Buffer.from(pdfContent);
}

/**
 * Creates a minimal WAV audio buffer
 */
export function createTestAudioBuffer(): Buffer {
    return Buffer.from([
        // RIFF header
        0x52, 0x49, 0x46, 0x46, // "RIFF"
        0x24, 0x00, 0x00, 0x00, // File size - 8
        0x57, 0x41, 0x56, 0x45, // "WAVE"
        // fmt chunk
        0x66, 0x6d, 0x74, 0x20, // "fmt "
        0x10, 0x00, 0x00, 0x00, // Size
        0x01, 0x00, // PCM
        0x01, 0x00, // Mono
        0x44, 0xac, 0x00, 0x00, // Sample rate 44100
        0x88, 0x58, 0x01, 0x00, // Byte rate
        0x02, 0x00, // Block align
        0x10, 0x00, // Bits per sample
        // data chunk
        0x64, 0x61, 0x74, 0x61, // "data"
        0x00, 0x00, 0x00, 0x00, // Data size
    ]);
}

/**
 * Test data fixtures
 */
export const TestData = {
    departments: {
        valid: [
            { name: 'Computer Science', code: 'CS' },
            { name: 'Electrical Engineering', code: 'EE' },
            { name: 'Mechanical Engineering', code: 'ME' }
        ],
        invalid: [
            { name: '', code: 'TEST' }, // Empty name
            { name: 'Test', code: '' }, // Empty code
            { name: 'A'.repeat(256), code: 'TEST' } // Name too long
        ]
    },

    semesters: {
        valid: [
            { name: 'Semester 1', semester_number: 1 },
            { name: 'Semester 2', semester_number: 2 },
            { name: 'Semester 3', semester_number: 3 }
        ]
    },

    subjects: {
        valid: [
            { name: 'Data Structures', code: 'CS201' },
            { name: 'Algorithms', code: 'CS301' },
            { name: 'Operating Systems', code: 'CS401' }
        ]
    },

    modules: {
        valid: [
            { name: 'Introduction' },
            { name: 'Arrays and Linked Lists' },
            { name: 'Trees and Graphs' }
        ]
    },

    notes: {
        valid: [
            { title: 'Lecture Notes 1', pdfUrl: '/pdfs/lecture1.pdf' },
            { title: 'Tutorial Notes', pdfUrl: '/pdfs/tutorial.pdf' }
        ]
    }
};

/**
 * Environment validation
 */
export function validateTestEnvironment(): { isValid: boolean; missing: string[] } {
    const missing: string[] = [];

    // Check if backend is configured
    if (!process.env.API_BASE && !process.env.CI) {
        // Not required, but warn
    }

    // Check for AI services (optional)
    const hasDeepgram = !!process.env.DEEPGRAM_API_KEY;
    const hasLLM = !!process.env.LLM_KEY;

    return {
        isValid: missing.length === 0,
        missing
    };
}
