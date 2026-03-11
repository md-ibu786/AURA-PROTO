// HierarchicalModelPicker.tsx
// Renders a hierarchical list of models grouped by provider and vendor

// Provides search functionality, expand/collapse sections, and model selection.
// Supports 3-level hierarchy (Provider -> Vendor -> Model) for OpenRouter
// and 2-level hierarchy (Provider -> Model) for others.

import React, { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronRight, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/cn';
import { ModelGroup, ModelInfo } from '@/types/settings';

export interface HierarchicalModelPickerProps {
    groups: ModelGroup[];
    value: string;
    onChange: (model: string) => void;
    isLoading?: boolean;
    placeholder?: string;
    className?: string;
}

export function HierarchicalModelPicker({
    groups,
    value,
    onChange,
    isLoading = false,
    placeholder = 'Search models...',
    className
}: HierarchicalModelPickerProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedProviders, setExpandedProviders] = useState<Record<string, boolean>>({});
    const [expandedVendors, setExpandedVendors] = useState<Record<string, boolean>>({});

    const toggleProvider = (provider: string) => {
        setExpandedProviders(prev => ({ ...prev, [provider]: !prev[provider] }));
    };

    const toggleVendor = (vendorId: string) => {
        setExpandedVendors(prev => ({ ...prev, [vendorId]: !prev[vendorId] }));
    };

    const filteredGroups = useMemo(() => {
        if (!searchQuery.trim()) return groups;

        const query = searchQuery.toLowerCase();
        
        return groups.map(group => {
            const filteredVendors = group.vendors.map(vendor => {
                const filteredModels = vendor.models.filter(model => {
                    const displayName = model.display_name || '';
                    return displayName.toLowerCase().includes(query) || 
                           model.name.toLowerCase().includes(query);
                });
                return { ...vendor, models: filteredModels };
            }).filter(vendor => vendor.models.length > 0);

            return { ...group, vendors: filteredVendors };
        }).filter(group => group.vendors.length > 0);
    }, [groups, searchQuery]);

    // When searching, auto-expand everything that matches
    const isSearching = searchQuery.trim().length > 0;

    const isProviderExpanded = (provider: string) => {
        if (isSearching) return true;
        if (expandedProviders[provider] !== undefined) return expandedProviders[provider];
        return true; // Default expanded
    };

    const isVendorExpanded = (vendorId: string) => {
        if (isSearching) return true;
        if (expandedVendors[vendorId] !== undefined) return expandedVendors[vendorId];
        return true; // Default expanded
    };

    if (isLoading) {
        return (
            <div data-testid="model-picker-skeleton" className={cn("flex flex-col gap-2 p-2 border border-border rounded-lg bg-card/50", className)}>
                <div className="h-9 bg-muted/50 rounded animate-pulse mb-2"></div>
                <div className="h-6 w-24 bg-muted/50 rounded animate-pulse ml-2 mb-1"></div>
                <div className="h-8 bg-muted/50 rounded animate-pulse ml-4 mb-1"></div>
                <div className="h-8 bg-muted/50 rounded animate-pulse ml-4 mb-2"></div>
                <div className="h-6 w-24 bg-muted/50 rounded animate-pulse ml-2 mb-1"></div>
                <div className="h-8 bg-muted/50 rounded animate-pulse ml-4 mb-1"></div>
            </div>
        );
    }

    return (
        <div className={cn("flex flex-col border border-border rounded-lg bg-card/30 overflow-hidden", className)}>
            {/* Search Input */}
            <div className="p-2 border-b border-border/50 bg-card/50">
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder={placeholder}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-primary/50 rounded-md"
                    />
                </div>
            </div>

            {/* List */}
            <div className="max-h-[360px] overflow-y-auto p-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
                {groups.length === 0 ? (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                        No models available
                    </div>
                ) : filteredGroups.length === 0 ? (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                        No models found
                    </div>
                ) : (
                    <div className="flex flex-col space-y-1">
                        {filteredGroups.map(group => (
                            <div key={group.provider} className="flex flex-col">
                                {/* Provider Header */}
                                <button
                                    onClick={() => toggleProvider(group.provider)}
                                    className="flex items-center w-full px-2 py-1.5 text-left hover:bg-muted/30 rounded transition-colors group/header"
                                >
                                    {isProviderExpanded(group.provider) ? (
                                        <ChevronDown className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                                    ) : (
                                        <ChevronRight className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                                    )}
                                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                        {group.providerLabel}
                                    </span>
                                </button>

                                {/* Provider Content */}
                                <AnimatePresence initial={false}>
                                    {isProviderExpanded(group.provider) && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            transition={{ duration: 0.2 }}
                                            className="overflow-hidden"
                                        >
                                            {group.provider === 'openrouter' ? (
                                                /* 3-Level Hierarchy for OpenRouter */
                                                group.vendors.map(vendor => {
                                                    const vendorId = `${group.provider}-${vendor.vendor}`;
                                                    return (
                                                        <div key={vendorId} className="flex flex-col mt-0.5">
                                                            <button
                                                                onClick={() => toggleVendor(vendorId)}
                                                                className="flex items-center w-full pl-6 pr-2 py-1 text-left hover:bg-muted/30 rounded transition-colors"
                                                            >
                                                                {isVendorExpanded(vendorId) ? (
                                                                    <ChevronDown className="h-3 w-3 mr-1.5 text-muted-foreground/80" />
                                                                ) : (
                                                                    <ChevronRight className="h-3 w-3 mr-1.5 text-muted-foreground/80" />
                                                                )}
                                                                <span className="text-xs font-semibold text-muted-foreground/80">
                                                                    {vendor.vendorLabel}
                                                                </span>
                                                            </button>

                                                            <AnimatePresence initial={false}>
                                                                {isVendorExpanded(vendorId) && (
                                                                    <motion.div
                                                                        initial={{ height: 0, opacity: 0 }}
                                                                        animate={{ height: 'auto', opacity: 1 }}
                                                                        exit={{ height: 0, opacity: 0 }}
                                                                        transition={{ duration: 0.2 }}
                                                                        className="overflow-hidden flex flex-col space-y-0.5 mt-0.5"
                                                                    >
                                                                        {vendor.models.map(model => (
                                                                            <ModelItem
                                                                                key={model.name}
                                                                                model={model}
                                                                                isSelected={value === model.name}
                                                                                onClick={() => onChange(model.name)}
                                                                                indentClass="pl-12"
                                                                            />
                                                                        ))}
                                                                    </motion.div>
                                                                )}
                                                            </AnimatePresence>
                                                        </div>
                                                    );
                                                })
                                            ) : (
                                                /* 2-Level Hierarchy for Vertex/Ollama */
                                                <div className="flex flex-col space-y-0.5 mt-0.5">
                                                    {group.vendors.flatMap(v => v.models).map(model => (
                                                        <ModelItem
                                                            key={model.name}
                                                            model={model}
                                                            isSelected={value === model.name}
                                                            onClick={() => onChange(model.name)}
                                                            indentClass="pl-6"
                                                        />
                                                    ))}
                                                </div>
                                            )}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function ModelItem({ 
    model, 
    isSelected, 
    onClick, 
    indentClass 
}: { 
    model: ModelInfo; 
    isSelected: boolean; 
    onClick: () => void;
    indentClass: string;
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "flex items-center w-full pr-3 py-1.5 text-left text-sm rounded transition-colors relative group",
                indentClass,
                isSelected 
                    ? "bg-primary/20 text-primary font-medium" 
                    : "text-foreground hover:bg-primary/10"
            )}
            title={model.name}
        >
            {isSelected && (
                <div className="absolute left-[calc(var(--indent)-8px)] h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" 
                     style={{ '--indent': indentClass === 'pl-12' ? '48px' : '24px' } as React.CSSProperties} />
            )}
            <span className="truncate flex-1">
                {model.display_name || model.name}
            </span>
            {isSelected && <Check className="h-3.5 w-3.5 flex-shrink-0 ml-2" />}
        </button>
    );
}
