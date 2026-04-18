/**
 * ============================================================================
 * FILE: DefaultModelSection.tsx
 * LOCATION: frontend/src/features/settings/components/DefaultModelSection.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Component for configuring default AI models for different use cases.
 *    Allows administrators to set preferred models for chat, embeddings,
 *    and entity extraction tasks.
 *
 * ROLE IN PROJECT:
 *    Part of the settings configuration system:
 *    - Displays current default model settings per use case
 *    - Provides hierarchical model picker for selection
 *    - Groups models by provider for easier navigation
 *    - Shows real-time update feedback (pending/success/error states)
 *    - Syncs with server state to prevent conflicts
 *
 * KEY COMPONENTS:
 *    - DefaultModelSection: Main container managing data fetching
 *    - UseCaseSection: Individual use case configuration section
 *    - USE_CASES: Configuration array defining use cases and descriptions
 *    - HierarchicalModelPicker: Reusable model selection component
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react
 *    - Internal: features/settings/hooks/useSettingsApi, features/settings/hooks/useModelList,
 *                features/settings/components/HierarchicalModelPicker, types/settings
 *
 * USAGE:
 *    <DefaultModelSection />
 *    Used within SettingsPage for default model configuration section
 * ============================================================================
 */

import { useState, useEffect } from 'react';
import { useDefaults, useAllModels, useUpdateDefault } from '../hooks/useSettingsApi';
import { groupModelsByProvider } from '../hooks/useModelList';
import { HierarchicalModelPicker } from './HierarchicalModelPicker';
import { ChatModelsSection } from './ChatModelsSection';
import { UseCase, ModelGroup, ModelInfo } from '@/types/settings';
import { Check, AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/cn';

const USE_CASES: { id: UseCase; label: string; description: string }[] = [
    { id: 'chat', label: 'Chat Model', description: 'Used for conversational responses and RAG' },
    { id: 'embeddings', label: 'Embeddings Model', description: 'Used for document indexing and vector search' },
    { id: 'entity_extraction', label: 'Entity Extraction Model', description: 'Used for building knowledge graphs from documents' },
    { id: 'gatekeeper', label: 'Gatekeeper Model', description: 'Used for query validation and access control' },
    { id: 'relationship_extraction', label: 'Relationship Extraction Model', description: 'Used for extracting relationships between entities in documents' }
];

const USE_CASE_MODEL_TYPES: Record<UseCase, 'generation' | 'embedding'> = {
    chat: 'generation',
    embeddings: 'embedding',
    entity_extraction: 'generation',
    gatekeeper: 'generation',
    relationship_extraction: 'generation',
};

export function DefaultModelSection() {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const {
        data: defaults,
        isLoading: loadingDefaults,
        isFetching: isFetchingDefaults,
    } = useDefaults();
    const {
        data: allModels,
        isLoading: loadingModels,
        isFetching: isFetchingModels,
        refetch: refetchModels,
    } = useAllModels();
    const modelList = allModels || [];
    const shouldShowSkeleton =
        (loadingDefaults && !defaults) ||
        (loadingModels && modelList.length === 0);
    
    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            // Force refresh by passing refetch option
            await refetchModels({ throwOnError: true });
        } finally {
            // Give a little time for the animation
            setTimeout(() => setIsRefreshing(false), 500);
        }
    };

    if (shouldShowSkeleton) {
        return (
            <div className="space-y-6">
                {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className="animate-pulse flex flex-col space-y-2">
                        <div className="h-5 bg-muted/50 rounded w-1/4"></div>
                        <div className="h-4 bg-muted/50 rounded w-2/4 mb-2"></div>
                        <div className="h-10 bg-muted/50 rounded w-full"></div>
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex justify-end -mb-4">
                <button
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                    <RefreshCw className={cn("w-3 h-3", isRefreshing && "animate-spin")} />
                    {isRefreshing ? 'Refreshing models...' : 'Refresh model list'}
                </button>
            </div>
            {USE_CASES.map(useCase => (
                useCase.id === 'chat'
                    ? <ChatModelsSection key={useCase.id} />
                    : (
                        <UseCaseSection
                            key={useCase.id}
                            useCase={useCase}
                            currentValue={defaults?.[useCase.id]?.model || ''}
                            groupedModels={groupModelsByProvider(modelList, USE_CASE_MODEL_TYPES[useCase.id])}
                            allModels={modelList}
                            isRefreshing={isFetchingDefaults || isFetchingModels}
                        />
                    )
            ))}
        </div>
    );
}

function UseCaseSection({ 
    useCase,
    currentValue,
    groupedModels,
    allModels,
    isRefreshing,
}: {
    useCase: typeof USE_CASES[0];
    currentValue: string;
    groupedModels: ModelGroup[];
    allModels: ModelInfo[];
    isRefreshing: boolean;
}) {
    const mutation = useUpdateDefault(useCase.id);
    const [selected, setSelected] = useState(currentValue);

    const hasSelectedModel = selected
        ? allModels.some(model => model.name === selected)
        : false;

    // Sync local state when server default changes and the target model is present.
    useEffect(() => {
        const hasServerModel = currentValue
            ? allModels.some(model => model.name === currentValue)
            : false;
        if (currentValue && hasServerModel) {
            setSelected(currentValue);
            return;
        }
        if (!selected && currentValue && !hasServerModel && allModels.length > 0) {
            setSelected(allModels[0].name);
        }
    }, [allModels, currentValue, selected]);

    const handleChange = (modelName: string) => {
        setSelected(modelName);
        
        // Find provider for the selected model
        const modelInfo = allModels.find(m => m.name === modelName);
        const provider = modelInfo?.provider || 'vertex_ai'; // Fallback
        
        mutation.mutate({
            provider,
            model: modelName
        });
    };

    return (
        <div className="flex flex-col space-y-2">
            <div>
                <h3 className="font-semibold text-sm sm:text-base">{useCase.label}</h3>
                <p className="text-xs sm:text-sm text-muted-foreground">{useCase.description}</p>
            </div>
            
            <div className="relative">
                <HierarchicalModelPicker
                    groups={groupedModels}
                    value={hasSelectedModel ? selected : ''}
                    onChange={handleChange}
                    placeholder={`Select ${useCase.label.toLowerCase()}...`}
                    className="mt-2"
                />
                
                {/* Feedback */}
                <div className="mt-2 h-5">
                    {mutation.isPending && (
                        <span className="text-xs text-muted-foreground animate-pulse">Updating...</span>
                    )}
                    {mutation.isSuccess && (
                        <span className="text-xs text-green-500 flex items-center gap-1">
                            <Check className="w-3 h-3" /> Updated successfully
                        </span>
                    )}
                    {mutation.isError && (
                        <span className="text-xs text-destructive flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> Failed to update
                        </span>
                    )}
                    {!mutation.isPending && !mutation.isSuccess && !mutation.isError && isRefreshing && (
                        <span className="text-xs text-muted-foreground">Refreshing model availability...</span>
                    )}
                </div>

                {/* OpenRouter Embeddings Warning */}
                {useCase.id === 'embeddings' && (() => {
                    const modelInfo = allModels.find(m => m.name === selected);
                    const isOpenRouter = modelInfo?.provider === 'openrouter';
                    if (!isOpenRouter || !selected) return null;
                    return (
                        <div className="mt-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                            <p className="text-xs text-amber-600 dark:text-amber-400">
                                <AlertCircle className="w-3 h-3 inline mr-1" />
                                OpenRouter embeddings only support{' '}
                                <code className="px-1 py-0.5 bg-amber-500/20 rounded text-[10px]">openai/text-embedding*</code>{' '}
                                models. Non-compatible models may fail.
                            </p>
                        </div>
                    );
                })()}
            </div>
        </div>
    );
}
