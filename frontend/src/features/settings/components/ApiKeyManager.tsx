/**
 * ============================================================================
 * FILE: ApiKeyManager.tsx
 * LOCATION: frontend/src/features/settings/components/ApiKeyManager.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Component for managing API keys for AI providers that require authentication.
 *    Supports storing, validating, and deleting API keys securely.
 *
 * ROLE IN PROJECT:
 *    Part of the settings configuration system:
 *    - Displays API key status for each provider (configured/not configured)
 *    - Allows secure storage of API keys (masked display)
 *    - Provides key validation against provider APIs
 *    - Supports key deletion with confirmation
 *    - Handles loading and error states gracefully
 *
 * KEY COMPONENTS:
 *    - ApiKeyManager: Main container component rendering provider key cards
 *    - ProviderKeyCard: Individual provider card with key management UI
 *    - PROVIDERS: Configuration array for supported providers
 *    - useApiKeyStatus, useStoreApiKey, useDeleteApiKey, useValidateApiKey: Custom hooks
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react
 *    - Internal: features/settings/hooks/useSettingsApi, lib/cn, types/settings
 *
 * USAGE:
 *    <ApiKeyManager />
 *    Used within SettingsPage for API key management section
 * ============================================================================
 */

import React, { useState } from 'react';
import { 
    Eye, EyeOff, Key, Trash2, CheckCircle, 
    XCircle, AlertCircle, Loader2, Shield
} from 'lucide-react';
import { 
    useApiKeyStatus, 
    useStoreApiKey, 
    useDeleteApiKey, 
    useValidateApiKey 
} from '../hooks/useSettingsApi';
import { cn } from '@/lib/cn';
import { ProviderType } from '@/types/settings';

const PROVIDERS: { id: ProviderType; label: string }[] = [
    { id: 'vertex_ai', label: 'Vertex AI' },
    { id: 'openrouter', label: 'OpenRouter' }
];

export function ApiKeyManager() {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {PROVIDERS.map(provider => (
                <ProviderKeyCard key={provider.id} provider={provider} />
            ))}
        </div>
    );
}

function ProviderKeyCard({ provider }: { provider: typeof PROVIDERS[0] }) {
    const { data: status, isLoading: loadingStatus } = useApiKeyStatus(provider.id);
    const storeMutation = useStoreApiKey(provider.id);
    const deleteMutation = useDeleteApiKey(provider.id);
    const validateMutation = useValidateApiKey(provider.id);
    
    const [inputValue, setInputValue] = useState('');
    const [showInput, setShowInput] = useState(false);
    const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
    const [validationResult, setValidationResult] = useState<{valid: boolean; message?: string} | null>(null);

    const hasKey = status && status.masked_key !== null;

    const handleStore = (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim()) return;
        
        storeMutation.mutate(inputValue.trim(), {
            onSuccess: () => {
                setInputValue('');
                setValidationResult(null);
            }
        });
    };

    const handleDelete = () => {
        if (!isConfirmingDelete) {
            setIsConfirmingDelete(true);
            return;
        }
        
        deleteMutation.mutate(undefined, {
            onSuccess: () => {
                setIsConfirmingDelete(false);
                setValidationResult(null);
            }
        });
    };

    const handleValidate = () => {
        setValidationResult(null);
        validateMutation.mutate(undefined, {
            onSuccess: (data) => {
                setValidationResult({
                    valid: data.valid,
                    message: data.error
                });
            },
            onError: () => {
                setValidationResult({
                    valid: false,
                    message: 'Network error or server unavailable'
                });
            }
        });
    };

    if (loadingStatus) {
        return (
            <div className="bg-card/50 rounded-xl border border-border p-4 sm:p-5 animate-pulse">
                <div className="h-6 w-32 bg-muted/50 rounded mb-4"></div>
                <div className="h-10 bg-muted/50 rounded mb-4"></div>
                <div className="h-8 w-24 bg-muted/50 rounded"></div>
            </div>
        );
    }

    return (
        <div className="bg-card rounded-xl border border-border p-4 sm:p-5 flex flex-col h-full relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-muted-foreground" />
                    <h3 className="font-semibold">{provider.label} Key</h3>
                </div>
                
                {hasKey ? (
                    <div className="flex items-center gap-1.5 px-2 py-0.5 bg-green-500/10 text-green-500 rounded-full text-xs font-medium">
                        <CheckCircle className="w-3 h-3" /> Configured
                    </div>
                ) : (
                    <div className="flex items-center gap-1.5 px-2 py-0.5 bg-yellow-500/10 text-yellow-500 rounded-full text-xs font-medium">
                        <AlertCircle className="w-3 h-3" /> Not Configured
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="flex-1 space-y-4">
                {hasKey ? (
                    <>
                        <div className="bg-card/50 border border-border rounded-lg p-3 flex items-center justify-between">
                            <div className="flex flex-col">
                                <span className="text-xs text-muted-foreground mb-1">Masked Key</span>
                                <code className="text-sm font-mono">{status.masked_key}</code>
                            </div>
                            {status.valid !== null && (
                                <div title={status.valid ? "Key is valid" : "Key is invalid"}>
                                    {status.valid ? (
                                        <CheckCircle className="w-5 h-5 text-green-500" />
                                    ) : (
                                        <XCircle className="w-5 h-5 text-destructive" />
                                    )}
                                </div>
                            )}
                        </div>

                        {validationResult && (
                            <div className={cn(
                                "p-2 rounded text-xs flex items-start gap-1.5",
                                validationResult.valid ? "bg-green-500/10 text-green-500" : "bg-destructive/10 text-destructive"
                            )}>
                                {validationResult.valid ? <CheckCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" /> : <XCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />}
                                <span>{validationResult.valid ? "Key validated successfully" : validationResult.message || "Invalid key"}</span>
                            </div>
                        )}

                        <div className="flex flex-wrap gap-2 mt-auto pt-4">
                            <button
                                onClick={handleValidate}
                                disabled={validateMutation.isPending}
                                className="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-medium rounded transition-colors flex items-center gap-1.5 disabled:opacity-50"
                            >
                                {validateMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Shield className="w-3.5 h-3.5" />}
                                Validate
                            </button>
                            
                            <button
                                onClick={handleDelete}
                                disabled={deleteMutation.isPending}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center gap-1.5 disabled:opacity-50",
                                    isConfirmingDelete 
                                        ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" 
                                        : "bg-destructive/10 text-destructive hover:bg-destructive/20"
                                )}
                            >
                                {deleteMutation.isPending ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <Trash2 className="w-3.5 h-3.5" />
                                )}
                                {isConfirmingDelete ? "Confirm Delete?" : "Delete Key"}
                            </button>

                            {isConfirmingDelete && (
                                <button
                                    onClick={() => setIsConfirmingDelete(false)}
                                    className="px-3 py-1.5 bg-muted text-muted-foreground hover:text-foreground text-xs font-medium rounded transition-colors"
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    </>
                ) : (
                    <form onSubmit={handleStore} className="flex flex-col h-full space-y-3">
                        <p className="text-xs text-muted-foreground">
                            Enter an API key to enable models from {provider.label}.
                        </p>
                        
                        <div className="relative">
                            <Key className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <input
                                type={showInput ? "text" : "password"}
                                placeholder="Enter API Key"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                className="w-full pl-9 pr-10 py-2 text-sm bg-card/50 border border-border focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/50 rounded-md font-mono"
                            />
                            <button
                                type="button"
                                onClick={() => setShowInput(!showInput)}
                                className="absolute right-2 top-2 p-0.5 text-muted-foreground hover:text-foreground transition-colors"
                            >
                                {showInput ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>
                        
                        <div className="mt-auto pt-4">
                            <button
                                type="submit"
                                disabled={!inputValue.trim() || storeMutation.isPending}
                                className="w-full px-3 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md transition-colors hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
                            >
                                {storeMutation.isPending ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" /> Saving...
                                    </>
                                ) : (
                                    "Save Key"
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>
            
            {/* Loading Overlay */}
            {(storeMutation.isPending || deleteMutation.isPending) && (
                <div className="absolute inset-0 bg-background/50 backdrop-blur-[1px] flex items-center justify-center z-10">
                    <Loader2 className="w-6 h-6 text-primary animate-spin" />
                </div>
            )}
        </div>
    );
}
