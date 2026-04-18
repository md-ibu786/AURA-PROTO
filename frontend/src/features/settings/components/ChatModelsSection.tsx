/**
 * ============================================================================
 * FILE: ChatModelsSection.tsx
 * LOCATION: frontend/src/features/settings/components/ChatModelsSection.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Component for configuring 1-5 chat models with default selection in admin settings
 *
 * ROLE IN PROJECT:
 *    Part of the settings configuration system:
 *    - Displays list of selected chat models (max 5)
 *    - Allows adding models via HierarchicalModelPicker
 *    - Allows removing models and setting default model
 *    - Saves configuration via API mutation
 *    - Replaces standard UseCaseSection for the chat use case
 *
 * KEY COMPONENTS:
 *    - ChatModelsSection: Main component with model list management
 *    - State: selectedModels array, defaultIndex number
 *    - Handlers: add, remove, set default, save
 *
 * DEPENDENCIES:
 *    - External: react, framer-motion, lucide-react, sonner
 *    - Internal: features/settings/hooks/useSettingsApi,
 *                features/settings/hooks/useModelList,
 *                features/settings/components/HierarchicalModelPicker,
 *                types/settings
 *
 * USAGE:
 *    <ChatModelsSection />
 *    Used within DefaultModelSection for the chat use case
 * ============================================================================
 */

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GripVertical, Star, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useChatModelsConfig, useUpdateChatModels, useAllModels } from '../hooks/useSettingsApi';
import { groupModelsByProvider } from '../hooks/useModelList';
import { HierarchicalModelPicker } from './HierarchicalModelPicker';
import type { ChatModelEntry } from '@/types/settings';

export function ChatModelsSection() {
    const [selectedModels, setSelectedModels] = useState<ChatModelEntry[]>([]);
    const [defaultIndex, setDefaultIndex] = useState(0);

    const { data: config, isLoading: loadingConfig } = useChatModelsConfig();
    const { data: allModels, isLoading: loadingModels } = useAllModels();
    const updateChatModels = useUpdateChatModels();

    const groupedModels = useMemo(
        () => groupModelsByProvider(allModels || [], 'generation'),
        [allModels]
    );

    useEffect(() => {
        if (config && config.models.length > 0) {
            setSelectedModels(config.models);
            setDefaultIndex(config.default_index);
        }
    }, [config]);

    const handleAddModel = (model: string) => {
        if (selectedModels.length >= 5) {
            toast.error('Maximum 5 models allowed');
            return;
        }

        const modelInfo = allModels?.find(m => m.name === model);
        if (!modelInfo) return;

        const exists = selectedModels.some(
            m => m.provider === modelInfo.provider && m.model === modelInfo.name
        );
        if (exists) return;

        setSelectedModels(prev => [
            ...prev,
            { provider: modelInfo.provider, model: modelInfo.name },
        ]);
    };

    const handleRemoveModel = (index: number) => {
        setSelectedModels(prev => {
            const newModels = prev.filter((_, i) => i !== index);
            if (defaultIndex >= newModels.length) {
                setDefaultIndex(Math.max(0, newModels.length - 1));
            }
            return newModels;
        });
    };

    const handleSetDefault = (index: number) => {
        setDefaultIndex(index);
    };

    const handleSave = () => {
        if (selectedModels.length === 0) return;
        updateChatModels.mutate({
            models: selectedModels,
            default_index: defaultIndex,
        });
    };

    const isAtMax = selectedModels.length >= 5;

    const hasChanges = useMemo(() => {
        if (!config) return false;
        if (selectedModels.length !== config.models.length) return true;
        if (defaultIndex !== config.default_index) return true;
        return selectedModels.some(
            (entry, i) =>
                entry.provider !== config.models[i].provider ||
                entry.model !== config.models[i].model
        );
    }, [selectedModels, defaultIndex, config]);

    if (loadingConfig || loadingModels) {
        return (
            <div className="animate-pulse flex flex-col space-y-2">
                <div className="h-5 bg-muted/50 rounded w-1/4"></div>
                <div className="h-4 bg-muted/50 rounded w-2/4 mb-2"></div>
                <div className="h-10 bg-muted/50 rounded w-full"></div>
            </div>
        );
    }

    return (
        <div className="flex flex-col space-y-4">
            <div>
                <h3 className="font-semibold text-sm sm:text-base">Chat Models</h3>
                <p className="text-xs sm:text-sm text-muted-foreground">
                    Configure up to 5 models available to users in the chat interface
                </p>
            </div>

            <div className="flex flex-col space-y-2">
                <AnimatePresence mode="popLayout">
                    {selectedModels.map((entry, index) => {
                        const isDefault = defaultIndex === index;
                        const displayName =
                            allModels?.find(m => m.name === entry.model)?.display_name ||
                            entry.model;

                        return (
                            <motion.div
                                key={`${entry.provider}-${entry.model}`}
                                layout
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="flex items-center justify-between p-3 bg-card/50 rounded-md border border-border/10"
                            >
                                <div className="flex items-center gap-2">
                                    <GripVertical className="w-4 h-4 text-muted-foreground/40 hidden sm:block" />
                                    <div className="flex flex-col">
                                        <span className="font-semibold text-sm">{displayName}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {entry.provider}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    {isDefault ? (
                                        <div className="flex items-center gap-1 text-primary">
                                            <Star className="w-4 h-4 fill-primary/30" />
                                            <span className="text-xs hidden sm:inline">Default</span>
                                        </div>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={() => handleSetDefault(index)}
                                            className="flex items-center gap-1 text-muted-foreground hover:text-primary transition-colors"
                                            aria-label={`Set ${displayName} as default`}
                                        >
                                            <Star className="w-4 h-4" />
                                            <span className="text-xs hidden sm:inline">Set as Default</span>
                                        </button>
                                    )}

                                    <button
                                        type="button"
                                        onClick={() => handleRemoveModel(index)}
                                        disabled={selectedModels.length === 1}
                                        className="p-1 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                        aria-label={`Remove model ${displayName}`}
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>

            <div className={isAtMax ? 'opacity-50 pointer-events-none' : ''}>
                <HierarchicalModelPicker
                    groups={groupedModels}
                    value=""
                    onChange={handleAddModel}
                    placeholder="Add a chat model..."
                />
            </div>

            <button
                type="button"
                onClick={handleSave}
                disabled={selectedModels.length === 0 || updateChatModels.isPending || !hasChanges}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
                {updateChatModels.isPending && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                )}
                {updateChatModels.isPending ? 'Saving...' : 'Save'}
            </button>
        </div>
    );
}
