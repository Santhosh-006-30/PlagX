'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { FileText, Upload, LayoutDashboard, LogOut, Shield } from 'lucide-react';

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  const isActive = (path: string) => pathname === path;

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 z-50">
      <div className="max-w-7xl mx-auto px-4 h-full flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2 font-bold text-xl text-blue-600">
          <Shield size={28} />
          <span>PlagX</span>
        </Link>

        <div className="flex items-center gap-6">
          <Link 
            href="/dashboard" 
            className={`flex items-center gap-1 text-sm font-medium transition-colors ${isActive('/dashboard') ? 'text-blue-600' : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white'}`}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </Link>
          <Link 
            href="/upload" 
            className={`flex items-center gap-1 text-sm font-medium transition-colors ${isActive('/upload') ? 'text-blue-600' : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white'}`}
          >
            <Upload size={18} />
            Upload
          </Link>
        </div>
      </div>
    </nav>
  );
}
