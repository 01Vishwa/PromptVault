'use client'

import { useRunDetail, useRunTrace } from '@/lib/hooks/useRuns';
import TraceGraph from '@/components/trace/TraceGraph';

export default function RunDetail({ params }: { params: { runId: string } }) {
  const { data: run, isLoading: isRunLoading } = useRunDetail(params.runId);
  const { data: trace, isLoading: isTraceLoading } = useRunTrace(params.runId);

  if (isRunLoading) return <div>Loading Run...</div>;
  if (!run) return <div>Run not found</div>;

  return (
      <div className="flex flex-col h-full space-y-4">
        {/* Header Breadcrumb */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold">{params.runId}</h2>
              <p className="text-sm text-slate-500">Task: {run.task_id} | Status: <span className="font-semibold">{run.status}</span></p>
            </div>
            {run.judge_scores && (
               <div className="flex space-x-4 text-center">
                 <div><p className="text-xs text-slate-400">Score</p><p className="font-bold">{(run.judge_scores.score.value * 100).toFixed(0)}%</p></div>
                 <div><p className="text-xs text-slate-400">Tool Acc</p><p className="font-bold">{run.judge_scores.tool_accuracy}%</p></div>
               </div>
            )}
        </div>

        {/* Trace Explorer full height minus header */}
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden h-[600px] relative">
            {isTraceLoading ? (
                <div className="p-8">Loading Trace Graph...</div>
            ) : trace ? (
                <TraceGraph nodes={trace.nodes} edges={trace.edges} />
            ) : (
                <div className="p-12 text-center text-slate-500">No trace data available for this run.</div>
            )}
        </div>
      </div>
  );
}
