export interface Task {
    task_id: string;
    prompt: string;
    expected_outcome: string;
    min_steps: number;
    max_steps: number;
    category: string;
}
