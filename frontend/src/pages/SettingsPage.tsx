// SettingsPage.tsx
// Admin settings page with provider configuration, default models, API credentials, and system status

// Mirrors AURA-CHAT SettingsPage.tsx structure with 2-column layout.
// Features main content (2/3) + sidebar (1/3) with system status and about section.

// @see: features/settings/components/ - ProviderSettingsSection, DefaultModelSection, ApiKeyManager
// @see: api/client.ts - checkHealth function for system status monitoring

import { useQuery } from '@tanstack/react-query';
import {
    Settings,
    Database,
    Zap,
    CheckCircle,
    XCircle,
    RefreshCw,
    Shield,
    Cpu,
    Key
} from 'lucide-react';
import { checkHealth } from '../api/client';
import { cn } from '@/lib/cn';
import { ProviderSettingsSection } from '../features/settings/components/ProviderSettingsSection';
import { DefaultModelSection } from '../features/settings/components/DefaultModelSection';
import { ApiKeyManager } from '../features/settings/components/ApiKeyManager';

import { AdminHeader } from '../components/layout/AdminHeader';

export function SettingsPage() {
    const healthQuery = useQuery({
        queryKey: ['health'],
        queryFn: checkHealth,
        refetchInterval: 30000, // Refresh every 30 seconds
    });

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <AdminHeader 
                title="Settings" 
                subtitle="Configure AURA and view system status" 
            />

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                <div className="max-w-7xl mx-auto">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                        {/* Status & Information - Sidebar (1/3) */}
                        <div className="space-y-6 lg:order-2">
                            {/* System Status */}
                            <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2">
                                        <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                                        System Status
                                    </h2>
                                    <button
                                        onClick={() => healthQuery.refetch()}
                                        disabled={healthQuery.isFetching}
                                        className="text-muted-foreground hover:text-foreground transition-colors p-2 -mr-2 sm:p-0 sm:mr-0 min-h-11 sm:min-h-0 flex items-center justify-center"
                                    >
                                        <RefreshCw className={cn("w-4 h-4 sm:w-5 sm:h-5", healthQuery.isFetching && "animate-spin")} />
                                    </button>
                                </div>

                                <div className="space-y-5 sm:space-y-4">
                                    {/* API Status */}
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex items-start gap-3">
                                            <Settings className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                            <div>
                                                <p className="font-medium text-sm sm:text-base">API Server</p>
                                                <p className="text-xs sm:text-sm text-muted-foreground">
                                                    Version {healthQuery.data?.version || 'unknown'}
                                                </p>
                                            </div>
                                        </div>
                                        <StatusBadge
                                            status={healthQuery.data?.status === 'healthy' ? 'healthy' : 'degraded'}
                                        />
                                    </div>

                                    {/* Firestore Status */}
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex items-start gap-3">
                                            <Database className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                            <div>
                                                <p className="font-medium text-sm sm:text-base">Firestore Database</p>
                                                <p className="text-xs sm:text-sm text-muted-foreground">
                                                    Cloud database connection
                                                </p>
                                            </div>
                                        </div>
                                        <StatusBadge
                                            status={healthQuery.data?.services_ready ? 'connected' : 'disconnected'}
                                        />
                                    </div>

                                    {/* Services Status */}
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex items-start gap-3">
                                            <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                            <div>
                                                <p className="font-medium text-sm sm:text-base">Backend Services</p>
                                                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                                                    Firestore, Redis, AudioPipeline
                                                </p>
                                            </div>
                                        </div>
                                        <StatusBadge
                                            status={healthQuery.data?.neo4j_connected ? 'ready' : 'not ready'}
                                        />
                                    </div>
                                </div>
                            </section>

                            {/* About */}
                            <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                                <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4">About AURA</h2>
                                <p className="text-sm sm:text-base text-muted-foreground mb-3 sm:mb-4 leading-relaxed">
                                    AURA Notes Manager is a staff portal for managing academic content,
                                    organizing modules, processing documents into knowledge graphs, and
                                    publishing materials for students.
                                </p>
                                <div className="space-y-2.5 sm:space-y-2 text-xs sm:text-sm text-muted-foreground">
                                    <p className="flex items-start gap-2"><span className="mt-0.5 shrink-0">•</span> <span>Organize departments, semesters, and modules</span></p>
                                    <p className="flex items-start gap-2"><span className="mt-0.5 shrink-0">•</span> <span>Upload and manage notes and documents</span></p>
                                    <p className="flex items-start gap-2"><span className="mt-0.5 shrink-0">•</span> <span>Audio-to-notes pipeline with AI transcription</span></p>
                                    <p className="flex items-start gap-2"><span className="mt-0.5 shrink-0">•</span> <span>Knowledge graph processing and publishing</span></p>
                                </div>
                            </section>
                        </div>

                        {/* Main Configuration - Primary Column (2/3) */}
                        <div className="lg:col-span-2 space-y-6 lg:order-1">
                            {/* Provider Configuration */}
                            <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                                <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2 mb-4">
                                    <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                                    Provider Configuration
                                </h2>
                                <ProviderSettingsSection />
                            </section>

                            {/* Default Models */}
                            <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                                <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2 mb-4">
                                    <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                                    Default Models
                                </h2>
                                <DefaultModelSection />
                            </section>

                            {/* API Keys */}
                            <section className="bg-card rounded-xl border border-border p-4 sm:p-6">
                                <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2 mb-4">
                                    <Key className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                                    API Keys
                                </h2>
                                <ApiKeyManager />
                            </section>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const isPositive = ['healthy', 'connected', 'ready'].includes(status);

    return (
        <div className={cn(
            "flex items-center gap-1.5 sm:gap-2 sm:px-3 sm:py-1 sm:rounded-full text-xs sm:text-sm w-fit",
            isPositive ? "text-green-500 sm:bg-green-500/10" : "text-destructive sm:bg-destructive/10"
        )}>
            {isPositive ? (
                <CheckCircle className="w-5 h-5 sm:w-4 sm:h-4 shrink-0" />
            ) : (
                <XCircle className="w-5 h-5 sm:w-4 sm:h-4 shrink-0" />
            )}
            <span className="hidden sm:inline capitalize whitespace-nowrap">{status}</span>
        </div>
    );
}
