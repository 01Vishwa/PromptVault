'use client'

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Activity, ListChecks, PlayCircle, ShieldAlert } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: '/system', label: 'System Health', icon: <Activity className="w-5 h-5 mr-3"/> },
    { href: '/quality', label: 'Quality Metrics', icon: <LayoutDashboard className="w-5 h-5 mr-3"/> },
    { href: '/runs', label: 'Run History', icon: <PlayCircle className="w-5 h-5 mr-3"/> },
    { href: '/tasks', label: 'Task Library', icon: <ListChecks className="w-5 h-5 mr-3"/> },
    { href: '/hitl', label: 'HITL Review', icon: <ShieldAlert className="w-5 h-5 mr-3"/> },
  ];

  return (
    <div className="w-64 bg-slate-900 h-screen text-slate-300 flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold text-white tracking-widest uppercase">LoopMind</h1>
        <p className="text-xs text-slate-500 mt-1">Eval Framework</p>
      </div>
      <nav className="flex-1 px-4 space-y-2 mt-4">
        {links.map((link) => {
          const isActive = pathname.startsWith(link.href);
          return (
            <Link key={link.href} href={link.href}>
              <span className={`flex items-center px-4 py-3 rounded-md transition-colors ${
                isActive ? 'bg-indigo-600 text-white' : 'hover:bg-slate-800 hover:text-white'
              }`}>
                {link.icon}
                {link.label}
              </span>
            </Link>
          )
        })}
      </nav>
    </div>
  );
}
