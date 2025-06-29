import React, { useState } from 'react';
import { Sliders, Play, Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { audioAPI } from '../../services/api';
import DownloadButton from './DownloadButton';
import toast from 'react-hot-toast';

interface MasteringControlsProps {
  fileId: string;
  fileName?: string;
  onMasteringComplete?: (sessionId: string) => void;
  className?: string;
}

interface MasteringOptions {
  intensity: 'low' | 'medium' | 'high';
  style: 'warm' | 'balanced' | 'open' | 'punchy';
  loudness: number;
  stereo_width: 'narrow' | 'normal' | 'wide';
}

const MasteringControls: React.FC<MasteringControlsProps> = ({
  fileId,
  fileName = 'audio-file',
  onMasteringComplete,
  className = '',
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'completed' | 'failed'>('idle');
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [options, setOptions] = useState<MasteringOptions>({
    intensity: 'medium',
    style: 'balanced',
    loudness: -14,
    stereo_width: 'normal',
  });

  const handleStartMastering = async () => {
    try {
      setIsProcessing(true);
      setStatus('processing');
      setProgress(0);

      const response = await audioAPI.masterFile(fileId, options);
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);

      // Poll for status updates
      pollMasteringStatus(newSessionId);
      
      toast.success('Mastering started! This may take a few minutes.');
      
    } catch (error: any) {
      console.error('Failed to start mastering:', error);
      toast.error(error.response?.data?.detail || 'Failed to start mastering');
      setStatus('failed');
      setIsProcessing(false);
    }
  };

  const pollMasteringStatus = async (sessionId: string) => {
    try {
      const response = await audioAPI.getMasteringStatus(fileId, sessionId);
      const { status: currentStatus, progress: currentProgress } = response.data;
      
      setProgress(currentProgress || 0);
      
      if (currentStatus === 'completed') {
        setStatus('completed');
        setIsProcessing(false);
        onMasteringComplete?.(sessionId);
        toast.success('Mastering completed! You can now download your mastered track.');
      } else if (currentStatus === 'failed') {
        setStatus('failed');
        setIsProcessing(false);
        toast.error('Mastering failed. Please try again.');
      } else {
        // Continue polling
        setTimeout(() => pollMasteringStatus(sessionId), 2000);
      }
    } catch (error) {
      console.error('Failed to check mastering status:', error);
      setStatus('failed');
      setIsProcessing(false);
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'processing':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Sliders className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'processing':
        return `Processing... ${progress}%`;
      case 'completed':
        return 'Mastering completed!';
      case 'failed':
        return 'Mastering failed';
      default:
        return 'Ready to master';
    }
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              AI Mastering
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {getStatusText()}
            </p>
          </div>
        </div>
        
        {status === 'completed' && sessionId && (
          <DownloadButton
            fileId={fileId}
            sessionId={sessionId}
            fileName={fileName}
            isMastered={true}
            variant="primary"
          />
        )}
      </div>

      {/* Progress Bar */}
      {isProcessing && (
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
            <span>Processing</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Basic Controls */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Intensity
          </label>
          <select
            value={options.intensity}
            onChange={(e) => setOptions({ ...options, intensity: e.target.value as any })}
            disabled={isProcessing}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="low">Low - Subtle enhancement</option>
            <option value="medium">Medium - Balanced processing</option>
            <option value="high">High - Aggressive processing</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Style
          </label>
          <select
            value={options.style}
            onChange={(e) => setOptions({ ...options, style: e.target.value as any })}
            disabled={isProcessing}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="warm">Warm - Rich and smooth</option>
            <option value="balanced">Balanced - Natural sound</option>
            <option value="open">Open - Bright and airy</option>
            <option value="punchy">Punchy - Dynamic and powerful</option>
          </select>
        </div>
      </div>

      {/* Advanced Controls */}
      <div className="mb-6">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 font-medium"
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced Options
        </button>
        
        {showAdvanced && (
          <div className="mt-4 space-y-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Target Loudness (LUFS): {options.loudness}
              </label>
              <input
                type="range"
                min="-23"
                max="-6"
                value={options.loudness}
                onChange={(e) => setOptions({ ...options, loudness: parseInt(e.target.value) })}
                disabled={isProcessing}
                className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                <span>-23 (Quiet)</span>
                <span>-14 (Standard)</span>
                <span>-6 (Loud)</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Stereo Width
              </label>
              <select
                value={options.stereo_width}
                onChange={(e) => setOptions({ ...options, stereo_width: e.target.value as any })}
                disabled={isProcessing}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="narrow">Narrow - Focused center</option>
                <option value="normal">Normal - Natural width</option>
                <option value="wide">Wide - Enhanced stereo</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Action Button */}
      {status !== 'completed' && (
        <button
          onClick={handleStartMastering}
          disabled={isProcessing}
          className="w-full flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Processing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Start Mastering
            </>
          )}
        </button>
      )}

      {/* Info */}
      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900 rounded-lg">
        <p className="text-sm text-blue-700 dark:text-blue-300">
          <strong>Professional AI Mastering:</strong> Our AI will analyze your track and apply 
          professional mastering techniques including EQ, compression, limiting, and stereo enhancement 
          to make your music sound polished and radio-ready.
        </p>
      </div>
    </div>
  );
};

export default MasteringControls;