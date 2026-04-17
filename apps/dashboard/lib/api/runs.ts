import { apiClient } from "./client";
import { CreateRunRequest, RunSummaryResponse, RunDetailResponse, ProgressEvent } from "../types/run";
import { ReactFlowResponse } from "../types/trace";

export const getRuns = (limit = 20, offset = 0, status?: string) => 
    apiClient.get<RunSummaryResponse[]>("/api/runs", { limit, offset, status });

export const getRun = (runId: string) => 
    apiClient.get<RunDetailResponse>(`/api/runs/${runId}`);

export const getRunTrace = (runId: string) => 
    apiClient.get<ReactFlowResponse>(`/api/runs/${runId}/trace`);

export const createRun = (request: CreateRunRequest) => 
    apiClient.post<{job_id: string}>("/api/runs", request);

export const streamRunProgress = (runId: string, onEvent: (e: ProgressEvent) => void): EventSource => {
    const baseUrl = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:3000";
    const es = new EventSource(`${baseUrl}/api/runs/${runId}/stream`);
    es.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onEvent({
                type: data.event ?? "progress",
                completed: data.data?.completed ?? 0,
                total: data.data?.total ?? 0,
                data: data.data
            });
        } catch (e) {
            onEvent({ type: "error", completed: 0, total: 0, data: event.data });
        }
    };
    return es;
};
