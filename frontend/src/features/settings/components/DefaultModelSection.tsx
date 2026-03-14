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
import { useGroupedModels } from '../hooks/useModelList';
import { HierarchicalModelPicker } from './HierarchicalModelPicker';
import { UseCase, ModelGroup, ModelInfo } from '@/types/settings';
import { Check, AlertCircle } from 'lucide-react';

const USE_CASES: { id: UseCase; label: string; description: string }[] = [
    { id: 'chat', label: 'Chat Model', description: 'Used for conversational responses and RAG' },
    { id: 'embeddings', label: 'Embeddings Model', description: 'Used for document indexing and vector search' },
    { id: 'entity_extraction', label: 'Entity Extraction Model', description: 'Used for building knowledge graphs from documents' }
];

export function DefaultModelSection() {
    const { data: defaults, isLoading: loadingDefaults } = useDefaults();
    const { data: allModels, isLoading: loadingModels } = useAllModels();
    const groupedModels = useGroupedModels(allModels);
    
    if (loadingDefaults || loadingModels) {
        return (
            <div className="space-y-6">
                {[1, 2, 3].map(i => (
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
            {USE_CASES.map(useCase => (
                <UseCaseSection
                    key={useCase.id}
                    useCase={useCase}
                    currentValue={defaults?.[useCase.id]?.model || ''}
                    groupedModels={groupedModels}
                    allModels={allModels || []}
                />
            ))}
        </div>
    );
}

function UseCaseSection({ 
    useCase, 
    currentValue, 
    groupedModels, 
    allModels 
}: { 
    useCase: typeof USE_CASES[0];
    currentValue: string;
    groupedModels: ModelGroup[];
    allModels: ModelInfo[];
}) {
    const mutation = useUpdateDefault(useCase.id);
    const [selected, setSelected] = useState(currentValue);

    // Sync local state when server default changes (e.g. via another tab)
    useEffect(() => {
        setSelected(currentValue);
    }, [currentValue]);

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
                    value={selected}
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
                </div>
            </div>
        </div>
    );
}
