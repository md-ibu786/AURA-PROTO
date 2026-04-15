/**
 * ============================================================================
 * FILE: ProviderSettingsSection.tsx
 * LOCATION: frontend/src/features/settings/components/ProviderSettingsSection.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Component displaying status cards for each configured AI provider.
 *    Shows provider information, available model counts, and configuration status.
 *
 * ROLE IN PROJECT:
 *    Part of the settings configuration system:
 *    - Displays provider cards with icons and model counts
 *    - Indicates provider availability status (active/no-key/unavailable)
 *    - Helps administrators quickly identify which providers are configured
 *    - Shows loading states while fetching model information
 *    - Integrates with API key status for complete visibility
 *
 * KEY COMPONENTS:
 *    - ProviderSettingsSection: Main container component
 *    - ProviderCard: Individual provider status card
 *    - PROVIDERS: Configuration array defining provider metadata
 *    - useAllModels, useApiKeyStatus: Custom hooks for data fetching
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react
 *    - Internal: features/settings/hooks/useSettingsApi, lib/cn, types/settings
 *
 * USAGE:
 *    <ProviderSettingsSection />
 *    Used within SettingsPage for provider overview section
 * ============================================================================
 */

import { Cpu, Globe, Server, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { useAllModels, useApiKeyStatus } from '../hooks/useSettingsApi';
import { cn } from '@/lib/cn';
import { ProviderType } from '@/types/settings';

const PROVIDERS: { id: ProviderType; label: string; icon: React.ElementType; needsKey: boolean }[] = [
    { id: 'vertex_ai', label: 'Vertex AI', icon: Cpu, needsKey: true },
    { id: 'openrouter', label: 'OpenRouter', icon: Globe, needsKey: true },
    { id: 'ollama', label: 'Ollama', icon: Server, needsKey: false }
];

export function ProviderSettingsSection() {
    const { data: models = [], isLoading } = useAllModels(true);

    return (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PROVIDERS.map(provider => {
                const providerModels = models.filter(m => m.provider === provider.id);
                return (
                    <ProviderCard
                        key={provider.id}
                        provider={provider}
                        modelCount={providerModels.length}
                        isLoading={isLoading}
                    />
                );
            })}
        </div>
    );
}

function ProviderCard({ 
    provider, 
    modelCount, 
    isLoading 
}: { 
    provider: typeof PROVIDERS[0]; 
    modelCount: number;
    isLoading: boolean;
}) {
    const { data: keyStatus, isLoading: keyLoading } = useApiKeyStatus(
        provider.needsKey ? provider.id : ''
    );

    const Icon = provider.icon;
    const hasModels = modelCount > 0;
    
    // Determine status
    let status: 'active' | 'no-key' | 'unavailable' = 'unavailable';
    if (hasModels) {
        status = 'active';
    } else if (provider.needsKey && !keyLoading && (!keyStatus || keyStatus.masked_key === null)) {
        status = 'no-key';
    }

    if (isLoading) {
        return (
            <div className="bg-card/50 rounded-xl border border-border p-4 animate-pulse">
                <div className="h-6 bg-muted/50 rounded w-1/2 mb-4"></div>
                <div className="h-4 bg-muted/50 rounded w-1/3 mb-2"></div>
                <div className="h-4 bg-muted/50 rounded w-1/4"></div>
            </div>
        );
    }

    return (
        <div className="bg-card rounded-xl border border-border p-4 flex flex-col h-full">
            <div className="flex items-center gap-2 mb-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                    <Icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-semibold text-sm sm:text-base">{provider.label}</h3>
            </div>
            
            <div className="mt-auto space-y-3">
                <div className="text-2xl font-bold">
                    {modelCount} <span className="text-sm font-normal text-muted-foreground">models</span>
                </div>
                
                <div className={cn(
                    "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium w-fit",
                    status === 'active' && "text-green-500 bg-green-500/10",
                    status === 'no-key' && "text-yellow-500 bg-yellow-500/10",
                    status === 'unavailable' && "text-muted-foreground bg-muted/20"
                )}>
                    {status === 'active' && <CheckCircle className="w-3.5 h-3.5" />}
                    {status === 'no-key' && <AlertTriangle className="w-3.5 h-3.5" />}
                    {status === 'unavailable' && <XCircle className="w-3.5 h-3.5" />}
                    
                    <span>
                        {status === 'active' && "Active"}
                        {status === 'no-key' && "No API Key"}
                        {status === 'unavailable' && "Unavailable"}
                    </span>
                </div>
            </div>
        </div>
    );
}
