'use client';

import { useState } from 'react';
import ChatInput from '@/components/ChatInput';
import ChatMessages from '@/components/ChatMessages';
import SourcePanel from '@/components/SourcePanel';

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

export default function Home() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [thinking, setThinking] = useState<ThinkingState>({
        isActive: false,
        step: '',
        steps: []
    });
    const [activeSources, setActiveSources] = useState<Message['sources']>([]);

    const handleSubmit = async (query: string, files?: File[]) => {
        if (!query.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: query.trim()
        };

        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);
        setThinking({ isActive: true, step: 'Analyzing query...', steps: ['Analyzing query...'] });

        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            isStreaming: true
        }]);

        try {
            const response = await fetch('/api/v1/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify({
                    query: userMessage.content,
                    settings: { search_depth: 'normal', enable_reflection: true }
                })
            });

            if (!response.ok) throw new Error('Stream failed');

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let accumulatedContent = '';
            let sources: Message['sources'] = [];
            let thinkingSteps: string[] = [];

            while (reader) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(line.slice(6));

                            switch (event.type) {
                                case 'thinking':
                                    const thought = event.data.thought;
                                    thinkingSteps.push(thought);
                                    setThinking({
                                        isActive: true,
                                        step: thought.includes('Search') ? 'Searching...' :
                                            thought.includes('Read') ? 'Reading...' :
                                                thought.includes('Verify') ? 'Verifying...' : 'Thinking...',
                                        steps: thinkingSteps
                                    });
                                    break;

                                case 'tool_call':
                                    setThinking(prev => ({
                                        ...prev,
                                        step: `Using ${event.data.tool}...`
                                    }));
                                    break;

                                case 'content':
                                    accumulatedContent += event.data.delta;
                                    setMessages(prev => prev.map(m =>
                                        m.id === assistantId
                                            ? { ...m, content: accumulatedContent }
                                            : m
                                    ));
                                    break;

                                case 'sources':
                                    sources = event.data.sources || [];
                                    setActiveSources(sources);
                                    break;

                                case 'done':
                                    setMessages(prev => prev.map(m =>
                                        m.id === assistantId
                                            ? { ...m, sources, thinking: thinkingSteps, isStreaming: false }
                                            : m
                                    ));
                                    break;
                            }
                        } catch (parseError) {
                            // CQ-007: Log JSON parsing errors instead of silently failing
                            console.warn('Failed to parse SSE event:', line, parseError);
                        }
                    }
                }
            }
        } catch (error) {
            setMessages(prev => prev.map(m =>
                m.id === assistantId
                    ? { ...m, content: 'Sorry, an error occurred. Please try again.', isStreaming: false }
                    : m
            ));
        } finally {
            setIsLoading(false);
            setThinking({ isActive: false, step: '', steps: [] });
        }
    };

    const hasMessages = messages.length > 0;

    return (
        <div className="flex h-full">
            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                {!hasMessages ? (
                    /* Hero State - "Ask the Web" */
                    <div className="flex-1 flex flex-col items-center justify-center px-4">
                        <h1 className="text-4xl md:text-5xl font-bold mb-4 gradient-text">
                            Ask the Web
                        </h1>
                        <p className="text-muted-foreground text-center max-w-md mb-8">
                            An agentic search engine with multi-step reasoning and intelligent synthesis.
                        </p>
                        <div className="w-full max-w-2xl">
                            <ChatInput
                                onSubmit={handleSubmit}
                                isLoading={isLoading}
                                thinking={thinking}
                            />
                        </div>
                    </div>
                ) : (
                    /* Chat State */
                    <>
                        <ChatMessages
                            messages={messages}
                            thinking={thinking}
                        />
                        <div className="p-4 border-t border-border">
                            <div className="max-w-3xl mx-auto">
                                <ChatInput
                                    onSubmit={handleSubmit}
                                    isLoading={isLoading}
                                    thinking={thinking}
                                    compact
                                />
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* Right Panel - Sources (only when chat is active) */}
            {hasMessages && activeSources && activeSources.length > 0 && (
                <SourcePanel sources={activeSources} />
            )}
        </div>
    );
}
