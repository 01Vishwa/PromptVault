import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/Sidebar';

const inter = Inter({
    subsets: ['latin'],
    display: 'swap',
    variable: '--font-inter'
});

export const metadata: Metadata = {
    title: 'Axiom AI — Ask the Web',
    description: 'An agentic search engine with multi-step reasoning, real-time web search, and intelligent synthesis.',
    keywords: ['AI', 'search', 'ReACT', 'agent', 'web search', 'agentic'],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className={`${inter.variable} font-sans`}>
                <div className="flex h-screen overflow-hidden">
                    {/* Left Sidebar */}
                    <Sidebar />

                    {/* Main Content */}
                    <main className="flex-1 overflow-auto">
                        {children}
                    </main>
                </div>
            </body>
        </html>
    );
}
