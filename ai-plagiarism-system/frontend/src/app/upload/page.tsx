'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import api, { docsApi, scanApi } from '@/lib/api';
import { Upload, FileText, CheckCircle, Loader2, AlertCircle } from 'lucide-react';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'analyzing' | 'done' | 'error'>('idle');
  const [error, setError] = useState('');
  const [testResult, setTestResult] = useState('');
  const router = useRouter();

  const testConnection = async () => {
    try {
      const { data } = await api.get('/');
      setTestResult('✅ Backend Connected: ' + JSON.stringify(data));
    } catch (err: any) {
      setTestResult('❌ Backend Connection Failed: ' + err.message);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      console.log('DEBUG: File dropped:', e.dataTransfer.files[0].name);
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setStatus('uploading');
    setError('');

    try {
      console.log('DEBUG: Starting upload for', file.name);
      const formData = new FormData();
      formData.append('file', file);
      
      const { data: doc } = await docsApi.upload(formData);
      console.log('DEBUG: Upload success, document ID:', doc.id);
      
      setStatus('analyzing');
      const { data: job } = await scanApi.analyze(doc.id);
      console.log('DEBUG: Analysis job created:', job.id);
      
      setStatus('done');
      router.push(`/report/${job.id}`);
    } catch (err: any) {
      console.error('DEBUG: Upload/Analysis error:', err);
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string' 
        ? detail 
        : Array.isArray(detail) 
          ? detail[0]?.msg 
          : 'Something went wrong during processing.';
      setError(message);
      setStatus('error');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black pt-24 pb-12">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4">
        <div className="card">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2">Upload Document</h1>
            <p className="text-zinc-600 dark:text-zinc-400">
              Submit your PDF, DOCX or TXT file for plagiarism analysis.
            </p>
            <div className="mt-4">
              <button 
                onClick={testConnection}
                className="text-xs text-blue-600 hover:underline"
              >
                Test connection to server
              </button>
              {testResult && <p className="text-xs mt-1 font-mono">{testResult}</p>}
            </div>
          </div>

          <div className="bg-zinc-100 dark:bg-zinc-900 rounded-2xl p-8 border border-zinc-200 dark:border-zinc-800">
            <h3 className="text-lg font-medium mb-4 text-center">Step 1: Choose your file</h3>
            <div className="flex flex-col items-center gap-4">
              <input
                type="file"
                id="file-upload"
                className="block w-full text-sm text-zinc-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-full file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100 cursor-pointer"
                onChange={(e) => {
                  console.log('DEBUG: File selected via standard input');
                  handleFileChange(e);
                }}
                accept=".pdf,.docx,.txt"
              />
              {file && (
                <p className="text-blue-600 font-bold text-center">
                  ✅ Selected: {file.name}
                </p>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl flex items-center gap-3">
              <AlertCircle size={20} />
              {error}
            </div>
          )}

          <div className="mt-8 flex flex-col items-center gap-4">
            {!file && (
              <p className="text-sm text-red-500 font-medium">Please select a file first</p>
            )}
            <button
              onClick={handleUpload}
              disabled={!file || isUploading}
              className={`btn-primary w-full flex items-center justify-center gap-2 py-3 text-lg ${(!file || isUploading) ? 'opacity-50 cursor-not-allowed bg-zinc-400' : 'bg-blue-600 hover:bg-blue-700'}`}
            >
              {isUploading ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle size={20} />
                  Start Analysis
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
