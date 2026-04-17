import { X } from 'lucide-react';

export default function SpanDrawer({ span, onClose }: { span: any, onClose: () => void }) {
  const data = span.data?.attributes || {};

  return (
    <div className="w-80 border-l border-slate-200 bg-white h-full overflow-y-auto flex flex-col shadow-xl z-10 absolute right-0 top-0">
      <div className="p-4 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white z-20">
        <h3 className="font-semibold text-slate-800">Span Details</h3>
        <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-md">
          <X className="w-4 h-4 text-slate-500" />
        </button>
      </div>
      <div className="p-4 space-y-6 flex-1">
        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Identity</span>
          <div className="bg-slate-50 rounded p-2 text-sm text-slate-700 break-all border border-slate-100">
            {span.id}
          </div>
        </div>

        {span.type === "error" && (
            <div>
              <span className="bg-red-100 text-red-700 px-2 py-1 rounded text-xs font-bold uppercase">Error Segment</span>
            </div>
        )}

        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Attributes</span>
          <div className="space-y-2">
            {Object.entries(data).map(([k, v]) => (
                <div key={k} className="text-sm">
                    <span className="font-medium text-slate-600 block">{k}</span>
                    <span className="text-slate-800 break-words">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
