import { apiClient } from "./client";
import { SuiteMetrics } from "../types/metrics";

export const getMetricsSummary = () => 
    apiClient.get<SuiteMetrics>("/api/metrics/summary");

export const getMetricsHistory = (days = 7) => 
    apiClient.get<SuiteMetrics[]>("/api/metrics/history", { days });

export const getAlerts = () => 
    apiClient.get<any[]>("/api/metrics/alerts");
