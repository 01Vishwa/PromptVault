'use client'

import { useMetrics } from '@/lib/hooks/useMetrics';
import MetricCard from '@/components/cards/MetricCard';
import SuccessRateChart from '@/components/charts/SuccessRateChart';
import LatencyChart from '@/components/charts/LatencyChart';

export default function SystemHealth() {
  const { summary, history } = useMetrics();

  if (summary.isLoading) return <div className="p-8">Loading System Health...</div>;
  if (summary.isError) return <div className="p-8 text-red-500">Error loading metrics. Is the backend running?</div>;

  const data = summary.data;
  const historyData = history.data || [];

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">System Health</h1>
        {data?.regression_detected && (
           <div className="bg-red-100 text-red-700 px-4 py-2 rounded-lg text-sm font-medium border border-red-200">
             🚨 Regression Detected: -{data.regression_delta}%
           </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <MetricCard label="Success Rate" value={data?.task_success_rate ? (data.task_success_rate * 100).toFixed(1) : 0} unit="%" alertLevel={data?.regression_detected ? "critical" : "ok"} />
        <MetricCard label="Avg Corectness" value={data?.avg_correctness ? (data.avg_correctness * 100).toFixed(1) : 0} unit="%" />
        <MetricCard label="P99 Latency" value={data?.latency_p99_ms || 0} unit="ms" alertLevel={(data?.latency_p99_ms || 0) > 4000 ? "warn" : "ok"} />
        <MetricCard label="Tool Error Rate" value={data?.tool_error_rate ? (data.tool_error_rate * 100).toFixed(1) : 0} unit="%" alertLevel={(data?.tool_error_rate || 0) > 0.1 ? "warn" : "ok"} />
        <MetricCard label="Avg Est. Cost" value={`$${data?.estimated_cost_usd?.toFixed(3) || "0.00"}`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-700 mb-6">Success Rate History</h3>
          <SuccessRateChart data={historyData.map(h => ({...h, task_success_rate: h.task_success_rate * 100}))} />
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-700 mb-6">Latency Trends</h3>
          <LatencyChart data={historyData} />
        </div>
      </div>
    </div>
  );
}
