'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    MessageSquare,
    Plus,
    ChevronLeft,
    ChevronRight,
    Trash2
} from 'lucide-react';
import clsx from 'clsx';

interface ChatThread {
    id: string;
    title: string;
    timestamp: Date;
}

export default function Sidebar() {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [threads, setThreads] = useState<ChatThread[]>([
        { id: '1', title: 'AI developments 2024', timestamp: new Date() },
        { id: '2', title: 'NVIDIA vs AMD comparison', timestamp: new Date() },
        { id: '3', title: 'Quantum computing basics', timestamp: new Date() },
    ]);
    const [activeThread, setActiveThread] = useState<string | null>(null);

    const handleNewChat = () => {
        const newThread: ChatThread = {
            id: Date.now().toString(),
            title: 'New conversation',
            timestamp: new Date()
        };
        setThreads(prev => [newThread, ...prev]);
        setActiveThread(newThread.id);
    };

    const handleDeleteThread = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setThreads(prev => prev.filter(t => t.id !== id));
        if (activeThread === id) setActiveThread(null);
    };

    return (
        <motion.aside
            initial={false}
            animate={{ width: isCollapsed ? 64 : 280 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="h-full bg-card border-r border-border flex flex-col"
        >
            {/* Header */}
            <div className="p-4 flex items-center justify-between border-b border-border">
                <AnimatePresence mode="wait">
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex items-center gap-2"
                        >
                            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
                                <MessageSquare size={16} className="text-accent-foreground" />
                            </div>
                            <span className="font-semibold text-foreground">Axiom AI</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="p-2 rounded-lg hover:bg-muted transition-colors"
                >
                    {isCollapsed ? (
                        <ChevronRight size={18} className="text-muted-foreground" />
                    ) : (
                        <ChevronLeft size={18} className="text-muted-foreground" />
                    )}
                </button>
            </div>

            {/* New Chat Button */}
            <div className="p-3">
                <button
                    onClick={handleNewChat}
                    className={clsx(
                        "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg",
                        "bg-accent hover:bg-accent-light transition-colors",
                        "text-accent-foreground font-medium text-sm"
                    )}
                >
                    <Plus size={18} />
                    {!isCollapsed && <span>New Chat</span>}
                </button>
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto px-3 pb-3">
                <AnimatePresence mode="wait">
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                        >
                            <p className="text-xs text-muted-foreground px-3 py-2 uppercase tracking-wider">
                                History
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className="space-y-1">
                    {threads.map((thread) => (
                        <motion.div
                            key={thread.id}
                            onClick={() => setActiveThread(thread.id)}
                            className={clsx(
                                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left group cursor-pointer",
                                "transition-colors duration-150",
                                activeThread === thread.id
                                    ? "bg-muted text-foreground"
                                    : "hover:bg-muted/50 text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <MessageSquare size={16} className="flex-shrink-0" />

                            {!isCollapsed && (
                                <>
                                    <span className="flex-1 truncate text-sm">
                                        {thread.title}
                                    </span>
                                    <button
                                        onClick={(e) => handleDeleteThread(thread.id, e)}
                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-error/20 rounded transition-all"
                                    >
                                        <Trash2 size={14} className="text-error" />
                                    </button>
                                </>
                            )}
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Footer */}
            {!isCollapsed && (
                <div className="p-4 border-t border-border">
                    <p className="text-xs text-muted-foreground text-center">
                        Powered by ReACT & ReWOO
                    </p>
                </div>
            )}
        </motion.aside>
    );
}
