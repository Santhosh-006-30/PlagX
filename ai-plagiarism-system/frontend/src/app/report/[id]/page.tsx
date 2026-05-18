'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import Navbar from '@/components/Navbar';
import { scanApi, getFileUrl } from '@/lib/api';
import { Loader2, AlertCircle, FileText, Download, ShieldCheck, Info } from 'lucide-react';
import SourceSidebar from '@/components/SourceSidebar';

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

export default function ReportPage() {
  const { id } = useParams();
  const [reportData, setReportData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<string[]>(['exact', 'semantic', 'ai']);

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
        <p className="text-zinc-600 dark:text-zinc-400">Loading enterprise audit report...</p>
      </div>
    );
  }

  if (error || !reportData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 dark:bg-black">
        <AlertCircle className="text-red-600 mb-4" size={48} />
        <p className="text-xl font-bold mb-2">Analysis Failed</p>
        <p className="text-zinc-600 dark:text-zinc-400">{error || 'Report not found.'}</p>
      </div>
    );
  }

  const { job, document_title, document_text, highlight_regions } = reportData;
  const results = job.results || { overall_similarity: 0, ai_score: 0, matches: [], explainability: {} };
  const explain = results.explainability || { summary: "No summary available.", risk_level: "Unknown" };

  // Filter highlights based on user toggles
  const filteredHighlights = (highlight_regions || []).filter((h: any) => 
    activeFilters.includes(h.type)
  );

  const toggleFilter = (type: string) => {
    setActiveFilters(prev => 
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  };

  return (
    <div className="h-screen flex flex-col bg-zinc-50 dark:bg-black overflow-hidden">
      <Navbar />
      
      <div className="flex-1 flex overflow-hidden pt-16">
        {/* Main Document Area */}
        <div className="flex-1 overflow-y-auto bg-zinc-100 dark:bg-zinc-950 p-4 lg:p-8">
          <div className="max-w-4xl mx-auto">
            
            {/* Hardened Header */}
            <div className="mb-8 flex items-start justify-between bg-white dark:bg-zinc-900 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 shadow-sm">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{document_title}</h1>
                  <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    explain.risk_level === 'Critical' || explain.risk_level === 'High' 
                      ? 'bg-red-100 text-red-700' 
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {explain.risk_level} Risk
                  </span>
                </div>
                <div className="flex items-center gap-4 text-zinc-500 text-sm">
                  <span className="flex items-center gap-1.5"><FileText size={14}/> ID: {id.slice(0,8)}</span>
                  <span className="flex items-center gap-1.5"><ShieldCheck size={14}/> Enterprise Hardened</span>
                </div>
                
                {/* Explainability Card */}
                <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-100 dark:border-blue-900/30 flex gap-3">
                  <Info className="text-blue-600 flex-shrink-0 mt-0.5" size={18} />
                  <p className="text-xs text-blue-800 dark:text-blue-300 leading-relaxed italic">
                    {explain.summary}
                  </p>
                </div>
              </div>

              <div className="flex gap-8 items-center pl-8">
                <div className="text-right">
                  <p className="text-3xl font-black text-red-600 leading-none">{Math.round(job.overall_score || 0)}%</p>
                  <p className="text-[10px] font-bold text-zinc-400 uppercase mt-1">Similarity</p>
                </div>
                <button className="p-3 bg-zinc-100 dark:bg-zinc-800 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors">
                  <Download size={20} className="text-zinc-600 dark:text-zinc-400" />
                </button>
              </div>
            </div>

            {/* View Toggles */}
            <div className="flex gap-2 mb-4">
              {[
                { id: 'exact', label: 'Exact Matches', color: 'bg-red-500' },
                { id: 'semantic', label: 'Paraphrasing', color: 'bg-orange-500' },
                { id: 'ai', label: 'AI Heatmap', color: 'bg-purple-500' }
              ].map(filter => (
                <button
                  key={filter.id}
                  onClick={() => toggleFilter(filter.id)}
                  className={`px-4 py-2 rounded-full text-xs font-bold border transition-all flex items-center gap-2 ${
                    activeFilters.includes(filter.id) 
                      ? 'bg-white dark:bg-zinc-800 border-zinc-300' 
                      : 'opacity-40 border-transparent grayscale'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full ${filter.color}`} />
                  {filter.label}
                </button>
              ))}
            </div>

            <div className="shadow-2xl mb-20">
              <DocumentViewer 
                fileUrl={getFileUrl(reportData.file_key || '')} 
                fileType={reportData.file_type || 'txt'} 
                segments={filteredHighlights}
                fullText={document_text}
                onSegmentClick={(seg) => {
                  if (seg.source_id) setSelectedSourceId(seg.source_id);
                }}
              />
            </div>
          </div>
        </div>

        {/* Comparison Sidebar */}
        <div className="w-[400px] flex-shrink-0">
          <SourceSidebar 
            sources={results.matches || []}
            overallSimilarity={Math.round(job.overall_score || 0)}
            aiProbability={Math.round(job.ai_probability || 0)}
            onSourceClick={(id) => setSelectedSourceId(id)}
          />
        </div>
      </div>
    </div>
  );
}
