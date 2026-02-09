'use client';

import { ExternalLink, FileText } from 'lucide-react';

interface Source {
    id: number;
    title: string;
    url: string;
    snippet?: string;
}

interface SourcePanelProps {
    sources: Source[];
}

export default function SourcePanel({ sources }: SourcePanelProps) {
    const getDomain = (url: string): string => {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch {
            return url;
        }
    };

    return (
        <aside className="w-72 border-l border-border bg-card/50 overflow-y-auto">
            <div className="p-4 border-b border-border">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <FileText size={16} className="text-accent" />
                    Sources ({sources.length})
                </h3>
            </div>

            <div className="p-3 space-y-2">
                {sources.map((source) => (
                    <a
                        key={source.id}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-3 rounded-lg bg-muted hover:bg-muted/80 border border-border hover:border-accent/50 transition-all group"
                    >
                        <div className="flex items-start justify-between gap-2 mb-1">
                            <span className="text-xs font-medium text-accent">
                                [{source.id}]
                            </span>
                            <ExternalLink
                                size={12}
                                className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                            />
                        </div>

                        <h4 className="text-sm font-medium text-foreground line-clamp-2 mb-1">
                            {source.title}
                        </h4>

                        <p className="text-xs text-muted-foreground">
                            {getDomain(source.url)}
                        </p>

                        {source.snippet && (
                            <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                                {source.snippet}
                            </p>
                        )}
                    </a>
                ))}
            </div>
        </aside>
    );
}
