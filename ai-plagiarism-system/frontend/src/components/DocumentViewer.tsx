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
  start_char: number;
  end_char: number;
  type: 'exact' | 'semantic' | 'ai' | 'citation';
  confidence: number;
  source_id?: string;
  color: string;
  page?: number;
}

interface DocumentViewerProps {
  fileUrl: string;
  fileType: string;
  segments: AISegment[];
  fullText: string;
  onSegmentClick?: (segment: AISegment) => void;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({ 
  fileUrl, 
  fileType, 
  segments, 
  fullText,
  onSegmentClick 
}) => {
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
        <pre className="whitespace-pre-wrap font-sans text-lg p-8 lg:p-12 leading-relaxed text-zinc-800 dark:text-zinc-200">
          {applyHighlightsToText(fullText, segments, onSegmentClick)}
        </pre>
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

const getHighlightClass = (similarity: number) => {
  if (similarity > 70) return 'highlight-plagiarism-high';
  if (similarity > 40) return 'highlight-plagiarism-med';
  return 'highlight-plagiarism-low';
};

const getAIHighlightClass = (score: number) => {
  if (score > 80) return 'highlight-ai-high';
  return 'highlight-ai-low';
};

const getHighlightAttributes = (seg: AISegment) => {
  const simScore = seg.similarity_score || seg.similarity || 0;
  const aiScore = seg.ai_score || 0;
  const isPlagiarism = simScore > 20;
  const isAI = aiScore > 20;
  
  // Debug
  if (simScore > 0 || aiScore > 0) {
    console.log('HIGHLIGHT CHECK:', { text: seg.text?.slice(0, 50), simScore, aiScore, isPlagiarism, isAI });
  }

  if (isPlagiarism) {
    const className = getHighlightClass(simScore);
    const sourceMarker = seg.source_index ? `[${seg.source_index}]` : '';
    return {
      class: className,
      'data-source-index': sourceMarker,
      title: `${Math.round(simScore)}% Similarity Match${seg.source_index ? ` (Source ${seg.source_index})` : ''}`
    };
  }
  
  if (isAI) {
    return {
      class: aiScore > 80 ? 'highlight-ai-high' : 'highlight-ai-low',
      title: `AI Probability: ${Math.round(aiScore)}%`
    };
  }
  
  // If segment was marked as highlight by backend, still show it
  if (seg.highlight) {
    return {
      class: 'highlight-ai-low',
      title: `AI: ${Math.round(aiScore)}% | Sim: ${Math.round(simScore)}%`
    };
  }

  return null;
};

const applyPDFHighlights = (container: HTMLElement, segments: AISegment[], pageNum: number) => {
  const pageSegments = segments.filter(s => s.page === pageNum);
  const textDivs = Array.from(container.querySelectorAll('span'));

  pageSegments.forEach(seg => {
    const attrs = getHighlightAttributes(seg);
    if (!attrs) return;

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
            m.classList.add(attrs.class);
            if (attrs['data-source-index']) {
              m.setAttribute('data-source-index', attrs['data-source-index']);
            }
            m.title = attrs.title;
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

const applyHighlightsToText = (
  text: string, 
  segments: AISegment[], 
  onSegmentClick?: (segment: AISegment) => void
) => {
  if (!text) return text;
  if (!segments || segments.length === 0) return text;

  // ALL index calculations happen on the ORIGINAL text — never on a normalized copy.
  const ranges: { start: number; end: number; segment: AISegment }[] = [];

  segments.forEach((seg) => {
    const bStart = seg.start_char;
    const bEnd = seg.end_char;

    if (bStart >= 0 && bEnd > bStart && bEnd <= text.length) {
      ranges.push({ start: bStart, end: bEnd, segment: seg });
      return;
    }

    // --- Strategy 2: Find the segment's text in the ORIGINAL text via indexOf ---
    // Try near the expected position first, then from the beginning.
    const searchFrom = Math.max(0, bStart - 100);
    let foundAt = text.indexOf(segText, searchFrom);
    if (foundAt === -1 && searchFrom > 0) {
      foundAt = text.indexOf(segText); // global fallback
    }

    if (foundAt >= 0) {
      ranges.push({ start: foundAt, end: foundAt + segText.length, attrs });
      console.log('HIGHLIGHT (indexOf):', foundAt, '-', foundAt + segText.length, segText.slice(0, 40));
      return;
    }

    // --- Strategy 3: Fuzzy search — normalize for matching, then map back ---
    // Collapse whitespace in both the segment and the original text for comparison only.
    const segNorm = segText.replace(/\s+/g, ' ').trim();
    if (segNorm.length < 3) return;

    // Walk through the original text looking for a fuzzy match.
    // We build a "normalized window" as we scan, tracking the original positions.
    let winStart = -1;   // original-text index where current window starts
    let winBuf = '';     // normalized content of the window
    let i = 0;

    while (i < text.length) {
      const ch = text[i];
      const isSpace = /\s/.test(ch);

      if (winStart === -1) {
        // Haven't started a window yet
        if (!isSpace) {
          winStart = i;
          winBuf = ch;
        }
        i++;
        continue;
      }

      // Append to window, collapsing whitespace
      if (isSpace) {
        if (!winBuf.endsWith(' ')) winBuf += ' ';
      } else {
        winBuf += ch;
      }

      // Check if the window ends with our target
      if (winBuf.length >= segNorm.length) {
        const tail = winBuf.slice(winBuf.length - segNorm.length);
        if (tail.toLowerCase() === segNorm.toLowerCase()) {
          // Match found! The end position in original text is i+1.
          // Walk backwards to find the start in original text.
          const matchEnd = i + 1;
          // Count how many original chars contribute to segNorm.length normalized chars
          let charsNeeded = segNorm.length;
          let j = i;
          let inSpace = false;
          while (j >= 0 && charsNeeded > 0) {
            const c = text[j];
            if (/\s/.test(c)) {
              if (!inSpace) { charsNeeded--; inSpace = true; }
            } else {
              charsNeeded--;
              inSpace = false;
            }
            if (charsNeeded > 0) j--;
          }
          const matchStart = j;

          if (matchStart >= 0) {
            ranges.push({ start: matchStart, end: matchEnd, attrs });
            console.log('HIGHLIGHT (fuzzy):', matchStart, '-', matchEnd, text.slice(matchStart, matchEnd).slice(0, 40));
          }
          // Move past this match to avoid duplicates
          winStart = -1;
          winBuf = '';
          i++;
          continue;
        }
      }

      // Trim window if it's getting too long (2x target to limit scan cost)
      if (winBuf.length > segNorm.length * 2) {
        const trim = winBuf.length - segNorm.length * 2;
        winBuf = winBuf.slice(trim);
      }

      i++;
    }

    // If none of the strategies worked
    if (!ranges.some(r => r.attrs === attrs)) {
      console.warn('HIGHLIGHT MISS:', segText.slice(0, 50));
    }
  });

  // Sort by start position, merge overlaps
  ranges.sort((a, b) => a.start - b.start);
  const merged: typeof ranges = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r.start < last.end) {
      last.end = Math.max(last.end, r.end); // extend
    } else {
      merged.push({ ...r });
    }
  }

  // Build React elements by walking the ORIGINAL text
  const elements: (string | JSX.Element)[] = [];
  let cursor = 0;

  merged.forEach((range, idx) => {
    if (range.start > cursor) {
      elements.push(text.slice(cursor, range.start));
    }
    elements.push(
      <span
        key={`hl-${idx}`}
        className={`highlight-${range.segment.type} cursor-pointer transition-all hover:brightness-95`}
        title={`${range.segment.type.toUpperCase()}: ${Math.round(range.segment.confidence * 100)}%`}
        onClick={() => onSegmentClick?.(range.segment)}
      >
        {text.slice(range.start, range.end)}
      </span>
    );
    cursor = range.end;
  });

  if (cursor < text.length) {
    elements.push(text.slice(cursor));
  }

  console.log(`HIGHLIGHT SUMMARY: ${merged.length} regions rendered from ${segments.length} segments`);
  return elements;
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
