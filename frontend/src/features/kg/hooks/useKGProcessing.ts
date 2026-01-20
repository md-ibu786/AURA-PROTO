import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getKGDocumentStatus,
    processKGBatch,
    getKGProcessingQueue
} from '../../../api/explorerApi';
import type { ProcessingRequest } from '../types/kg.types';
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
        onSuccess: (data, variables) => {
            queryClient.invalidateQueries({ queryKey: ['kg', 'queue'] });
            // Start polling if needed (though queue query handles it via refetchInterval)
            setKGPolling(variables.module_id, true);
        },
    });

    return {
        useFileKGStatus,
        useProcessingQueue,
        processFiles,
    };
}
