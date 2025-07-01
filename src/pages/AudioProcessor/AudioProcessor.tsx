import React, { useState, useRef } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Upload, Play, Pause, Download, Settings, Headphones, Volume2, AudioWaveform as Waveform, Sliders, Zap, CheckCircle, AlertCircle, Clock, X, FileAudio, Loader2, RefreshCw, Trash2, Music } from 'lucide-react';
import { apiClient } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { useAudio } from '../../contexts/AudioContext';
import toast from 'react-hot-toast';

interface ProcessingTask {
  id: string;
  filename: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  originalUrl?: string;
  processedUrl?: string;
  processingType: string;
  cost: number;
  createdAt: string;
  metadata?: any;
}

const PROCESSING_OPTIONS = [
  {
    id: 'master',
    name: 'Professional Mastering',
    description: 'AI-powered mastering for professional sound quality',
    cost: 0.05,
    icon: Volume2,
    color: 'purple'
  },
  {
    id: 'enhance',
    name: 'Audio Enhancement',
    description: 'Remove noise, enhance clarity and dynamics',
    cost: 0.03,
    icon: Zap,
    color: 'blue'
  },
  {
    id: 'normalize',
    name: 'Loudness Normalization',
    description: 'Normalize audio levels for consistent playback',
    cost: 0.01,
    icon: Sliders,
    color: 'green'
  },
  {
    id: 'eq',
    name: 'AI EQ Optimization',
    description: 'Intelligent frequency balancing and EQ',
    cost: 0.02,
    icon: Waveform,
    color: 'orange'
  },
];

const ENHANCEMENT_LEVELS = ['light', 'moderate', 'heavy'];
const PROCESSING_STYLES = ['balanced', 'creative', 'professional'];
const TARGET_GENRES = ['jazz', 'rock', 'classical', 'electronic', 'pop', 'hip-hop'];

export default function AudioProcessor() {
  const { user } = useAuth();
  const { currentTrack, isPlaying, playTrack, pauseTrack } = useAudio();
  const audioRef = useRef<HTMLAudioElement>(null);
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedOperation, setSelectedOperation] = useState('enhance');
  const [processingStyle, setProcessingStyle] = useState('balanced');
  const [enhancementLevel, setEnhancementLevel] = useState('moderate');
  const [targetGenre, setTargetGenre] = useState('jazz');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advancedSettings, setAdvancedSettings] = useState({
    targetLUFS: -14,
    limitThreshold: -1,
    enhanceVocals: false,
    stereoWidth: 100,
    bassBoost: 0,
    trebleBoost: 0,
  });

  // Fetch processing history
  const { data: processingHistory = [], refetch } = useQuery({
    queryKey: ['processing-history'],
    queryFn: async () => {
      const response = await apiClient.get('/audio/processing-history');
      return response.data;
    },
  });

  const processMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await apiClient.post('/music/process-file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 100));
          console.log(`Upload Progress: ${percentCompleted}%`);
        },
      });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Audio processing started!');
      setSelectedFile(null);
      refetch();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Processing failed');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (taskId: string) => {
      await apiClient.delete(`/audio/processing/${taskId}`);
    },
    onSuccess: () => {
      toast.success('Processing task deleted');
      refetch();
    },
    onError: () => {
      toast.error('Failed to delete processing task');
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('audio/')) {
        toast.error('Please select an audio file');
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleProcess = () => {
    if (!selectedFile) {
      toast.error('Please select an audio file');
      return;
    }

    if (user && user.creditsRemaining <= 0) {
      toast.error('Insufficient credits. Please upgrade your plan.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('operation', selectedOperation);
    formData.append('style', processingStyle);
    formData.append('enhancement_level', enhancementLevel);
    
    if (selectedOperation === 'style_transfer') {
      formData.append('target_genre', targetGenre);
    }

    // Add advanced settings
    if (showAdvanced) {
      formData.append('settings', JSON.stringify(advancedSettings));
    }

    processMutation.mutate(formData);
  };

  const handlePlayPause = (audioUrl: string) => {
    if (currentTrack === audioUrl && isPlaying) {
      pauseTrack();
    } else {
      playTrack(audioUrl);
    }
  };

  const downloadResult = async (result: any) => {
    try {
      const audioUrl = result.results?.output_file_path;
      if (audioUrl) {
        const response = await fetch(audioUrl);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `processed_${Date.now()}.wav`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success('Download started');
      }
    } catch (error) {
      toast.error('Download failed');
    }
  };

  // Calculate estimated cost
  const selectedOption = PROCESSING_OPTIONS.find(option => option.id === selectedOperation);
  const estimatedCost = selectedOption ? selectedOption.cost : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Hidden audio element for playback */}
      <audio ref={audioRef} />
      
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Headphones className="h-6 w-6 text-purple-600" />
              Audio Processor
            </h1>
            <p className="text-gray-600 mt-1">
              Enhance and transform your audio with AI-powered processing
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Credits Remaining</p>
            <p className="text-2xl font-bold text-purple-600">{user?.creditsRemaining || 0}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Processing Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* File Upload */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Upload Audio File</h2>
            
            <div 
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                selectedFile ? 'border-purple-400 bg-purple-50' : 'border-gray-300 hover:border-purple-400'
              }`}
            >
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileSelect}
                className="hidden"
                id="audio-upload"
              />
              <label htmlFor="audio-upload" className="cursor-pointer">
                <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                {selectedFile ? (
                  <div>
                    <p className="text-lg font-medium text-gray-900 mb-1">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-gray-600">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Click to change
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-lg font-medium text-gray-900 mb-2">
                      Choose audio file
                    </p>
                    <p className="text-gray-600">
                      Drag and drop or click to browse
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      Supports MP3, WAV, FLAC, and other audio formats
                    </p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Processing Options */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Processing Options</h2>
            
            {/* Operation Selection */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Processing Operation
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {PROCESSING_OPTIONS.map((operation) => (
                    <div
                      key={operation.id}
                      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                        selectedOperation === operation.id
                          ? `border-${operation.color}-500 bg-${operation.color}-50`
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                      onClick={() => setSelectedOperation(operation.id)}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg bg-${operation.color}-100`}>
                          <operation.icon className={`h-5 w-5 text-${operation.color}-600`} />
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900">{operation.name}</h4>
                          <p className="text-sm text-gray-600">{operation.description}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Style Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Processing Style
                </label>
                <select
                  value={processingStyle}
                  onChange={(e) => setProcessingStyle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {PROCESSING_STYLES.map(style => (
                    <option key={style} value={style}>
                      {style.charAt(0).toUpperCase() + style.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Enhancement Level (for enhance operation) */}
              {selectedOperation === 'enhance' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Enhancement Level
                  </label>
                  <select
                    value={enhancementLevel}
                    onChange={(e) => setEnhancementLevel(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    {ENHANCEMENT_LEVELS.map(level => (
                      <option key={level} value={level}>
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Target Genre (for style transfer) */}
              {selectedOperation === 'style_transfer' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target Genre
                  </label>
                  <select
                    value={targetGenre}
                    onChange={(e) => setTargetGenre(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    {TARGET_GENRES.map(genre => (
                      <option key={genre} value={genre}>
                        {genre.charAt(0).toUpperCase() + genre.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Advanced Settings */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-sm text-purple-600 hover:text-purple-700"
                >
                  <Settings className="h-4 w-4" />
                  Advanced Settings
                </button>
                
                {showAdvanced && (
                  <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Target LUFS: {advancedSettings.targetLUFS} dB
                      </label>
                      <input
                        type="range"
                        min="-24"
                        max="-9"
                        step="1"
                        value={advancedSettings.targetLUFS}
                        onChange={(e) => setAdvancedSettings(prev => ({
                          ...prev,
                          targetLUFS: parseInt(e.target.value)
                        }))}
                        className="w-full"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Limiter Threshold: {advancedSettings.limitThreshold} dB
                      </label>
                      <input
                        type="range"
                        min="-6"
                        max="0"
                        step="0.5"
                        value={advancedSettings.limitThreshold}
                        onChange={(e) => setAdvancedSettings(prev => ({
                          ...prev,
                          limitThreshold: parseFloat(e.target.value)
                        }))}
                        className="w-full"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Stereo Width: {advancedSettings.stereoWidth}%
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="200"
                        step="5"
                        value={advancedSettings.stereoWidth}
                        onChange={(e) => setAdvancedSettings(prev => ({
                          ...prev,
                          stereoWidth: parseInt(e.target.value)
                        }))}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Bass Boost: {advancedSettings.bassBoost} dB
                        </label>
                        <input
                          type="range"
                          min="-6"
                          max="6"
                          step="0.5"
                          value={advancedSettings.bassBoost}
                          onChange={(e) => setAdvancedSettings(prev => ({
                            ...prev,
                            bassBoost: parseFloat(e.target.value)
                          }))}
                          className="w-full"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Treble Boost: {advancedSettings.trebleBoost} dB
                        </label>
                        <input
                          type="range"
                          min="-6"
                          max="6"
                          step="0.5"
                          value={advancedSettings.trebleBoost}
                          onChange={(e) => setAdvancedSettings(prev => ({
                            ...prev,
                            trebleBoost: parseFloat(e.target.value)
                          }))}
                          className="w-full"
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="enhance-vocals"
                        checked={advancedSettings.enhanceVocals}
                        onChange={(e) => setAdvancedSettings(prev => ({
                          ...prev,
                          enhanceVocals: e.target.checked
                        }))}
                        className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                      />
                      <label htmlFor="enhance-vocals" className="ml-2 block text-sm text-gray-700">
                        Enhance vocals
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Cost Estimate */}
              <div className="bg-blue-50 p-3 rounded-lg">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-blue-700">Estimated Cost:</span>
                  <span className="font-semibold text-blue-900">${estimatedCost.toFixed(3)}</span>
                </div>
              </div>

              {/* Process Button */}
              <button
                onClick={handleProcess}
                disabled={processMutation.isPending || !selectedFile}
                className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {processMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Headphones className="h-5 w-5" />
                    Process Audio
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Processing Results */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Processing Results</h2>
              <button
                onClick={() => refetch()}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-full"
                title="Refresh results"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
            
            {processingHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Headphones className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No processed files yet</p>
                <p className="text-sm">Upload and process your first audio file!</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {processingHistory.map((task: any) => (
                  <div
                    key={task.id}
                    className="p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {task.status === 'completed' ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : task.status === 'processing' || task.status === 'uploading' ? (
                          <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-sm font-medium capitalize">
                          {task.status}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-gray-500">
                          ${task.cost?.toFixed(3) || '0.000'}
                        </span>
                        <button
                          onClick={() => deleteMutation.mutate(task.id)}
                          className="p-1 text-gray-400 hover:text-red-500"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    
                    <div className="mb-2">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {task.filename || 'Audio file'}
                      </p>
                      <p className="text-xs text-gray-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(task.createdAt).toLocaleString()}
                      </p>
                    </div>
                    
                    {task.status === 'processing' && (
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                        <div 
                          className="bg-purple-600 h-2 rounded-full" 
                          style={{ width: `${task.progress || 0}%` }}
                        ></div>
                      </div>
                    )}
                    
                    {task.status === 'completed' && task.processedUrl && (
                      <div className="flex items-center gap-2 mt-3">
                        <button
                          onClick={() => handlePlayPause(task.processedUrl)}
                          className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200"
                          title={currentTrack === task.processedUrl && isPlaying ? "Pause" : "Play"}
                        >
                          {currentTrack === task.processedUrl && isPlaying ? (
                            <Pause className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </button>
                        
                        <button
                          onClick={() => downloadResult(task)}
                          className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        
                        {task.originalUrl && (
                          <button
                            onClick={() => handlePlayPause(task.originalUrl!)}
                            className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 ml-auto"
                            title="Play original"
                          >
                            <Music className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    )}
                    
                    {task.status === 'failed' && (
                      <div className="mt-2 text-sm text-red-600">
                        Processing failed. Please try again.
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Processing Info */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4">Processing Info</h3>
            
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Professional Mastering</h4>
                <p className="text-sm text-gray-600">
                  Our AI mastering chain applies professional-grade processing including EQ, compression, 
                  stereo enhancement, and limiting to make your tracks sound polished and ready for release.
                </p>
              </div>
              
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Audio Enhancement</h4>
                <p className="text-sm text-gray-600">
                  Intelligently removes noise, enhances clarity, and improves overall audio quality 
                  using advanced AI models trained on thousands of professional recordings.
                </p>
              </div>
              
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Supported Formats</h4>
                <p className="text-sm text-gray-600">
                  We support WAV, MP3, FLAC, AAC, and OGG formats. For best results, 
                  use uncompressed WAV files at 44.1kHz or higher.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}