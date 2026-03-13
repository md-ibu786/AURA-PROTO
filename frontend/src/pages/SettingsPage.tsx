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

                                <div className="space-y-8 sm:space-y-6">
                                    {/* Notes Manager Status */}
                                    <div className="space-y-4">
                                        <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                                            <Shield className="w-3 h-3" />
                                            Notes Manager
                                        </h3>
                                        <div className="space-y-4">
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

                                            {/* Redis Status */}
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex items-start gap-3">
                                                    <RefreshCw className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                                    <div>
                                                        <p className="font-medium text-sm sm:text-base">Redis Cache</p>
                                                        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                                                            Task queue & caching
                                                        </p>
                                                    </div>
                                                </div>
                                                <StatusBadge
                                                    status={healthQuery.data?.neo4j_connected ? 'ready' : 'not ready'}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="border-t border-border pt-6 sm:pt-4" />

                                    {/* Chat Status */}
                                    <div className="space-y-4">
                                        <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                                            <Zap className="w-3 h-3" />
                                            AURA Chat
                                        </h3>
                                        <div className="space-y-4">
                                            {/* API Status */}
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex items-start gap-3">
                                                    <Cpu className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                                    <div>
                                                        <p className="font-medium text-sm sm:text-base">Chat Server</p>
                                                        <p className="text-xs sm:text-sm text-muted-foreground">
                                                            Version {healthQuery.data?.chat?.version || 'unknown'}
                                                        </p>
                                                    </div>
                                                </div>
                                                <StatusBadge
                                                    status={healthQuery.data?.chat?.status || 'disconnected'}
                                                />
                                            </div>

                                            {/* Neo4j Status */}
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex items-start gap-3">
                                                    <Database className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                                    <div>
                                                        <p className="font-medium text-sm sm:text-base">Neo4j Graph</p>
                                                        <p className="text-xs sm:text-sm text-muted-foreground">
                                                            Knowledge graph database
                                                        </p>
                                                    </div>
                                                </div>
                                                <StatusBadge
                                                    status={healthQuery.data?.chat?.neo4j_connected ? 'connected' : 'disconnected'}
                                                />
                                            </div>

                                            {/* Semantic Router Status */}
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex items-start gap-3">
                                                    <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground shrink-0 mt-1 sm:mt-0.5" />
                                                    <div>
                                                        <p className="font-medium text-sm sm:text-base">Semantic Router</p>
                                                        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                                                            Query intent classification
                                                        </p>
                                                    </div>
                                                </div>
                                                <StatusBadge
                                                    status={healthQuery.data?.chat?.semantic_router || 'not ready'}
                                                />
                                            </div>
                                        </div>
                                    </div>
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
