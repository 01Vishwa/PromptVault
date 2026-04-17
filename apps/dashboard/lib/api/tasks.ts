import { apiClient } from "./client";
import { Task } from "../types/task";

export const listTasks = () => 
    apiClient.get<Task[]>("/api/tasks");

export const getTaskHistory = (taskId: string) => 
    apiClient.get<any[]>(`/api/tasks/${taskId}/history`);
