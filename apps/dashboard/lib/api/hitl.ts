import { apiClient } from "./client";

export const annotateRun = (runId: string, payload: any) => 
    apiClient.post<any>(`/api/hitl/${runId}/annotate`, payload);
