'use client'

import { Bell, Search, User } from 'lucide-react';

export default function TopBar() {
  return (
    <div className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8">
      <div className="flex bg-slate-100 items-center px-3 py-2 rounded-md w-96 text-slate-400">
        <Search className="w-4 h-4 mr-2" />
        <input type="text" placeholder="Search runs, tasks..." className="bg-transparent outline-none w-full text-sm text-slate-700 placeholder-slate-400" />
      </div>
      <div className="flex items-center space-x-4 text-slate-500">
        <Bell className="w-5 h-5 cursor-pointer hover:text-indigo-600" />
        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center cursor-pointer">
          <User className="w-4 h-4 text-slate-600" />
        </div>
      </div>
    </div>
  );
}
