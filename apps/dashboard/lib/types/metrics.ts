export interface SuiteMetrics {
    run_id: string;
    run_timestamp: string;
    task_success_rate: number;
    latency_p50_ms: number;
    latency_p99_ms: number;
    avg_tokens_per_task: number;
    estimated_cost_usd: number;
    tool_error_rate: number;
    avg_step_efficiency: number;
    error_count: number;
    avg_correctness: number;
    hallucination_rate: number;
    safety_pass_rate: number;
    regression_detected: boolean;
    regression_delta: number | null;
    regressed_tasks: string[];
    improved_tasks: string[];
}
