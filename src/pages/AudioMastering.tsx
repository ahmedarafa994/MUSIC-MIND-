import { useState } from 'react';
import { Headphones, Upload, Play, Pause, Download, Settings, Volume2, Sliders, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

// Mock data - would be replaced with actual API calls
const PROCESSING_OPTIONS = [
  {
    id: 'master',
    name: 'Professional Mastering',
    description: 'AI-powered mastering for professional sound quality',
    cost: 0.05,
    icon: Volume2,
    color: 'bg-purple-500',
  },
  {
    id: 'enhance',
    name: 'Audio Enhancement',
    description: 'Remove noise, enhance clarity and dynamics',
    cost: 0.03,
    icon: Zap,
    color: 'bg-blue-500',
  },
  {
    id: 'normalize',
    name: 'Loudness Normalization',
    description: 'Normalize audio levels for consistent playback',
    cost: 0.01,
    icon: Sliders,
    color: 'bg-green-500',
  }
];

export default function AudioMastering() {
  const [selectedProcessing, setSelectedProcessing] = useState('master');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const [processedFiles, setProcessedFiles] = useState([
    { 
      id: 'proc_123456', 
      filename: 'vocal_track.mp3', 
      status: 'completed', 
      date: '2023-11-15',
      processingType: 'master',
      originalUrl: 'https://example.com/original.mp3',
      processedUrl: 'https://example.com/processed.mp3'
    },
    { 
      id: 'proc_123457', 
      filename: 'guitar_recording.wav', 
      status: 'processing', 
      date: '2023-11-14',
      processingType: 'enhance',
      originalUrl: 'https://example.com/original.mp3',
      progress: 45
    }
  ]);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      toast.success(`File selected: ${files[0].name}`);
    }
  };
  
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      toast.success(`File selected: ${files[0].name}`);
    }
  };
  
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };
  
  const handleProcess = () => {
    if (!selectedFile) {
      toast.error('Please select a file first');
      return;
    }
    
    setIsProcessing(true);
    
    // Simulate API call
    setTimeout(() => {
      setProcessedFiles(prev => [
        {
          id: `proc_${Math.random().toString(36).substr(2, 9)}`,
          filename: selectedFile.name,
          status: 'processing',
          date: new Date().toISOString().split('T')[0],
          processingType: selectedProcessing,
          originalUrl: 'https://example.com/original.mp3',
          progress: 0
        },
        ...prev
      ]);
      
      setIsProcessing(false);
      setSelectedFile(null);
      toast.success('Audio processing started!');
      
      // Simulate progress updates
      const interval = setInterval(() => {
        setProcessedFiles(prev => {
          const updated = [...prev];
          const processingFile = updated.find(f => f.status === 'processing');
          
          if (processingFile) {
            if (!processingFile.progress) processingFile.progress = 0;
            processingFile.progress += 10;
            
            if (processingFile.progress >= 100) {
              processingFile.status = 'completed';
              processingFile.processedUrl = 'https://example.com/processed.mp3';
              clearInterval(interval);
              toast.success('Audio processing completed!');
            }
          } else {
            clearInterval(interval);
          }
          
          return updated;
        });
      }, 1000);
    }, 1500);
  };
  
  const selectedOption = PROCESSING_OPTIONS.find(opt => opt.id === selectedProcessing);
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Headphones className="h-6 w-6" />
          AI Audio Mastering
        </h1>
        <p className="mt-1 opacity-90">
          Enhance and master your audio files with AI-powered processing
        </p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload and Processing Options */}
        <div className="lg:col-span-2 space-y-6">
          {/* File Upload */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Upload Audio File</h2>
            
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition-colors cursor-pointer"
            >
              <input
                type="file"
                id="file-upload"
                className="hidden"
                accept="audio/*"
                onChange={handleFileChange}
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-700 font-medium mb-2">
                  {selectedFile ? selectedFile.name : 'Drag & drop your audio file here, or click to browse'}
                </p>
                <p className="text-sm text-gray-500">
                  Supports MP3, WAV, FLAC, AAC, OGG (max 100MB)
                </p>
              </label>
            </div>
          </div>
          
          {/* Processing Options */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Processing Options</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {PROCESSING_OPTIONS.map((option) => (
                <div
                  key={option.id}
                  onClick={() => setSelectedProcessing(option.id)}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedProcessing === option.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className={`${option.color} p-2 rounded-lg`}>
                      <option.icon className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{option.name}</h3>
                      <p className="text-xs text-gray-500 mt-1">{option.description}</p>
                      <p className="text-xs font-medium text-green-600 mt-2">
                        ${option.cost.toFixed(2)}/minute
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Advanced Settings */}
            <div className="border-t pt-4">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
              >
                <Settings className="h-4 w-4" />
                <span>Advanced Settings</span>
              </button>
              
              {showAdvanced && (
                <div className="mt-4 space-y-4 bg-gray-50 p-4 rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Target LUFS
                      </label>
                      <input
                        type="number"
                        defaultValue={-14}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="-30"
                        max="0"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Limit Threshold (dB)
                      </label>
                      <input
                        type="number"
                        defaultValue={-1}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        min="-10"
                        max="0"
                        step="0.1"
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="enhanceVocals"
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="enhanceVocals" className="text-sm text-gray-700">
                      Enhance Vocals
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Processing Summary */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Processing Summary</h2>
            
            {selectedOption && (
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <div className={`${selectedOption.color} p-2 rounded-lg`}>
                    <selectedOption.icon className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{selectedOption.name}</p>
                    <p className="text-sm text-gray-500">${selectedOption.cost.toFixed(2)}/min</p>
                  </div>
                </div>
                
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-600">
                    Estimated cost for 3-minute track: 
                    <span className="font-medium text-gray-900 ml-1">
                      ${(selectedOption.cost * 3).toFixed(2)}
                    </span>
                  </p>
                </div>
                
                <button
                  onClick={handleProcess}
                  disabled={isProcessing || !selectedFile}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
                >
                  {isProcessing ? (
                    <>
                      <Upload className="h-5 w-5 animate-pulse" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <Headphones className="h-5 w-5" />
                      <span>Process Audio</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
          
          {/* Processing History */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Recent Processing</h2>
            
            <div className="space-y-4">
              {processedFiles.length > 0 ? (
                processedFiles.slice(0, 3).map((file) => (
                  <div key={file.id} className="border rounded-lg p-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-gray-900">{file.filename}</p>
                        <p className="text-xs text-gray-500">{file.date} • {file.processingType}</p>
                      </div>
                      <div>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          file.status === 'completed' 
                            ? 'bg-green-100 text-green-800'
                            : file.status === 'processing'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {file.status}
                        </span>
                      </div>
                    </div>
                    
                    {file.status === 'processing' && file.progress !== undefined && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${file.progress}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{file.progress}% complete</p>
                      </div>
                    )}
                    
                    {file.status === 'completed' && file.processedUrl && (
                      <div className="mt-2 flex space-x-2">
                        <button className="p-1 bg-gray-100 rounded-full hover:bg-gray-200">
                          <Play className="h-4 w-4 text-gray-700" />
                        </button>
                        <button className="p-1 bg-gray-100 rounded-full hover:bg-gray-200">
                          <Download className="h-4 w-4 text-gray-700" />
                        </button>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-6">
                  <Headphones className="h-12 w-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">No processed files yet</p>
                  <p className="text-sm text-gray-400">Upload an audio file to get started</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}