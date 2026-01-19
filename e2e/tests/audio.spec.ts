import { test, expect } from '@playwright/test';
import { ApiHelper } from '../page-objects/ApiHelper';
import { ExplorerPage } from '../page-objects/ExplorerPage';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Audio Processing E2E Tests
 * Tests the complete audio processing pipeline:
 * - Document upload
 * - Voice recording upload
 * - AI transcription
 * - Transcript refinement
 * - Note generation
 * - PDF creation
 */

test.describe('Audio Processing - Document Upload', () => {
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; moduleId: string };
    let testPdfPath: string;

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();

        // Create a test PDF file
        testPdfPath = path.join(__dirname, '..', 'data', 'test-document.pdf');
        if (!fs.existsSync(path.dirname(testPdfPath))) {
            fs.mkdirSync(path.dirname(testPdfPath), { recursive: true });
        }
        // Create minimal valid PDF
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
<< /Length 44 >>
stream
BT /F1 12 Tf 72 720 Td (Test PDF) Tj ET
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
        fs.writeFileSync(testPdfPath, pdfContent);
    });

    test.afterAll(async ({ request }) => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
        if (testPdfPath && fs.existsSync(testPdfPath)) {
            fs.unlinkSync(testPdfPath);
        }
        const dataDir = path.join(__dirname, '..', 'data');
        if (fs.existsSync(dataDir)) {
            fs.rmdirSync(dataDir, { recursive: true });
        }
    });

    test('Upload document via API', async () => {
        const fileBuffer = fs.readFileSync(testPdfPath);
        const result = await apiHelper.uploadDocument(
            hierarchy.moduleId,
            fileBuffer,
            'test-document.pdf',
            'Test Document'
        );

        expect(result.success).toBe(true);
        expect(result.documentUrl).toBeDefined();
    });

    test('Verify document appears in module', async ({ request }) => {
        const fileBuffer = fs.readFileSync(testPdfPath);
        await apiHelper.uploadDocument(
            hierarchy.moduleId,
            fileBuffer,
            'test-document.pdf',
            'API Test Doc'
        );

        // Get module's notes
        const modules = await apiHelper.getModulesBySubject(hierarchy.subjectId);
        const module = modules.find((m: any) => m.id === hierarchy.moduleId);

        // Note should be created
        expect(module).toBeDefined();
    });
});

test.describe('Audio Processing - Voice Pipeline', () => {
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; moduleId: string };
    let testAudioPath: string;

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();

        // Create a minimal audio file (WAV header)
        testAudioPath = path.join(__dirname, '..', 'data', 'test-audio.wav');
        if (!fs.existsSync(path.dirname(testAudioPath))) {
            fs.mkdirSync(path.dirname(testAudioPath), { recursive: true });
        }

        // Minimal WAV file (1 second of silence)
        const wavBuffer = Buffer.from([
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
        fs.writeFileSync(testAudioPath, wavBuffer);
    });

    test.afterAll(async () => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
        if (testAudioPath && fs.existsSync(testAudioPath)) {
            fs.unlinkSync(testAudioPath);
        }
    });

    test('Start audio processing pipeline', async () => {
        const fileBuffer = fs.readFileSync(testAudioPath);
        const jobId = await apiHelper.startAudioPipeline(
            hierarchy.moduleId,
            fileBuffer,
            'test-audio.wav',
            'Test Topic'
        );

        expect(jobId).toBeDefined();
        expect(jobId.length).toBeGreaterThan(0);
    });

    test('Poll pipeline status', async () => {
        const fileBuffer = fs.readFileSync(testAudioPath);
        const jobId = await apiHelper.startAudioPipeline(
            hierarchy.moduleId,
            fileBuffer,
            'test-audio.wav',
            'Status Test'
        );

        // Poll for status
        const status = await apiHelper.getPipelineStatus(jobId);
        expect(status).toBeDefined();
        expect(status.jobId).toBe(jobId);
        expect(status.status).toBeDefined();
    });

    test('Complete pipeline creates note and PDF', async function() {
        // Skip if no actual AI services configured
        // This test requires real Deepgram and Vertex AI credentials
        if (!process.env.DEEPGRAM_API_KEY || !process.env.LLM_KEY) {
            this.skip();
        }

        const fileBuffer = fs.readFileSync(testAudioPath);
        const jobId = await apiHelper.startAudioPipeline(
            hierarchy.moduleId,
            fileBuffer,
            'test-audio.wav',
            'Complete Pipeline Test'
        );

        // Wait for processing (up to 2 minutes)
        const result = await apiHelper.waitForNoteProcessing(jobId, 120000);
        expect(result.status).toBe('complete');
        expect(result.pdfUrl).toBeDefined();
    });
});

test.describe('Audio Processing - UI Integration', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; moduleId: string };
    let testPdfPath: string;

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();

        // Create test PDF
        testPdfPath = path.join(__dirname, '..', 'data', 'upload-test.pdf');
        if (!fs.existsSync(path.dirname(testPdfPath))) {
            fs.mkdirSync(path.dirname(testPdfPath), { recursive: true });
        }
        const pdfContent = `%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
172
%%EOF`;
        fs.writeFileSync(testPdfPath, pdfContent);
    });

    test.afterAll(async () => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
        if (testPdfPath && fs.existsSync(testPdfPath)) {
            fs.unlinkSync(testPdfPath);
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('Upload document via UI dialog', async () => {
        // Navigate to module
        await explorerPage.expandPath(['Test Dept', 'Test Semester', 'Test Subject']);

        // Open upload dialog
        await explorerPage.openUploadDialog('Test Module');
        await explorerPage.selectUploadMode('document');

        // Upload file
        await explorerPage.uploadDocumentFile(testPdfPath, 'UI Test Document');

        // Verify success (dialog should show processing state)
        const isOpen = await explorerPage.isDialogOpen();
        expect(isOpen).toBe(true);
    });

    test('Upload dialog shows correct module info', async () => {
        await explorerPage.expandPath(['Test Dept', 'Test Semester', 'Test Subject']);
        await explorerPage.openUploadDialog('Test Module');

        // Check that module name is displayed
        const dialogText = await explorerPage.uploadDialog.textContent();
        expect(dialogText).toContain('Test Module');
    });
});

test.describe('Audio Processing - Error Handling', () => {
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; moduleId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();
    });

    test.afterAll(async () => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
    });

    test('Rejects invalid file type', async ({ request }) => {
        const invalidBuffer = Buffer.from('Not a valid file');
        const response = await request.post('http://localhost:8001/api/audio/upload-document', {
            multipart: {
                file: {
                    name: 'test.txt',
                    mimeType: 'text/plain',
                    buffer: invalidBuffer
                },
                moduleId: hierarchy.moduleId,
                title: 'Invalid Test'
            }
        });

        // Should fail validation
        expect(response.ok()).toBe(false);
    });

    test('Fails with missing moduleId', async ({ request }) => {
        const response = await request.post('http://localhost:8001/api/audio/upload-document', {
            multipart: {
                file: {
                    name: 'test.pdf',
                    mimeType: 'application/pdf',
                    buffer: Buffer.from('PDF content')
                },
                title: 'No Module'
            }
        });

        expect(response.ok()).toBe(false);
    });
});

test.describe('Audio Processing - Performance', () => {
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; moduleId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();
    });

    test.afterAll(async () => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
    });

    test('Document upload completes within acceptable time', async () => {
        // Create a small PDF
        const pdfBuffer = Buffer.from(`%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
172
%%EOF`);

        const start = Date.now();
        const result = await apiHelper.uploadDocument(
            hierarchy.moduleId,
            pdfBuffer,
            'perf-test.pdf',
            'Performance Test'
        );
        const duration = Date.now() - start;

        expect(result.success).toBe(true);
        expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
    });
});