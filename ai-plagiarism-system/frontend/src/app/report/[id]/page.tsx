'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import Navbar from '@/components/Navbar';
import { scanApi, getFileUrl } from '@/lib/api';
import { Loader2, AlertCircle, FileText, ChevronRight, Hash, Percent, BarChart2 } from 'lucide-react';

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
  AreaChart, Area, XAxis, YAxis, Tooltip as ChartTooltip,
  BarChart, Bar
} from 'recharts';

interface Match {
  text: string;
  source: string;
}

const COLORS = ['#ef4444', '#f97316', '#eab308', '#3b82f6'];

export default function ReportPage() {
  const { id } = useParams();
  const [reportData, setReportData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    const fetchReport = async () => {
      try {
        const { data } = await scanApi.getReport(id as string);
        setReportData(data);
        
        // If job is still processing or queued, poll every 3 seconds
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
        <p className="text-zinc-600 dark:text-zinc-400">Loading your report...</p>
      </div>
    );
  }

  if (error || !reportData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 dark:bg-black">
        <AlertCircle className="text-red-600 mb-4" size={48} />
        <p className="text-xl font-bold mb-2">Error</p>
        <p className="text-zinc-600 dark:text-zinc-400">{error || 'Report not found.'}</p>
      </div>
    );
  }

  const { job, document_title, document_text, document_segments } = reportData;
  const isProcessing = job.status === 'processing' || job.status === 'queued';
  const results = job.results || { 
    similarity: 0, 
    ai_score: 0,
    matches: [], 
    source_breakdown: {}, 
    match_groups: {}, 
    confidence: 0,
    integrity_flags: [],
    source_diversity: 0,
    ai_details: {}
  };

  // --- DEBUG: Log API response ---
  console.log('REPORT DATA:', reportData);
  console.log('RESULTS:', results);
  console.log('AI SCORE:', results.ai_score);
  console.log('SIMILARITY:', results.similarity);
  console.log('DOCUMENT SEGMENTS:', document_segments);
  console.log('MATCHES:', results.matches);

  // Build unified segments for highlighting
  // Priority: document_segments (sentence-level with ai_score) > results.matches (plagiarism matches)
  const highlightSegments = (document_segments || []).length > 0
    ? document_segments.filter((seg: any) => 
        seg.highlight || (seg.ai_score || 0) > 20 || (seg.similarity_score || 0) > 20
      )
    : results.matches.map((m: any) => ({
        text: m.text,
        start: 0,
        end: 0,
        ai_score: results.ai_score || 0,
        similarity_score: m.similarity || 0,
        similarity: m.similarity || 0,
        source: m.source,
        category: m.category,
        highlight: true
      }));

  // 1. Group and Rank Sources (Top 10)
  const sourceRanking = reportData ? Object.entries(
    results.matches.reduce((acc: any, match: any) => {
      const sourceId = match.source || 'Unknown Source';
      if (!acc[sourceId]) acc[sourceId] = { similarity: 0, category: match.category };
      acc[sourceId].similarity = Math.max(acc[sourceId].similarity, match.similarity);
      return acc;
    }, {})
  ).sort((a: any, b: any) => b[1].similarity - a[1].similarity).slice(0, 10) : [];

  // 2. Create a map of Source ID -> Index [1, 2, 3...]
  const sourceToIndexMap = new Map(sourceRanking.map(([id], idx) => [id, idx + 1]));

  // 3. Prepare Chart Data
  const chartData = Object.entries(results.match_groups || {}).map(([key, val]) => ({
    name: key.replace('_', ' '),
    value: val
  }));

  // 4. Density Data (Simplified Heatmap) — use document_segments or matches
  const docLen = document_text?.length || 1;
  const densityBins = 40;
  const allSegmentsForDensity = (document_segments || []).length > 0
    ? document_segments.filter((s: any) => s.highlight)
    : results.matches;
  
  const densityData = Array.from({ length: densityBins }, (_, i) => {
    const binStart = (i / densityBins) * docLen;
    const binEnd = ((i + 1) / densityBins) * docLen;
    const hasMatch = allSegmentsForDensity.some((m: any) => {
      const mStart = m.start ?? m.start_index ?? 0;
      const mEnd = m.end ?? m.end_index ?? 0;
      return (mStart >= binStart && mStart < binEnd) || (mEnd > binStart && mEnd <= binEnd);
    });
    return { bin: i, density: hasMatch ? 1 : 0 };
  });

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black pt-20">
      <Navbar />
      
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Main Dashboard - Left Side */}
          <div className="lg:col-span-4 space-y-6">
            
            {/* Audit Overview */}
            <div className="card p-8 bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Academic Audit</h2>
                <div className="flex gap-2">
                  <div className="px-3 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded-full text-[10px] font-black uppercase tracking-widest">
                    Diversity: {results.source_diversity}
                  </div>
                  <div className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full text-[10px] font-black uppercase tracking-widest">
                    Confidence: {results.confidence}%
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="flex flex-col items-center justify-center py-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-2xl">
                  <span className="text-4xl font-black">{results.similarity}%</span>
                  <span className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mt-1">Similarity</span>
                </div>
                <div className="flex flex-col items-center justify-center py-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-2xl">
                  <span className="text-4xl font-black">{results.ai_score || 0}%</span>
                  <span className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mt-1">AI Audit</span>
                </div>
              </div>

              {/* Match Distribution Chart */}
              <div className="mb-8">
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 mb-4 text-center">Match Distribution</h3>
                <div className="h-64 w-full relative">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <ChartTooltip 
                        contentStyle={{ backgroundColor: '#18181b', border: 'none', borderRadius: '12px', fontSize: '10px', color: '#fff' }}
                        itemStyle={{ color: '#fff' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Match Density Heatmap */}
              <div className="space-y-4">
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">Document Density Map</h3>
                <div className="flex gap-1 h-3 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden p-0.5">
                  {densityData.map((d, i) => (
                    <div 
                      key={i} 
                      className={`flex-1 h-full rounded-full transition-all duration-500 ${d.density > 0 ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'bg-transparent'}`}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-[9px] font-bold text-zinc-500 uppercase tracking-widest">
                  <span>Start</span>
                  <span>End</span>
                </div>
              </div>

              {/* Match Categories */}
              <div className="mt-8 space-y-4">
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">Match Classification</h3>
                <div className="grid grid-cols-1 gap-2">
                  {Object.entries(results.match_groups || {}).map(([key, val]: [string, any]) => (
                    <div key={key} className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl border border-zinc-100 dark:border-zinc-700/50">
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${key === 'not_cited' ? 'bg-red-500' : key === 'missing_quotes' ? 'bg-orange-500' : 'bg-yellow-500'}`} />
                        <span className="text-xs font-bold capitalize">{key.replace('_', ' ')}</span>
                      </div>
                      <span className="text-xs font-black">{Math.round(val)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Integrity Dashboard */}
            {results.integrity_flags?.length > 0 && (
              <div className="card p-8 bg-red-50/50 dark:bg-red-950/10 border-red-100 dark:border-red-900/20 shadow-xl">
                <h2 className="text-lg font-bold text-red-700 dark:text-red-400 flex items-center gap-2 mb-4">
                  <AlertCircle size={20} />
                  Integrity Dashboard
                </h2>
                <div className="space-y-2">
                  {results.integrity_flags.map((flag: string, idx: number) => (
                    <div key={idx} className="text-xs font-medium text-red-600 dark:text-red-300 bg-red-100/50 dark:bg-red-900/30 p-3 rounded-lg border border-red-200/50 dark:border-red-800/30">
                      • {flag}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top Sources Ranked */}
            <div className="card p-8 bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 shadow-xl">
              <h2 className="text-xl font-bold mb-6">Top Ranked Sources</h2>
              <div className="space-y-3">
                {sourceRanking.length > 0 ? sourceRanking.map(([source, data]: [any, any], idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-2xl border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700 transition-all cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 bg-blue-600 text-white rounded-lg flex items-center justify-center text-xs font-black">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="text-[11px] font-black truncate max-w-[150px] uppercase tracking-wider">Source {source.slice(0, 8)}</div>
                        <div className="text-[10px] text-zinc-500 capitalize">{data.category} match</div>
                      </div>
                    </div>
                    <div className={`text-xs font-black ${data.similarity > 70 ? 'text-red-500' : 'text-orange-500'}`}>
                      {data.similarity}%
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-8 text-zinc-500 text-xs">No significant matches found.</div>
                )}
              </div>
            </div>
          </div>

          {/* Document Viewer - Right Side */}
          <div className="lg:col-span-8">
            <div className="card overflow-hidden bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 shadow-2xl min-h-[900px] flex flex-col">
              <div className="p-4 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-900/50 backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-600 text-white rounded-lg">
                    <FileText size={18} />
                  </div>
                  <h3 className="font-bold text-sm">Integrity Audit Viewer</h3>
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-4 text-[9px] font-black uppercase tracking-[0.2em] text-zinc-400">
                    <div className="flex items-center gap-1.5"><div className="w-2 h-2 bg-red-500 rounded-full" /> High</div>
                    <div className="flex items-center gap-1.5"><div className="w-2 h-2 bg-orange-500 rounded-full" /> Med</div>
                    <div className="flex items-center gap-1.5"><div className="w-2 h-2 bg-yellow-400 rounded-full" /> Low</div>
                  </div>
                </div>
              </div>
              <div className="flex-1 p-8 bg-zinc-100/30 dark:bg-zinc-950/30">
                {reportData && (
                  <DocumentViewer 
                    fileUrl={getFileUrl(reportData.file_key || '')} 
                    fileType={reportData.file_type || 'txt'} 
                    segments={highlightSegments.map((seg: any, idx: number) => ({
                      ...seg,
                      source_index: seg.source ? sourceToIndexMap.get(seg.source) : idx + 1,
                      similarity: seg.similarity_score || seg.similarity || 0,
                    }))}
                    fullText={document_text}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function renderHighlightedText(text: string, matches: Match[]) {
  if (!text || !matches || matches.length === 0) return text;

  // Sort matches by length (descending) to avoid highlighting substrings of longer matches first
  const sortedMatches = [...matches].sort((a, b) => b.text.length - a.text.length);
  
  let parts: (string | JSX.Element)[] = [text];

  sortedMatches.forEach((match, matchIdx) => {
    const newParts: (string | JSX.Element)[] = [];
    
    // Create a regex from the match text, escaping special characters and allowing flexible whitespace
    const escapedMatch = match.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+');
    const regex = new RegExp(`(${escapedMatch})`, 'gi');

    parts.forEach((part) => {
      if (typeof part !== 'string') {
        newParts.push(part);
        return;
      }

      const segments = part.split(regex);
      segments.forEach((segment, segmentIdx) => {
        if (segment.match(regex)) {
          newParts.push(
            <span 
              key={`match-${matchIdx}-${segmentIdx}`} 
              className="bg-red-100 dark:bg-red-900/40 border-b-2 border-red-500 rounded-sm px-1 font-medium transition-colors hover:bg-red-200 dark:hover:bg-red-800 cursor-help" 
              title={`Match from Source: ${match.source}`}
            >
              {segment}
            </span>
          );
        } else if (segment !== '') {
          newParts.push(segment);
        }
      });
    });
    parts = newParts;
  });

  return parts;
}
