import React from 'react';
import { 
  Play, 
  Pause, 
  Download, 
  Trash2, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Clock, 
  Music 
} from 'lucide-react';

interface ProcessingResultProps {
  result: {
    id: string;
    filename: string;
    status: 'uploading' | 'processing' | 'completed' | 'failed';
    progress: number;
    originalUrl?: string;
    processedUrl?: string;
    processingType: string;
    cost: number;
    createdAt: string;
  };
  onPlay: (url: string, id: string) => void;
  onDownload: (url: string, filename: string) => void;
  onDelete: (id: string) => void;
  currentlyPlaying: string | null;
}

export default function ProcessingResult({ 
  result, 
  onPlay, 
  onDownload, 
  onDelete,
  currentlyPlaying
}: ProcessingResultProps) {
  return (
    <div className="p-4 border border-gray-200 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {result.status === 'completed' ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : result.status === 'processing' || result.status === 'uploading' ? (
            <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
          ) : (
            <AlertCircle className="h-4 w-4 text-red-500" />
          )}
          <span className="text-sm font-medium capitalize">
            {result.status}
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-500">
            ${result.cost?.toFixed(3) || '0.000'}
          </span>
          <button
            onClick={() => onDelete(result.id)}
            className="p-1 text-gray-400 hover:text-red-500"
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      <div className="mb-2">
        <p className="text-sm font-medium text-gray-900 truncate">
          {result.filename || 'Audio file'}
        </p>
        <p className="text-xs text-gray-500 flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(result.createdAt).toLocaleString()}
        </p>
      </div>
      
      {result.status === 'processing' && (
        <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
          <div 
            className="bg-blue-600 h-2 rounded-full" 
            style={{ width: `${result.progress || 0}%` }}
          ></div>
        </div>
      )}
      
      {result.status === 'completed' && result.processedUrl && (
        <div className="flex items-center gap-2 mt-3">
          <button
            onClick={() => onPlay(result.processedUrl!, result.id)}
            className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200"
            title={currentlyPlaying === result.id ? "Pause" : "Play"}
          >
            {currentlyPlaying === result.id ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </button>
          
          <button
            onClick={() => onDownload(result.processedUrl!, `processed_${result.filename}`)}
            className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
            title="Download"
          >
            <Download className="h-4 w-4" />
          </button>
          
          {result.originalUrl && (
            <button
              onClick={() => onPlay(result.originalUrl!, `original_${result.id}`)}
              className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200 ml-auto"
              title="Play original"
            >
              <Music className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
      
      {result.status === 'failed' && (
        <div className="mt-2 text-sm text-red-600">
          Processing failed. Please try again.
        </div>
      )}
    </div>
  );
}