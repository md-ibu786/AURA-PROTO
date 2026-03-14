/**
 * ============================================================================
 * FILE: useSettingsApi.ts
 * LOCATION: frontend/src/features/settings/hooks/useSettingsApi.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TanStack Query hooks for settings API interaction
 *
 * ROLE IN PROJECT:
 *    Provides hooks for fetching available AI models, default model settings,
 *    API key status, and mutations for storing/deleting API keys and updating
 *    defaults. Centralizes settings state management via React Query cache
 *
 * KEY COMPONENTS:
 *    - settingsKeys: Query key factory for cache invalidation
 *    - useAllModels: Fetches all available models from backend
 *    - useProviderModels: Fetches models filtered by provider
 *    - useModelDefaults: Gets default model configuration
 *    - useUpdateDefaults: Mutation for updating default models
 *    - useApiKeyStatus, useStoreApiKey, useDeleteApiKey: API key management
 *
 * DEPENDENCIES:
 *    - External: @tanstack/react-query, sonner
 *    - Internal: @/api/client, @/types/settings
 *
 * USAGE:
 *    const { data: models } = useAllModels();
 *    const updateDefaults = useUpdateDefaults();
 * ============================================================================
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from '@/api/client';
import { toast } from 'sonner';
import type { 
    ModelInfo, 
    DefaultModelSetting, 
    ApiKeyStatus,
    UseCase,
    ProviderType
} from '@/types/settings';

export const settingsKeys = {
    all: ['settings'] as const,
    models: () => [...settingsKeys.all, 'models'] as const,
    providerModels: (provider: string) => [...settingsKeys.models(), provider] as const,
    defaults: () => [...settingsKeys.all, 'defaults'] as const,
    apiKey: (provider: string) => [...settingsKeys.all, 'apiKey', provider] as const,
};

export const useAllModels = () => {
    return useQuery({
        queryKey: settingsKeys.models(),
        queryFn: async () => {
            return await fetchApi<ModelInfo[]>('/v1/settings/models');
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
};

export const useDefaults = () => {
    return useQuery({
        queryKey: settingsKeys.defaults(),
        queryFn: async () => {
            return await fetchApi<Record<string, DefaultModelSetting>>('/v1/settings/defaults');
        },
        staleTime: 2 * 60 * 1000, // 2 minutes
    });
};

export const useProviderModels = (provider: ProviderType | string) => {
    return useQuery({
        queryKey: settingsKeys.providerModels(provider),
        queryFn: async () => {
            return await fetchApi<ModelInfo[]>(`/v1/settings/providers/${provider}/models`);
        },
        enabled: !!provider,
    });
};

export const useApiKeyStatus = (provider: ProviderType | string) => {
    return useQuery({
        queryKey: settingsKeys.apiKey(provider),
        queryFn: async () => {
            return await fetchApi<ApiKeyStatus>(`/v1/settings/providers/${provider}/api-key`);
        },
        enabled: !!provider,
    });
};

export const useStoreApiKey = (provider: ProviderType | string) => {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: async (api_key: string) => {
            return await fetchApi<ApiKeyStatus>(
                `/v1/settings/providers/${provider}/api-key`,
                { 
                    method: 'POST',
                    body: JSON.stringify({ api_key })
                }
            );
        },
        onSuccess: () => {
            toast.success('API key stored');
            queryClient.invalidateQueries({ queryKey: settingsKeys.models() });
            queryClient.invalidateQueries({ queryKey: settingsKeys.providerModels(provider) });
            queryClient.invalidateQueries({ queryKey: settingsKeys.apiKey(provider) });
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to store API key');
        }
    });
};

export const useDeleteApiKey = (provider: ProviderType | string) => {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: async () => {
            return await fetchApi<{ status: string }>(
                `/v1/settings/providers/${provider}/api-key`,
                { method: 'DELETE' }
            );
        },
        onSuccess: () => {
            toast.success('API key deleted');
            queryClient.invalidateQueries({ queryKey: settingsKeys.apiKey(provider) });
            queryClient.invalidateQueries({ queryKey: settingsKeys.models() });
            queryClient.invalidateQueries({ queryKey: settingsKeys.providerModels(provider) });
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to delete API key');
        }
    });
};

export const useValidateApiKey = (provider: ProviderType | string) => {
    return useMutation({
        mutationFn: async () => {
            return await fetchApi<{ provider: string; valid: boolean; error?: string }>(
                `/v1/settings/providers/${provider}/validate`,
                { method: 'POST' }
            );
        },
        onSuccess: (data) => {
            if (data.valid) {
                toast.success('API key is valid');
            } else {
                toast.error(data.error || 'API key is invalid');
            }
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Validation failed');
        }
    });
};

export const useUpdateDefault = (useCase: UseCase | string) => {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: async (setting: DefaultModelSetting) => {
            return await fetchApi<{ use_case: string; provider: string; model: string }>(
                `/v1/settings/defaults/${useCase}`,
                {
                    method: 'PUT',
                    body: JSON.stringify(setting)
                }
            );
        },
        onSuccess: () => {
            toast.success('Default model updated');
            queryClient.invalidateQueries({ queryKey: settingsKeys.defaults() });
        },
        onError: (error: Error) => {
            toast.error(error.message || 'Failed to update default model');
        }
    });
};
