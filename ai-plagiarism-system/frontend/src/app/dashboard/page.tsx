'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { scanApi } from '@/lib/api';
import { FileText, Clock, ChevronRight, BarChart2, Plus } from 'lucide-react';
import Link from 'next/link';

export default function Dashboard() {
  const [recentScans, setRecentScans] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // In a real app, we'd fetch actual scans from the backend
    // For this demo, we'll show a "Start Scanning" button if none exist
    setIsLoading(false);
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black pt-24 pb-12">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">My Dashboard</h1>
            <p className="text-zinc-600 dark:text-zinc-400">Manage and view your plagiarism reports.</p>
          </div>
          <Link href="/upload" className="btn-primary flex items-center gap-2">
            <Plus size={20} />
            New Scan
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="card bg-blue-600 border-none text-white">
            <div className="flex items-center justify-between mb-4">
              <BarChart2 size={24} />
              <span className="text-sm font-medium opacity-80">Lifetime</span>
            </div>
            <p className="text-3xl font-bold">0</p>
            <p className="text-sm opacity-80">Total Documents Scanned</p>
          </div>
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <Clock size={24} className="text-blue-600" />
              <span className="text-sm font-medium text-zinc-500">Average</span>
            </div>
            <p className="text-3xl font-bold">0%</p>
            <p className="text-sm text-zinc-500">Mean Similarity Score</p>
          </div>
          <div className="card">
            <div className="flex items-center justify-between mb-4 text-green-500">
              <FileText size={24} />
              <span className="text-sm font-medium text-zinc-500">Status</span>
            </div>
            <p className="text-3xl font-bold text-green-500">Active</p>
            <p className="text-sm text-zinc-500">System Engine Status</p>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold mb-6">Recent Activities</h2>
          
          <div className="space-y-4">
            <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
              <FileText size={48} className="mb-4 opacity-20" />
              <p>No recent scans found.</p>
              <Link href="/upload" className="text-blue-600 hover:underline mt-2">
                Upload your first document
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
