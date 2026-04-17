import { apiClient } from "./client";

export const evaluateTrajectory = (request: any) => 
    apiClient.post<any>("/api/judge/evaluate", request);

export const pairwiseCompare = (request: any) => 
    apiClient.post<any>("/api/judge/pairwise", request);

export const getCacheStats = () => 
    apiClient.get<any>("/api/judge/cache/stats");
