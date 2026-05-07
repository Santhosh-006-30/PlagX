'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/build/pdf.mjs';
import mammoth from 'mammoth';
import { AlertCircle } from 'lucide-react';
import '@/styles/viewer.css';

// Set up PDF.js worker safely for Next.js
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
}

interface AISegment {
  text: string;
  start_index?: number;
  end_index?: number;
  start?: number;
  end?: number;
  page?: number;
  ai_score: number;
  similarity?: number;
  similarity_score?: number;
  highlight?: boolean;
  perplexity?: number;
  entropy?: number;
  match_type?: 'exact' | 'paraphrased';
  source_index?: number;
  source?: string;
  category?: string;
  classification?: string;
  citation_credit?: number;
  section?: string;
  novelty_score?: number;
}

interface DocumentViewerProps {
  fileUrl: string;
  fileType: string;
  segments: AISegment[];
  fullText: string;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({ fileUrl, fileType, segments, fullText }) => {
  const [docxHtml, setDocxHtml] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (fileType === 'docx' && fileUrl) {
      setIsLoading(true);
      setError(null);
      fetch(fileUrl)
        .then(res => {
          if (!res.ok) throw new Error(`Failed to fetch document: ${res.statusText}`);
          return res.arrayBuffer();
        })
        .then(buffer => {
          if (buffer.byteLength === 0) throw new Error("Document buffer is empty");
          return mammoth.convertToHtml({ arrayBuffer: buffer });
        })
        .then(result => {
          setDocxHtml(result.value);
          setIsLoading(false);
        })
        .catch(err => {
          console.error("DOCX Loading error:", err);
          setError(err.message || "Failed to parse document");
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, [fileUrl, fileType]);

  const renderHighlightedContent = () => {
    if (fileType === 'txt' || fileType === 'docx') {
      return (
        <div className="whitespace-pre-wrap font-sans text-lg p-8 leading-relaxed text-zinc-800 dark:text-zinc-200">
          {applyHighlightsToText(fullText, segments)}
        </div>
      );
    }

    if (fileType === 'pdf') {
      return <PDFRenderer fileUrl={fileUrl} segments={segments} />;
    }

    return <div>Unsupported file type</div>;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-20 bg-red-50 dark:bg-red-950/20 rounded-xl border border-red-100 dark:border-red-900/30">
        <AlertCircle className="text-red-600 mb-4" size={32} />
        <p className="text-red-800 dark:text-red-400 font-medium">{error}</p>
        <p className="text-red-600/60 dark:text-red-400/40 text-sm mt-2">Falling back to raw text view...</p>
        <div className="mt-6 w-full text-left">
           <pre className="whitespace-pre-wrap font-sans text-lg p-8 leading-relaxed opacity-60">
            {fullText}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-zinc-950 rounded-xl overflow-hidden shadow-sm border border-zinc-200 dark:border-zinc-800">
      {renderHighlightedContent()}
    </div>
  );
};

// --- Sub-components & Helpers ---

const PDFRenderer: React.FC<{ fileUrl: string; segments: AISegment[] }> = ({ fileUrl, segments }) => {
  const [numPages, setNumPages] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadingTask = pdfjs.getDocument(fileUrl);
    loadingTask.promise.then(pdf => {
      setNumPages(pdf.numPages);
    });
  }, [fileUrl]);

  return (
    <div className="pdf-viewer-container" ref={containerRef}>
      {Array.from({ length: numPages }, (_, i) => (
        <PDFPage key={i + 1} pageNum={i + 1} fileUrl={fileUrl} segments={segments} />
      ))}
    </div>
  );
};

const PDFPage: React.FC<{ pageNum: number; fileUrl: string; segments: AISegment[] }> = ({ pageNum, fileUrl, segments }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const textLayerRef = useRef<HTMLDivElement>(null);
  const [scale] = useState(1.5);

  useEffect(() => {
    const loadingTask = pdfjs.getDocument(fileUrl);
    loadingTask.promise.then(pdf => {
      pdf.getPage(pageNum).then(page => {
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
          canvasContext: context!,
          viewport: viewport
        };
        page.render(renderContext);

        // Render text layer
        page.getTextContent().then(textContent => {
          if (!textLayerRef.current) return;
          textLayerRef.current.innerHTML = '';
          
          // In modern PDF.js, we use the TextLayer class
          const textLayer = new pdfjs.TextLayer({
            textContentSource: textContent,
            container: textLayerRef.current,
            viewport
          });
          
          textLayer.render().then(() => {
            // Apply highlights after text layer is rendered
            setTimeout(() => applyPDFHighlights(textLayerRef.current!, segments, pageNum), 100);
          });
        });
      });
    });
  }, [pageNum, fileUrl, segments]);

  return (
    <div className="pdf-page-wrapper" style={{ width: 'fit-content' }}>
      <canvas ref={canvasRef} />
      <div ref={textLayerRef} className="pdf-overlay-layer textLayer" />
    </div>
  );
};

const applyHighlightsToText = (text: string, segments: AISegment[]) => {
  if (!text) return text;
  if (!segments || segments.length === 0) return text;

  // Sort segments by start position
  const sorted = [...segments].sort((a, b) => (a.start ?? a.start_index ?? 0) - (b.start ?? b.start_index ?? 0));
  
  const elements: (string | JSX.Element)[] = [];
  let cursor = 0;

  sorted.forEach((seg, idx) => {
    const start = seg.start ?? seg.start_index ?? 0;
    const end = seg.end ?? seg.end_index ?? 0;

    if (start < cursor) return; // Skip overlapping for simplicity in this view

    if (start > cursor) {
      elements.push(text.slice(cursor, start));
    }

    const type = seg.type || (seg.similarity_score && seg.similarity_score > 70 ? 'exact_plagiarism' : 'semantic_plagiarism');
    const colorClass = `highlight-${type.replace('_', '-')}`;

    elements.push(
      <span
        key={`hl-${idx}`}
        className={`${colorClass} highlight-wrapped px-0.5 rounded-sm`}
        title={seg.title || `${Math.round((seg.similarity_score || seg.ai_score || 0) * 100)}% Match`}
        onClick={() => console.log("Match Clicked:", seg)}
      >
        {text.slice(start, end)}
      </span>
    );
    cursor = end;
  });

  if (cursor < text.length) {
    elements.push(text.slice(cursor));
  }

  return elements;
};

const applyPDFHighlights = (container: HTMLElement, segments: AISegment[], pageNum: number) => {
  const pageSegments = segments.filter(s => s.page === pageNum);
  const textDivs = Array.from(container.querySelectorAll('span'));

  pageSegments.forEach(seg => {
    const start = seg.start ?? seg.start_index ?? 0;
    const end = seg.end ?? seg.end_index ?? 0;
    
    // PDF rendering logic relies on text content matching
    // Keeping existing text matching for PDF layer to maintain visual alignment
    const cleanSegText = seg.text.replace(/\s+/g, ' ').trim();
    if (cleanSegText.length < 5) return;

    let currentMatch = '';
    let matchedDivs: HTMLElement[] = [];

    for (const div of textDivs) {
      const divText = div.innerText.trim();
      if (!divText) continue;

      if (cleanSegText.includes(divText)) {
        matchedDivs.push(div);
        currentMatch += divText + ' ';
        
        if (currentMatch.trim().length >= cleanSegText.length * 0.8) {
          matchedDivs.forEach(m => {
            m.classList.add('highlight-plagiarism-med');
          });
          currentMatch = '';
          matchedDivs = [];
        }
      } else {
        currentMatch = '';
        matchedDivs = [];
      }
    }
  });
};

const injectHighlightsIntoHtml = (html: string, segments: AISegment[]) => {
  if (!html || !segments) return html;
  
  let processedHtml = html;
  const sorted = [...segments].sort((a, b) => (b.text?.length || 0) - (a.text?.length || 0));

  sorted.forEach(seg => {
    const attrs = getHighlightAttributes(seg);
    if (!attrs) return;

    // Normalize whitespace for matching
    const cleanText = (seg.text || '').replace(/\s+/g, ' ').trim();
    if (cleanText.length < 3) return;

    // Escape for regex, allow flexible whitespace between words
    const words = cleanText.split(' ').map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const flexPattern = words.join('\\s+');
    
    // Match text that's NOT inside an HTML tag
    try {
      const regex = new RegExp(`(${flexPattern})`, 'gi');
      const marker = attrs['data-source-index'] ? ` data-source-index="${attrs['data-source-index']}"` : '';
      const highlightSpan = `<span class="${attrs.class}" title="${attrs.title}"${marker}>$1</span>`;
      
      // Only replace in text nodes (simple heuristic: not already inside a tag attribute)
      processedHtml = processedHtml.replace(regex, (match, p1, offset) => {
        // Check we're not inside a tag by looking for unmatched < before this position
        const before = processedHtml.slice(Math.max(0, offset - 200), offset);
        const lastOpen = before.lastIndexOf('<');
        const lastClose = before.lastIndexOf('>');
        if (lastOpen > lastClose) return match; // Inside a tag, skip
        return highlightSpan.replace('$1', p1);
      });
    } catch (e) {
      console.warn('HIGHLIGHT REGEX ERROR:', cleanText.slice(0, 30), e);
    }
  });

  return processedHtml;
};

export default DocumentViewer;
