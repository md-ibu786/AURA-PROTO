/**
 * ============================================================================
 * FILE: useKGProcessing.ts
 * LOCATION: frontend/src/features/kg/hooks/useKGProcessing.ts
 * ============================================================================
 *
 * PURPOSE:
 *    React Query hooks for Knowledge Graph processing operations. Provides
 *    typed queries and mutations for document status, batch processing,
 *    and queue monitoring.
 *
 * ROLE IN PROJECT:
 *    Central hook module for all KG-related data fetching and mutations.
 *    Encapsulates React Query logic including:
 *    - Single document status queries
 *    - Processing queue monitoring
 *    - Batch processing mutations
 *
 * KEY HOOKS:
 *    - useFileKGStatus(documentId): Query single document status
 *    - useProcessingQueue(): Query queue with smart polling
 *    - processFiles: Mutation for batch processing
 *
 * POLLING STRATEGY:
 *    - useProcessingQueue polls every 2s when items are 'processing'
 *    - Polling stops when queue is empty or all items complete
 *
 * DEPENDENCIES:
 *    - External: @tanstack/react-query
 *    - Internal: api/explorerApi, stores/useExplorerStore, types/kg.types
 *
 * @see: api/explorerApi.ts - API functions used by hooks
 * @see: stores/useExplorerStore.ts - kgPolling state
 * @note: Smart polling only active during processing
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getKGDocumentStatus,
    processKGBatch,
    getKGProcessingQueue,
    deleteKGBatch
} from '../../../api/explorerApi';
import type { ProcessingRequest, DeleteBatchRequest } from '../types/kg.types';
import { useExplorerStore } from '../../../stores';

export function useKGProcessing() {
    const queryClient = useQueryClient();
    const { setKGPolling } = useExplorerStore();

    // Fetch status for a single document
    const useFileKGStatus = (documentId: string) => {
        return useQuery({
            queryKey: ['kg', 'status', documentId],
            queryFn: () => getKGDocumentStatus(documentId),
            enabled: !!documentId,
        });
    };

    // Fetch processing queue (polling enabled only when items in queue)
    const useProcessingQueue = () => {
        return useQuery({
            queryKey: ['kg', 'queue'],
            queryFn: getKGProcessingQueue,
            refetchInterval: (query) => {
                // Only poll if queue has items (active processing)
                const queue = query.state.data as Array<{ status: string }> | undefined;
                const hasActiveItems = queue?.some(item => item.status === 'processing');
                return hasActiveItems ? 2000 : false;
            },
        });
    };

    // Batch processing mutation
    const processFiles = useMutation({
        mutationFn: (request: ProcessingRequest) => processKGBatch(request),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ['kg', 'queue'] });
            // Start polling if needed (though queue query handles it via refetchInterval)
            setKGPolling(variables.module_id, true);
        },
    });

    // Batch delete mutation
    const deleteFiles = useMutation({
        mutationFn: (request: DeleteBatchRequest) => deleteKGBatch(request),
        onSuccess: () => {
            // Invalidate explorer tree to refresh KG status indicators
            queryClient.invalidateQueries({ queryKey: ['explorer', 'tree'] });
            queryClient.invalidateQueries({ queryKey: ['kg', 'queue'] });
        },
    });

    return {
        useFileKGStatus,
        useProcessingQueue,
        processFiles,
        deleteFiles,
    };
}
