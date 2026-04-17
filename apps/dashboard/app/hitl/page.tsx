'use client'

export default function HITLQueue() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden p-8 h-full">
        <h2 className="text-2xl font-bold text-slate-800">Human-In-The-Loop Review</h2>
        <p className="text-slate-500 mt-2">Awaiting review for pipeline failures</p>
        <div className="mt-8 border border-dashed border-slate-300 rounded-lg p-16 text-center text-slate-400 flex flex-col items-center justify-center h-[400px]">
            Annotation tooling and replay logs attach here.
        </div>
    </div>
  );
}
