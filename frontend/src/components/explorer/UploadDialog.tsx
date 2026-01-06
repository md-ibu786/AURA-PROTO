/**
 * Upload Dialog Component
 * Two-option popup for uploading notes (documents or voice for AI generation)
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { X, Upload, FileText, Mic, FileUp, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface UploadDialogProps {
    isOpen: boolean;
    onClose: () => void;
    moduleId: string;
    moduleName: string;
}

type UploadMode = 'select' | 'document' | 'voice' | 'processing';

interface ProcessingState {
    jobId: string;
    status: string;
    progress: number;
    message: string;
    result?: {
        pdfUrl?: string;
        noteId?: number;
    };
}

export function UploadDialog({ isOpen, onClose, moduleId, moduleName }: UploadDialogProps) {
    const [mode, setMode] = useState<UploadMode>('select');
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [topic, setTopic] = useState('');
    const [docTitle, setDocTitle] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [processing, setProcessing] = useState<ProcessingState | null>(null);
    const [error, setError] = useState<string | null>(null);
    const queryClient = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const pollIntervalRef = useRef<number | null>(null);

    // All hooks must be called before any conditional returns
    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            setSelectedFile(files[0]);
        }
    }, []);

    // Poll for processing status
    useEffect(() => {
        if (mode === 'processing' && processing?.jobId) {
            const pollStatus = async () => {
                try {
                    const response = await fetch(`/api/audio/pipeline-status/${processing.jobId}`);
                    const data = await response.json();

                    setProcessing(prev => ({
                        ...prev!,
                        status: data.status,
                        progress: data.progress,
                        message: data.message || prev!.message,
                        result: data.result,
                    }));

                    // Check if complete or error
                    if (data.status === 'complete') {
                        // Stop polling
                        if (pollIntervalRef.current) {
                            clearInterval(pollIntervalRef.current);
                            pollIntervalRef.current = null;
                        }
                        // Refresh the tree
                        await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
                    } else if (data.status === 'error') {
                        // Stop polling on error
                        if (pollIntervalRef.current) {
                            clearInterval(pollIntervalRef.current);
                            pollIntervalRef.current = null;
                        }
                        setError(data.message || 'Processing failed');
                    }
                } catch (err) {
                    console.error('Status poll error:', err);
                }
            };

            // Poll every 2 seconds
            pollIntervalRef.current = window.setInterval(pollStatus, 2000);
            // Initial poll
            pollStatus();

            return () => {
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
            };
        }
    }, [mode, processing?.jobId, queryClient]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, []);

    // Early return AFTER all hooks
    if (!isOpen) return null;

    const handleClose = () => {
        // Stop any polling
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }
        setMode('select');
        setSelectedFile(null);
        setTopic('');
        setDocTitle('');
        setIsUploading(false);
        setProcessing(null);
        setError(null);
        onClose();
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            setSelectedFile(files[0]);
        }
    };

    const handleChooseFile = () => {
        fileInputRef.current?.click();
    };

    const acceptedTypes = mode === 'document'
        ? '.pdf,.doc,.docx,.txt,.md'
        : '.mp3,.wav,.m4a,.flac,.ogg,.webm';

    const supportedText = mode === 'document'
        ? 'Supported file types: PDF, .doc, .docx, .txt, Markdown'
        : 'Supported file types: MP3, WAV, M4A, FLAC, OGG, WebM';

    const handleUpload = async () => {
        if (!selectedFile) return;

        setIsUploading(true);
        setError(null);

        try {
            if (mode === 'document') {
                // Upload document to backend
                const title = docTitle.trim() || selectedFile.name.replace(/\.[^/.]+$/, '');

                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('title', title);
                formData.append('moduleId', moduleId.toString());

                const response = await fetch('/api/audio/upload-document', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || 'Upload failed');
                }

                if (data.success) {
                    // Refresh the explorer tree to show the new note
                    await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
                    // Show success and close
                    setProcessing({
                        jobId: '',
                        status: 'complete',
                        progress: 100,
                        message: `Document "${title}" uploaded successfully!`,
                        result: { pdfUrl: data.documentUrl }
                    });
                    setMode('processing');
                } else {
                    throw new Error(data.message || 'Upload failed');
                }
            } else if (mode === 'voice') {
                if (!topic.trim()) {
                    setError('Please enter a topic for the notes');
                    setIsUploading(false);
                    return;
                }

                // Start AI processing pipeline
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('topic', topic);
                formData.append('moduleId', moduleId.toString());

                const response = await fetch('/api/audio/process-pipeline', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || 'Failed to start processing');
                }

                if (data.jobId) {
                    // Switch to processing mode with status polling
                    setProcessing({
                        jobId: data.jobId,
                        status: 'pending',
                        progress: 0,
                        message: 'Starting AI processing...',
                    });
                    setMode('processing');
                } else {
                    throw new Error('Failed to start processing');
                }
            }
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setIsUploading(false);
        }
    };

    const getStatusIcon = () => {
        if (!processing) return null;

        if (processing.status === 'complete') {
            return <CheckCircle size={48} className="text-success" />;
        } else if (processing.status === 'error' || error) {
            return <AlertCircle size={48} className="text-error" />;
        } else {
            return <Loader2 size={48} className="spinning text-accent" />;
        }
    };

    const getStatusLabel = () => {
        if (!processing) return '';

        switch (processing.status) {
            case 'pending': return 'Starting...';
            case 'transcribing': return 'Transcribing audio...';
            case 'refining': return 'Refining transcript...';
            case 'summarizing': return 'Generating notes...';
            case 'generating_pdf': return 'Creating PDF...';
            case 'complete': return 'Complete!';
            case 'error': return 'Error';
            default: return processing.status;
        }
    };

    // Render processing state
    if (mode === 'processing') {
        return (
            <div className="dialog-overlay">
                <div className="dialog upload-dialog" onClick={(e) => e.stopPropagation()}>
                    <div className="dialog-header">
                        <h2 className="dialog-title">
                            {processing?.status === 'complete' ? 'Upload Complete' : 'Processing...'}
                        </h2>
                        {processing?.status === 'complete' && (
                            <button className="dialog-close" onClick={handleClose}>
                                <X size={20} />
                            </button>
                        )}
                    </div>

                    <div className="dialog-body">
                        <div className="processing-status">
                            <div className="processing-icon">
                                {getStatusIcon()}
                            </div>

                            <div className="processing-label">
                                <span className={processing && processing.status !== 'complete' && processing.status !== 'error' ? 'animate-shine typewriter-text' : ''}>
                                    {getStatusLabel()}
                                </span>
                            </div>

                            {processing && processing.status !== 'complete' && processing.status !== 'error' && (
                                <div className="progress-bar-container">
                                    <div
                                        className="progress-bar"
                                        style={{ width: `${processing.progress}%` }}
                                    />
                                </div>
                            )}

                            <div className="processing-message">
                                {error || processing?.message}
                            </div>

                            {processing?.status === 'complete' && processing?.result?.pdfUrl && (
                                <div className="processing-actions">
                                    <a
                                        href={processing.result.pdfUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn btn-primary"
                                    >
                                        View PDF
                                    </a>
                                    <button className="btn btn-secondary" onClick={handleClose}>
                                        Close
                                    </button>
                                </div>
                            )}

                            {(processing?.status === 'error' || error) && (
                                <div className="processing-actions">
                                    <button className="btn btn-secondary" onClick={() => {
                                        setMode('voice');
                                        setProcessing(null);
                                        setError(null);
                                    }}>
                                        Try Again
                                    </button>
                                    <button className="btn btn-ghost" onClick={handleClose}>
                                        Close
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="dialog-overlay" onClick={handleClose}>
            <div className="dialog upload-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="dialog-header">
                    <h2 className="dialog-title">
                        {mode === 'select' ? 'Upload Notes' : mode === 'document' ? 'Upload Document' : 'Upload Voice Recording'}
                    </h2>
                    <button className="dialog-close" onClick={handleClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="dialog-body">
                    {/* Error message */}
                    {error && (
                        <div className="upload-error">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}

                    {/* Module info */}
                    <div className="upload-module-info">
                        <span className="text-muted">Uploading to:</span>
                        <span className="text-accent">{moduleName}</span>
                    </div>

                    {mode === 'select' ? (
                        /* Option selection mode */
                        <div className="upload-options">
                            <button
                                className="upload-option-card"
                                onClick={() => setMode('document')}
                            >
                                <div className="upload-option-icon">
                                    <FileText size={32} />
                                </div>
                                <div className="upload-option-content">
                                    <h3>Upload Document</h3>
                                    <p>Upload existing notes as PDF, Word, or text files</p>
                                </div>
                            </button>

                            <button
                                className="upload-option-card"
                                onClick={() => setMode('voice')}
                            >
                                <div className="upload-option-icon voice">
                                    <Mic size={32} />
                                </div>
                                <div className="upload-option-content">
                                    <h3>AI Note Generator</h3>
                                    <p>Upload a voice recording and let AI create notes for you</p>
                                </div>
                            </button>
                        </div>
                    ) : (
                        /* Upload zone mode */
                        <>
                            {mode === 'document' && (
                                <div className="form-group">
                                    <label className="form-label">Note Title (optional)</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="Leave empty to use filename..."
                                        value={docTitle}
                                        onChange={(e) => setDocTitle(e.target.value)}
                                    />
                                </div>
                            )}

                            {mode === 'voice' && (
                                <div className="form-group">
                                    <label className="form-label">Topic / Title <span className="text-error">*</span></label>
                                    <input
                                        type="text"
                                        className={`form-input ${selectedFile && !topic.trim() ? 'input-error' : ''}`}
                                        placeholder="Enter the topic for these notes..."
                                        value={topic}
                                        onChange={(e) => setTopic(e.target.value)}
                                        required
                                    />
                                    {selectedFile && !topic.trim() && (
                                        <span className="form-error">Title is required to generate notes</span>
                                    )}
                                </div>
                            )}

                            <div
                                className={`upload-zone ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                onClick={() => !selectedFile && handleChooseFile()}
                                style={{ cursor: selectedFile ? 'default' : 'pointer' }}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept={acceptedTypes}
                                    onChange={handleFileSelect}
                                    style={{ display: 'none' }}
                                />

                                {selectedFile ? (
                                    <div className="upload-file-preview">
                                        <FileUp size={32} className="text-accent" />
                                        <span className="upload-file-name">{selectedFile.name}</span>
                                        <span className="upload-file-size">
                                            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                                        </span>
                                        <button
                                            className="btn btn-ghost"
                                            onClick={() => setSelectedFile(null)}
                                        >
                                            Remove
                                        </button>
                                    </div>
                                ) : (
                                    <>
                                        <div className="upload-zone-icon">
                                            <Upload size={32} />
                                        </div>
                                        <p className="upload-zone-title">Upload sources</p>
                                        <p className="upload-zone-text">
                                            Drag and drop or click to upload
                                        </p>
                                    </>
                                )}
                            </div>

                            <p className="upload-supported-types">{supportedText}</p>

                            <div className="upload-actions">
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => {
                                        setMode('select');
                                        setSelectedFile(null);
                                        setError(null);
                                    }}
                                >
                                    Back
                                </button>
                                <button
                                    className="btn btn-primary"
                                    onClick={handleUpload}
                                    disabled={!selectedFile || isUploading || (mode === 'voice' && !topic.trim())}
                                >
                                    {isUploading ? (
                                        <>
                                            <Loader2 size={16} className="spinning" />
                                            Processing...
                                        </>
                                    ) : (
                                        <>
                                            <Upload size={16} />
                                            {mode === 'voice' ? 'Generate Notes' : 'Upload'}
                                        </>
                                    )}
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
