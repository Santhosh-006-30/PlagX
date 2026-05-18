'use client';

import React from 'react';
import { ExternalLink, CheckCircle, Shield, AlertCircle } from 'lucide-react';

interface SourceMatch {
  source: string;
  url?: string;
  similarity: number;
  match_type: 'exact' | 'semantic' | 'ai';
  text?: string;
}

interface SourceSidebarProps {
  sources: SourceMatch[];
  aiProbability: number;
  overallSimilarity: number;
  onSourceClick?: (sourceId: string) => void;
}

const SourceSidebar: React.FC<SourceSidebarProps> = ({ 
  sources, 
  aiProbability, 
  overallSimilarity,
  onSourceClick 
}) => {
  return (
    <div className="flex flex-col h-full bg-zinc-50 dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-800 w-full overflow-y-auto">
      {/* Summary Header */}
      <div className="p-6 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 mb-4">Originality Breakdown</h2>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-red-50 dark:bg-red-950/20 p-4 rounded-lg border border-red-100 dark:border-red-900/30">
            <p className="text-2xl font-bold text-red-600">{overallSimilarity}%</p>
            <p className="text-xs text-red-800 dark:text-red-400 font-medium">Similarity</p>
          </div>
          <div className="bg-purple-50 dark:bg-purple-950/20 p-4 rounded-lg border border-purple-100 dark:border-purple-900/30">
            <p className="text-2xl font-bold text-purple-600">{aiProbability}%</p>
            <p className="text-xs text-purple-800 dark:text-purple-400 font-medium">AI Prob.</p>
          </div>
        </div>
      </div>

      {/* Sources List */}
      <div className="flex-1 p-6">
        <h3 className="text-xs font-semibold uppercase text-zinc-400 mb-4">Ranked Sources</h3>
        <div className="space-y-3">
          {sources.length > 0 ? (
            sources.map((source, idx) => (
              <button
                key={idx}
                onClick={() => onSourceClick?.(source.source)}
                className="w-full text-left group bg-white dark:bg-zinc-950 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 hover:border-blue-500 transition-all shadow-sm hover:shadow-md"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                    source.match_type === 'exact' ? 'bg-red-100 text-red-700' : 
                    source.match_type === 'semantic' ? 'bg-orange-100 text-orange-700' : 
                    'bg-purple-100 text-purple-700'
                  }`}>
                    {source.match_type}
                  </span>
                  <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{Math.round(source.similarity)}%</span>
                </div>
                <h4 className="text-sm font-medium text-zinc-800 dark:text-zinc-200 mb-2 line-clamp-1">
                  {source.source.length > 20 ? source.source.slice(0, 30) + '...' : source.source}
                </h4>
                {source.text && (
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 italic line-clamp-2 border-l-2 border-zinc-200 dark:border-zinc-800 pl-2 mt-2">
                    "{source.text}"
                  </p>
                )}
              </button>
            ))
          ) : (
            <div className="text-center py-12 opacity-40">
              <CheckCircle className="mx-auto mb-3" size={32} />
              <p className="text-sm">Originality Verified</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SourceSidebar;
