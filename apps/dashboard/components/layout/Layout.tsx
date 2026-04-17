'use client'

import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
        <div className="flex h-screen bg-slate-50 overflow-hidden text-slate-800">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto p-8">
            {children}
            </main>
        </div>
        </div>
    </QueryClientProvider>
  );
}
