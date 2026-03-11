/**
 * ============================================================================
 * FILE: SettingsPage.tsx
 * LOCATION: frontend/src/pages/SettingsPage.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Admin-only page for provider configuration, default models, and API key management.
 *
 * ROLE IN PROJECT:
 *    Central interface for system-wide AI settings in AURA-NOTES-MANAGER.
 *    Allows administrators to:
 *    - View available AI providers and model counts
 *    - Set default models for Chat, Embeddings, and Entity Extraction
 *    - Store and validate API keys for Vertex AI and OpenRouter
 *
 * DEPENDENCIES:
 *    - External: react-router-dom, lucide-react
 *    - Internal: features/settings/components/*, styles/index.css
 *
 * USAGE:
 *    Route: /settings (protected, admin-only)
 * ============================================================================
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { ProviderSettingsSection } from '../features/settings/components/ProviderSettingsSection';
import { DefaultModelSection } from '../features/settings/components/DefaultModelSection';
import { ApiKeyManager } from '../features/settings/components/ApiKeyManager';
import '../styles/index.css';

export function SettingsPage() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-[#0A0A0A] text-foreground p-4 md:p-8">
            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                {/* Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2 mb-2">
                             <button 
                                onClick={() => navigate(-1)}
                                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                                title="Back"
                            >
                                <ArrowLeft className="w-5 h-5 text-muted-foreground" />
                            </button>
                            <h1 className="text-3xl font-bold tracking-tight text-[#FFD400]">Settings</h1>
                        </div>
                        <p className="text-muted-foreground">
                            Configure AI providers, default models, and API credentials.
                        </p>
                    </div>
                </div>

                {/* Sections */}
                <div className="space-y-12">
                    {/* Provider Status */}
                    <section className="space-y-4">
                        <div>
                            <h2 className="text-xl font-semibold">Provider Configuration</h2>
                            <p className="text-sm text-muted-foreground">Overview of available AI providers and model counts.</p>
                        </div>
                        <ProviderSettingsSection />
                    </section>

                    {/* Default Models */}
                    <section className="space-y-4">
                        <div>
                            <h2 className="text-xl font-semibold">Default Models</h2>
                            <p className="text-sm text-muted-foreground">Set global defaults for different system use cases.</p>
                        </div>
                        <DefaultModelSection />
                    </section>

                    {/* API Credentials */}
                    <section className="space-y-4">
                        <div>
                            <h2 className="text-xl font-semibold">API Credentials</h2>
                            <p className="text-sm text-muted-foreground">Manage keys and authentication for external providers.</p>
                        </div>
                        <ApiKeyManager />
                    </section>
                </div>
            </div>
        </div>
    );
}
