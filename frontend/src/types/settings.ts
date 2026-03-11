// settings.ts
// TypeScript types for settings API and model selection

// Defines ProviderType, UseCase, and various interfaces for model 
// configuration, grouping, and API key status.

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
