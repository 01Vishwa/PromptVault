import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: number;
  alertLevel?: "ok" | "warn" | "critical" | "none";
}

export default function MetricCard({ label, value, unit, trend, alertLevel = "none" }: MetricCardProps) {
  const bgColors = {
    ok: "bg-white",
    warn: "bg-amber-50 border-amber-200",
    critical: "bg-red-50 border-red-200",
    none: "bg-white",
  };

  return (
    <div className={`p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col ${bgColors[alertLevel]}`}>
      <span className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-2">{label}</span>
      <div className="flex items-baseline">
        <span className="text-3xl font-semibold text-slate-800">{value}</span>
        {unit && <span className="ml-1 text-slate-500 font-medium">{unit}</span>}
      </div>
      {trend !== undefined && (
        <div className={`flex items-center mt-3 text-sm font-medium ${trend > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
          {trend > 0 ? <ArrowUpRight className="w-4 h-4 mr-1" /> : <ArrowDownRight className="w-4 h-4 mr-1" />}
          <span>{Math.abs(trend)}% vs last run</span>
        </div>
      )}
    </div>
  );
}
