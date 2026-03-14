/**
 * ============================================================================
 * FILE: useModelList.ts
 * LOCATION: frontend/src/features/settings/hooks/useModelList.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Pure function to group models and React hook to use them
 *
 * ROLE IN PROJECT:
 *    Provides groupModelsByProvider function to convert flat model lists into
 *    hierarchical provider/vendor structures for UI selection components.
 *    Also exports a convenience hook useGroupedModels for React components
 *
 * KEY COMPONENTS:
 *    - groupModelsByProvider: Pure function grouping models hierarchically
 *    - useGroupedModels: React hook returning grouped models
 *    - PROVIDER_LABELS: Display names for each provider type
 *    - KNOWN_VENDORS: Mapping of vendor IDs to display labels
 *
 * DEPENDENCIES:
 *    - External: react (useMemo)
 *    - Internal: @/types/settings
 *
 * USAGE:
 *    const grouped = groupModelsByProvider(models);
 *    const grouped = useGroupedModels(models);
 * ============================================================================
 */
import { useMemo } from 'react';
import type { ModelInfo, ModelGroup, VendorGroup, ProviderType } from '@/types/settings';

const PROVIDER_LABELS: Record<ProviderType, string> = {
    vertex_ai: 'Vertex AI',
    openrouter: 'OpenRouter',
    ollama: 'Ollama'
};

const KNOWN_VENDORS: Record<string, string> = {
    anthropic: 'Anthropic',
    google: 'Google',
    openai: 'OpenAI',
    deepseek: 'DeepSeek',
    'meta-llama': 'Meta Llama'
};

function getVendorLabel(vendor: string): string {
    if (PROVIDER_LABELS[vendor as ProviderType]) return PROVIDER_LABELS[vendor as ProviderType];
    if (KNOWN_VENDORS[vendor]) return KNOWN_VENDORS[vendor];
    return vendor.charAt(0).toUpperCase() + vendor.slice(1);
}

export function groupModelsByProvider(models: ModelInfo[]): ModelGroup[] {
    if (!models || models.length === 0) return [];

    const providerMap = new Map<ProviderType, ModelInfo[]>();
    for (const model of models) {
        if (!providerMap.has(model.provider)) {
            providerMap.set(model.provider, []);
        }
        providerMap.get(model.provider)!.push(model);
    }

    const result: ModelGroup[] = [];

    for (const [provider, providerModels] of providerMap.entries()) {
        const vendorMap = new Map<string, ModelInfo[]>();
        
        for (const model of providerModels) {
            let vendor = provider as string;
            
            if (provider === 'openrouter') {
                const slashIndex = model.name.indexOf('/');
                if (slashIndex > -1) {
                    vendor = model.name.substring(0, slashIndex);
                }
            }
            
            if (!vendorMap.has(vendor)) {
                vendorMap.set(vendor, []);
            }
            vendorMap.get(vendor)!.push(model);
        }

        const vendors: VendorGroup[] = [];
        for (const [vendor, vModels] of vendorMap.entries()) {
            const sortedModels = [...vModels].sort((a, b) => {
                const nameA = a.display_name ?? a.name;
                const nameB = b.display_name ?? b.name;
                return nameA.localeCompare(nameB);
            });
            
            vendors.push({
                vendor,
                vendorLabel: getVendorLabel(vendor),
                models: sortedModels
            });
        }
        
        vendors.sort((a, b) => a.vendorLabel.localeCompare(b.vendorLabel));

        result.push({
            provider,
            providerLabel: PROVIDER_LABELS[provider] || provider,
            vendors
        });
    }

    result.sort((a, b) => a.providerLabel.localeCompare(b.providerLabel));

    return result;
}

export function useGroupedModels(models: ModelInfo[] | undefined) {
    return useMemo(() => {
        if (!models) return [];
        return groupModelsByProvider(models);
    }, [models]);
}
