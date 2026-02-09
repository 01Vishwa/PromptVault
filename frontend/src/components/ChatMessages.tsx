'use client';

import { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import clsx from 'clsx';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: Array<{ id: number; title: string; url: string; snippet?: string }>;
    thinking?: string[];
    isStreaming?: boolean;
}

interface ThinkingState {
    isActive: boolean;
    step: string;
    steps: string[];
}

interface ChatMessagesProps {
    messages: Message[];
    thinking: ThinkingState;
}

export default function ChatMessages({ messages, thinking }: ChatMessagesProps) {
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, thinking]);

    return (
        <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={clsx(
                            "flex gap-4 animate-slide-up",
                            message.role === 'user' ? 'justify-end' : 'justify-start'
                        )}
                    >
                        {/* Avatar - Assistant */}
                        {message.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
                                <Bot size={16} className="text-accent-foreground" />
                            </div>
                        )}

                        {/* Message Content */}
                        <div
                            className={clsx(
                                "max-w-[80%] rounded-2xl px-4 py-3",
                                message.role === 'user'
                                    ? "bg-accent text-accent-foreground rounded-br-md"
                                    : "bg-card border border-border rounded-bl-md"
                            )}
                        >
                            {message.role === 'assistant' ? (
                                <div className="prose prose-invert prose-sm max-w-none">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {message.content || (message.isStreaming ? '...' : '')}
                                    </ReactMarkdown>
                                </div>
                            ) : (
                                <p className="text-sm">{message.content}</p>
                            )}

                            {/* Inline Sources */}
                            {message.sources && message.sources.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-border">
                                    <p className="text-xs text-muted-foreground mb-2">Sources</p>
                                    <div className="flex flex-wrap gap-2">
                                        {message.sources.slice(0, 3).map((source) => (
                                            <a
                                                key={source.id}
                                                href={source.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-muted text-xs text-muted-foreground hover:text-foreground transition-colors"
                                            >
                                                <span className="text-accent">[{source.id}]</span>
                                                <span className="truncate max-w-[120px]">{source.title}</span>
                                            </a>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Avatar - User */}
                        {message.role === 'user' && (
                            <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                                <User size={16} className="text-muted-foreground" />
                            </div>
                        )}
                    </div>
                ))}

                {/* Thinking State */}
                {thinking.isActive && (
                    <div className="flex gap-4 animate-fade-in">
                        <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
                            <Bot size={16} className="text-accent-foreground" />
                        </div>
                        <div className="bg-card border border-border rounded-2xl rounded-bl-md px-4 py-3">
                            <div className="flex items-center gap-3">
                                <div className="flex gap-1">
                                    {[0, 1, 2].map((i) => (
                                        <span
                                            key={i}
                                            className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot"
                                            style={{ animationDelay: `${i * 0.2}s` }}
                                        />
                                    ))}
                                </div>
                                <span className="text-sm text-muted-foreground italic">
                                    {thinking.step}
                                </span>
                            </div>
                            {thinking.steps.length > 0 && (
                                <p className="text-xs text-muted-foreground mt-2">
                                    {thinking.steps.length} reasoning step{thinking.steps.length > 1 ? 's' : ''}
                                </p>
                            )}
                        </div>
                    </div>
                )}

                <div ref={endRef} />
            </div>
        </div>
    );
}
