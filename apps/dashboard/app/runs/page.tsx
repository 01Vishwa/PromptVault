'use client'

import { useRuns } from '@/lib/hooks/useRuns';
import Link from 'next/link';

export default function RunsList() {
  const { data: runs, isLoading } = useRuns(50);

  if (isLoading) return <div className="p-8 shrink-0 flex w-full">Loading runs...</div>;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden w-full h-[600px] overflow-y-auto">
      <div className="px-6 py-4 border-b border-slate-200 sticky top-0 bg-white shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">Recent Evaluation Runs</h2>
      </div>
      {(!runs || runs.length === 0) ? (
        <div className="p-12 text-center text-slate-500">No runs yet. Trigger a suite to see data.</div>
      ) : (
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-sm">
              <th className="px-6 py-3 font-medium">Run ID</th>
              <th className="px-6 py-3 font-medium">Task ID</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Score</th>
              <th className="px-6 py-3 font-medium">Duration</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                <td className="px-6 py-4 text-sm font-medium text-indigo-600">
                  <Link href={`/runs/${r.run_id}`}>{r.run_id}</Link>
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{r.task_id}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                    r.status === 'PASS' ? 'bg-emerald-100 text-emerald-700' : 
                    r.status === 'FAIL' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm font-medium">{r.score !== null ? (r.score * 100).toFixed(0) + '%' : '-'}</td>
                <td className="px-6 py-4 text-sm text-slate-500">{r.duration_ms}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
