/**
 * ============================================================================
 * FILE: settings.ts
 * LOCATION: frontend/src/types/settings.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TypeScript types for settings API and AI model selection
 *
 * ROLE IN PROJECT:
 *    Defines ProviderType, UseCase, and interfaces for model configuration,
 *    grouping, and API key status. Provides type safety for settings forms
 *    and AI model selection across the application
 *
 * KEY COMPONENTS:
 *    - ProviderType: Union of supported AI providers
 *    - UseCase: Union of AI operation types
 *    - ModelInfo: Individual model metadata
 *    - VendorGroup/ModelGroup: Hierarchical model structures
 *    - DefaultModelSetting: User default model configuration
 *    - ApiKeyStatus: API key storage status per provider
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: None
 *
 * USAGE:
 *    import type { ProviderType, ModelInfo, DefaultModelSetting } from '@/types/settings';
 * ============================================================================
 */
export type ProviderType = 'vertex_ai' | 'openrouter' | 'ollama';
export type UseCase = 'chat' | 'embeddings' | 'entity_extraction';

export interface ModelInfo {
    name: string;
    provider: ProviderType;
    display_name: string | null;
}

export interface VendorGroup {
    vendor: string;
    vendorLabel: string;
    models: ModelInfo[];
}

export interface ModelGroup {
    provider: ProviderType;
    providerLabel: string;
    vendors: VendorGroup[];
}

export interface DefaultModelSetting {
    provider: string;
    model: string;
}

export interface ApiKeyStatus {
    provider: string;
    masked_key: string;
    valid: boolean | null;
}
