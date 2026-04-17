import { useQuery } from '@tanstack/react-query';
import { getRuns, getRun, getRunTrace } from '../api/runs';

export function useRuns(limit: number = 20, offset: number = 0, status?: string) {
    return useQuery({ 
        queryKey: ['runs', limit, offset, status], 
        queryFn: () => getRuns(limit, offset, status) 
    });
}

export function useRunDetail(runId: string | null) {
    return useQuery({
        queryKey: ['run', runId],
        queryFn: () => getRun(runId!),
        enabled: !!runId
    });
}

export function useRunTrace(runId: string | null) {
    return useQuery({
        queryKey: ['trace', runId],
        queryFn: () => getRunTrace(runId!),
        enabled: !!runId
    });
}
