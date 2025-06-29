import React, { useState } from 'react';
import { Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { audioAPI } from '../../services/api';
import toast from 'react-hot-toast';

interface DownloadButtonProps {
  fileId: string;
  sessionId?: string;
  fileName?: string;
  isMastered?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'outline';
}

const DownloadButton: React.FC<DownloadButtonProps> = ({
  fileId,
  sessionId,
  fileName = 'audio-file',
  isMastered = false,
  className = '',
  size = 'md',
  variant = 'primary',
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const variantClasses = {
    primary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
    secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
    outline: 'border border-indigo-600 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900',
  };

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      setDownloadProgress(0);

      let response;
      if (isMastered && sessionId) {
        response = await audioAPI.downloadMasteredFile(fileId, sessionId);
      } else {
        response = await audioAPI.downloadFile(fileId);
      }

      // Create blob and download
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Determine file extension and name
      const contentType = response.headers['content-type'] || 'audio/wav';
      const extension = contentType.includes('mp3') ? '.mp3' : '.wav';
      const downloadFileName = isMastered 
        ? `${fileName}_mastered${extension}`
        : `${fileName}${extension}`;
      
      link.download = downloadFileName;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setDownloadProgress(100);
      toast.success(`${isMastered ? 'Mastered' : 'Original'} file downloaded successfully!`);
      
    } catch (error: any) {
      console.error('Download failed:', error);
      toast.error(error.response?.data?.detail || 'Download failed');
    } finally {
      setIsDownloading(false);
      setTimeout(() => setDownloadProgress(0), 2000);
    }
  };

  const getButtonContent = () => {
    if (isDownloading) {
      return (
        <>
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          {downloadProgress > 0 ? `${downloadProgress}%` : 'Downloading...'}
        </>
      );
    }

    if (downloadProgress === 100) {
      return (
        <>
          <CheckCircle className="h-4 w-4 mr-2" />
          Downloaded
        </>
      );
    }

    return (
      <>
        <Download className="h-4 w-4 mr-2" />
        Download {isMastered ? 'Mastered' : ''}
      </>
    );
  };

  return (
    <button
      onClick={handleDownload}
      disabled={isDownloading}
      className={`
        inline-flex items-center justify-center font-medium rounded-md
        transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500
        disabled:opacity-50 disabled:cursor-not-allowed
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${className}
      `}
    >
      {getButtonContent()}
    </button>
  );
};

export default DownloadButton;