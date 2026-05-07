'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import Navbar from '@/components/Navbar';
import { scanApi, getFileUrl } from '@/lib/api';
import { 
  Loader2, AlertCircle, FileText, ChevronRight, Hash, 
  Percent, BarChart2, Zap, Shield, Search, Info, X, ExternalLink 
} from 'lucide-react';

const DocumentViewer = dynamic(() => import('@/components/DocumentViewer'), { 
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center p-20 bg-zinc-50 dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="animate-spin text-blue-600" size={32} />
        <p className="text-zinc-500 font-medium">Initializing high-fidelity viewer...</p>
      </div>
    </div>
  )
});

import { 
  PieChart, Pie, Cell, ResponsiveContainer, 
  Tooltip as ChartTooltip
} from 'recharts';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#a855f7'];

export default function ReportPage() {
  const { id } = useParams();
  const [reportData, setReportData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedMatch, setSelectedMatch] = useState<any>(null);
  const [showAIHeatmap, setShowAIHeatmap] = useState(false);

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    const fetchReport = async () => {
      try {
        const { data } = await scanApi.getReport(id as string);
        setReportData(data);
        
        if (data.job.status === 'processing' || data.job.status === 'queued') {
          pollInterval = setTimeout(fetchReport, 3000);
        }
      } catch (err: any) {
        setError('Failed to load report.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchReport();
    return () => clearTimeout(pollInterval);
  }, [id]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 dark:bg-black">
        <Loader2 className="animate-spin text-blue-600 mb-4" size={48} />
        <p className="text-zinc-600 dark:text-zinc-400">Generating Enterprise Report...</p>
      </div>
    );
  }

  if (error || !reportData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 dark:bg-black">
        <AlertCircle className="text-red-600 mb-4" size={48} />
        <p className="text-xl font-bold mb-2">Access Denied or Report Not Found</p>
        <p className="text-zinc-600 dark:text-zinc-400">{error || 'Please contact support if this persists.'}</p>
      </div>
    );
  }

  const { job, document_title, document_text, document_segments } = reportData;
  const isProcessing = job.status === 'processing' || job.status === 'queued';
  
  // Aggregate highlights
  const highlights = document_segments || [];
  
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black pt-16 flex flex-col">
      <Navbar />
      
      {/* Top Header Bar */}
      <div className="h-14 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 px-6 flex items-center justify-between z-40">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium">
            <Shield size={14} className="text-blue-600" />
            <span>PlagX Analysis</span>
            <ChevronRight size={14} />
            <span className="text-zinc-900 dark:text-white font-bold">{document_title}</span>
          </div>
          {isProcessing && (
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-600 rounded-full text-[10px] font-bold animate-pulse">
              <Loader2 size={12} className="animate-spin" />
              Processing: {job.progress_detail}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowAIHeatmap(!showAIHeatmap)}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${showAIHeatmap ? 'bg-purple-600 text-white shadow-lg' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 hover:bg-zinc-200'}`}
          >
            <Zap size={14} />
            AI Heatmap {showAIHeatmap ? 'ON' : 'OFF'}
          </button>
          <button className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-bold shadow-lg hover:bg-blue-700 transition-all flex items-center gap-2">
            <FileText size={14} />
            Export PDF
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Analytics */}
        <div className="w-[400px] bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 overflow-y-auto p-6 space-y-8 hidden xl:block">
          <div>
            <h2 className="text-xs font-black uppercase tracking-widest text-zinc-400 mb-6 flex items-center gap-2">
              <BarChart2 size={16} />
              Originality Scorecard
            </h2>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl border border-zinc-100 dark:border-zinc-800 flex flex-col items-center">
                <span className="text-3xl font-black text-red-500">{job.overall_score || 0}%</span>
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mt-1">Similarity</span>
              </div>
              <div className="p-4 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl border border-zinc-100 dark:border-zinc-800 flex flex-col items-center">
                <span className="text-3xl font-black text-purple-500">{job.ai_probability || 0}%</span>
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mt-1">AI Audit</span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-zinc-400">Detected Sources</h3>
            <div className="space-y-3">
              {highlights.filter((h: any) => h.source_id && h.source_id !== 'null').map((match: any, idx: number) => (
                <div 
                  key={idx}
                  onClick={() => setSelectedMatch(match)}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${selectedMatch?.id === match.id ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/10' : 'border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/30 hover:bg-zinc-100 dark:hover:border-zinc-800'}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-0.5 bg-blue-600 text-white text-[10px] font-black rounded-md">SOURCE {idx + 1}</span>
                    <span className="text-xs font-black text-red-500">{Math.round(match.confidence * 100)}%</span>
                  </div>
                  <div className="text-[11px] font-bold truncate text-zinc-900 dark:text-zinc-200 uppercase tracking-tighter">
                    {match.source_id}
                  </div>
                </div>
              ))}
              {highlights.filter((h: any) => h.source_id && h.source_id !== 'null').length === 0 && (
                <div className="text-center py-8 text-zinc-500 text-xs font-medium bg-zinc-50 dark:bg-zinc-900/30 rounded-2xl border border-dashed border-zinc-200 dark:border-zinc-800">
                  No matches detected.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center: Main Viewer */}
        <div className="flex-1 overflow-y-auto bg-zinc-100 dark:bg-zinc-900 p-8 flex flex-col items-center">
          <div className="w-full max-w-[900px] bg-white dark:bg-zinc-950 shadow-2xl rounded-sm min-h-[1000px]">
            {reportData && (
              <DocumentViewer 
                fileUrl={getFileUrl(reportData.file_key || '')} 
                fileType={reportData.file_type || 'txt'} 
                segments={highlights.filter((h: any) => showAIHeatmap || h.type !== 'ai_generated')}
                fullText={document_text}
              />
            )}
          </div>
        </div>

        {/* Right Sidebar: Side-by-Side Comparison */}
        {selectedMatch && (
          <div className="w-[500px] bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-800 flex flex-col z-40 animate-in slide-in-from-right duration-300 shadow-2xl">
            <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-900/50 backdrop-blur-md">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <Search size={16} className="text-blue-600" />
                Source Comparison
              </h3>
              <button 
                onClick={() => setSelectedMatch(null)}
                className="p-1.5 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-full transition-all"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Your Document</span>
                  <span className={`px-2 py-0.5 text-white text-[10px] font-black rounded uppercase ${selectedMatch.type === 'exact_plagiarism' ? 'bg-red-500' : 'bg-orange-500'}`}>
                    {selectedMatch.type.replace('_', ' ')}
                  </span>
                </div>
                <div className="p-4 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl border-l-4 border-red-500 italic text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
                  "{document_text.slice(selectedMatch.start, selectedMatch.end)}"
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">External Source</span>
                  <a href="#" className="text-blue-600 hover:underline text-[10px] font-black uppercase flex items-center gap-1">
                    Verify Link <ExternalLink size={10} />
                  </a>
                </div>
                <div className="p-4 bg-blue-50/50 dark:bg-blue-900/10 rounded-2xl border-l-4 border-blue-500 italic text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
                  "Source text retrieval and comparison visualization is available in the full report view. This segment represents the matching content found in the external database."
                </div>
              </div>

              <div className="p-4 bg-zinc-100 dark:bg-zinc-900 rounded-2xl space-y-4 border border-zinc-200 dark:border-zinc-800">
                <h4 className="text-xs font-black uppercase tracking-widest flex items-center gap-2 text-zinc-500">
                  <Info size={14} className="text-blue-600" />
                  Match Meta
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-[9px] font-black text-zinc-400 uppercase">Certainty</div>
                    <div className="text-sm font-black">{Math.round(selectedMatch.confidence * 100)}%</div>
                  </div>
                  <div>
                    <div className="text-[9px] font-black text-zinc-400 uppercase">Analysis Engine</div>
                    <div className="text-sm font-black">Hybrid Winnowing</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="p-6 border-t border-zinc-200 dark:border-zinc-800">
              <button className="w-full py-3 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-xl font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-all shadow-xl">
                Generate Integrity Challenge
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
