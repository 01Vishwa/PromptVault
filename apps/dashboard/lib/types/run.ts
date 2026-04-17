export interface SpanResponse {
    span_type: string;
    span_id: string;
    duration_ms: number;
    attributes: Record<string, any>;
    error: boolean;
}

export interface TrajectoryResponse {
    spans: SpanResponse[];
    step_count: number;
    token_total: number;
    duration_ms: number;
    tool_names_called: string[];
    error_count: number;
}

export interface RunSummaryResponse {
    run_id: string;
    task_id: string;
    agent_version: string;
    status: string;
    created_at: string;
    score: number | null;
    duration_ms: number;
}

export interface RunDetailResponse {
    run_id: string;
    task_id: string;
    status: string;
    trajectory: TrajectoryResponse | null;
    judge_scores: Record<string, any> | null;
}

export interface CreateRunRequest {
    task_ids: string[] | "all";
    category?: string;
    agent_version?: string;
}

export interface ProgressEvent {
    type: string;
    completed: number;
    total: number;
    data: any;
}
