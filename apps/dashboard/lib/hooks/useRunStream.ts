import { useState, useEffect } from "react";
import { streamRunProgress } from "../api/runs";
import { ProgressEvent } from "../types/run";

export function useRunStream(runId: string | null) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [completed, setCompleted] = useState(0);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!runId) return;
    setIsStreaming(true);
    const es = streamRunProgress(runId, (event) => {
      setEvents(prev => [...prev, event]);
      if (event.type === "progress") { 
          setCompleted(event.completed); 
          setTotal(event.total); 
      }
      if (event.type === "suite_complete") setIsStreaming(false);
    });
    return () => { 
        es.close(); 
        setIsStreaming(false); 
    };
  }, [runId]);

  return { events, isStreaming, completed, total, progress: total ? completed/total : 0 };
}
