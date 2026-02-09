'use client';

import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from 'react';
import { Send, Paperclip, X, Loader2 } from 'lucide-react';
import clsx from 'clsx';

interface ThinkingState {
    isActive: boolean;
    step: string;
    steps: string[];
}

interface ChatInputProps {
    onSubmit: (query: string, files?: File[]) => void;
    isLoading: boolean;
    thinking: ThinkingState;
    compact?: boolean;
}

export default function ChatInput({
    onSubmit,
    isLoading,
    thinking,
    compact = false
}: ChatInputProps) {
    const [input, setInput] = useState('');
    const [files, setFiles] = useState<File[]>([]);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
        }
    }, [input]);

    const handleSubmit = (e?: FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || isLoading) return;

        onSubmit(input.trim(), files.length > 0 ? files : undefined);
        setInput('');
        setFiles([]);
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = e.target.files;
        if (selectedFiles) {
            setFiles(prev => [...prev, ...Array.from(selectedFiles)]);
        }
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    return (
        <div className="w-full">
            {/* Thinking Indicator */}
            {thinking.isActive && (
                <div className="mb-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-accent/10 border border-accent/20 animate-fade-in">
                    <div className="flex gap-1">
                        {[0, 1, 2].map((i) => (
                            <span
                                key={i}
                                className="w-2 h-2 rounded-full bg-accent animate-pulse-dot"
                                style={{ animationDelay: `${i * 0.2}s` }}
                            />
                        ))}
                    </div>
                    <span className="text-sm text-accent font-medium">{thinking.step}</span>
                </div>
            )}

            {/* File Attachments */}
            {files.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                    {files.map((file, index) => (
                        <div
                            key={index}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted text-sm"
                        >
                            <Paperclip size={14} className="text-muted-foreground" />
                            <span className="text-foreground truncate max-w-[150px]">
                                {file.name}
                            </span>
                            <button
                                onClick={() => removeFile(index)}
                                className="p-0.5 hover:bg-error/20 rounded transition-colors"
                            >
                                <X size={14} className="text-muted-foreground hover:text-error" />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Input Form */}
            <form onSubmit={handleSubmit}>
                <div
                    className={clsx(
                        "relative flex items-end gap-2 rounded-2xl",
                        "bg-input/80 backdrop-blur-glass border border-border",
                        "focus-within:border-accent focus-within:shadow-glow-sm",
                        "transition-all duration-200",
                        compact ? "p-2" : "p-3"
                    )}
                >
                    {/* File Upload Button */}
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept=".csv,.json,.txt,.pdf"
                        onChange={handleFileSelect}
                        className="hidden"
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className={clsx(
                            "p-2 rounded-lg hover:bg-muted transition-colors",
                            "text-muted-foreground hover:text-foreground"
                        )}
                    >
                        <Paperclip size={18} />
                    </button>

                    {/* Textarea */}
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask anything..."
                        disabled={isLoading}
                        rows={1}
                        className={clsx(
                            "flex-1 bg-transparent resize-none outline-none",
                            "text-foreground placeholder:text-muted-foreground",
                            "py-2 px-1 min-h-[40px] max-h-[200px]",
                            "disabled:opacity-50 disabled:cursor-not-allowed"
                        )}
                    />

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className={clsx(
                            "p-2.5 rounded-xl transition-all duration-200",
                            "disabled:opacity-40 disabled:cursor-not-allowed",
                            input.trim() && !isLoading
                                ? "bg-accent hover:bg-accent-light text-accent-foreground shadow-glow-sm"
                                : "bg-muted text-muted-foreground"
                        )}
                    >
                        {isLoading ? (
                            <Loader2 size={18} className="animate-spin" />
                        ) : (
                            <Send size={18} />
                        )}
                    </button>
                </div>
            </form>

            {/* Hint */}
            {!compact && (
                <p className="text-xs text-muted-foreground text-center mt-3">
                    Press <kbd className="px-1.5 py-0.5 rounded bg-muted text-foreground mx-1">Enter</kbd> to send,
                    <kbd className="px-1.5 py-0.5 rounded bg-muted text-foreground mx-1">Shift + Enter</kbd> for new line
                </p>
            )}
        </div>
    );
}
