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
  const [selectedProcessing, setSelectedProcessing] = useState('master'); // Could be 'landr' or 'matchering' directly
  const [showAdvanced, setShowAdvanced] = useState(false); // Re-evaluate use of this
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // New state for mastering services
  const [masteringServiceType, setMasteringServiceType] = useState<'landr' | 'matchering'>('landr');
  const [landrOptions, setLandrOptions] = useState({ style: 'balanced', intensity: 'medium', loudness: -14 }); // Example LANDR defaults
  const [matcheringReferenceFile, setMatcheringReferenceFile] = useState<File | null>(null);
  // Example: [{type: 'pcm16', filename_suffix: '_16bit.wav'}]
  const [matcheringOutputFormats, setMatcheringOutputFormats] = useState([{ type: 'pcm16', filename_suffix: '_16bit.wav' }]);


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
    
    setIsProcessing(true);
    toast.loading('Starting audio processing...');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('mastering_service_type', masteringServiceType);

    // Append service-specific options
    if (masteringServiceType === 'landr') {
      formData.append('landr_mastering_options_json', JSON.stringify(landrOptions));
    } else if (masteringServiceType === 'matchering') {
      if (matcheringReferenceFile) {
        formData.append('reference_file', matcheringReferenceFile);
      } else {
        toast.error('Matchering requires a reference file.');
        setIsProcessing(false);
        return;
      }
      // Add output formats if they are configurable by user in future
      formData.append('matchering_mastering_options_json', JSON.stringify({ output_formats: matcheringOutputFormats }));
    }

    // TODO: Add other general parameters like workflow_type, preset_name if needed by the backend endpoint for this specific call
    // For now, assuming they might default or are not strictly needed if mastering_service_type is specified.
    // formData.append('workflow_type', 'mastering_workflow'); // Example
    // formData.append('preset_name', selectedProcessing); // if 'master' corresponds to a preset


    // Replace with actual API endpoint
    fetch('/api/v1/processing/upload-and-process', {
      method: 'POST',
      body: formData,
      // Headers might be needed for auth (e.g., JWT token)
      // headers: { 'Authorization': `Bearer ${your_auth_token}` }
    })
    .then(response => {
      toast.dismiss(); // Dismiss loading toast
      if (!response.ok) {
        return response.json().then(err => { throw new Error(err.detail || 'Processing request failed') });
      }
      return response.json();
    })
    .then(data => {
      if (data.job_id) {
        toast.success(`Processing started! Job ID: ${data.job_id}`);
        // Add to local list of processed files (or refresh from server)
        setProcessedFiles(prev => [
          {
            id: data.job_id,
            filename: selectedFile.name,
            status: data.status || 'started', // API should return status
            date: new Date().toISOString().split('T')[0],
            processingType: masteringServiceType, // Use the service type
            originalUrl: URL.createObjectURL(selectedFile), // For local preview if needed
            progress: 0 // Initialize progress
          },
          ...prev
        ]);
        // TODO: Implement polling or WebSocket for job status updates instead of simulation
      } else {
        toast.error(data.message || 'Failed to start processing.');
      }
    })
    .catch(error => {
      toast.dismiss();
      toast.error(`Error: ${error.message}`);
    })
    .finally(() => {
      setIsProcessing(false);
      setSelectedFile(null); // Clear selected file after attempt
      setMatcheringReferenceFile(null); // Clear reference file
    });
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
            
            {/* Mastering Service Selector */}
            <div className="my-6">
              <h3 className="text-md font-semibold text-gray-800 mb-2">Mastering Service</h3>
              <div className="flex space-x-4">
                {(['landr', 'matchering'] as const).map((service) => (
                  <button
                    key={service}
                    onClick={() => setMasteringServiceType(service)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors
                      ${masteringServiceType === service
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                  >
                    {service.charAt(0).toUpperCase() + service.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Advanced Settings - now conditional based on service */}
            <div className="border-t pt-4">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
              >
                <Settings className="h-4 w-4" />
                <span>{masteringServiceType.charAt(0).toUpperCase() + masteringServiceType.slice(1)} Settings</span>
              </button>
              
              {showAdvanced && (
                <div className="mt-4 space-y-4 bg-gray-50 p-4 rounded-lg">
                  {/* LANDR Specific Settings */}
                  {masteringServiceType === 'landr' && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">LANDR Options</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label htmlFor="landrStyle" className="block text-sm font-medium text-gray-700 mb-1">Style</label>
                          <select
                            id="landrStyle"
                            value={landrOptions.style}
                            onChange={(e) => setLandrOptions(prev => ({ ...prev, style: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            {['balanced', 'warm', 'open', 'punchy'].map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                          </select>
                        </div>
                        <div>
                          <label htmlFor="landrIntensity" className="block text-sm font-medium text-gray-700 mb-1">Intensity</label>
                          <select
                            id="landrIntensity"
                            value={landrOptions.intensity}
                            onChange={(e) => setLandrOptions(prev => ({ ...prev, intensity: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            {['low', 'medium', 'high'].map(i => <option key={i} value={i}>{i.charAt(0).toUpperCase() + i.slice(1)}</option>)}
                          </select>
                        </div>
                        <div>
                          <label htmlFor="landrLoudness" className="block text-sm font-medium text-gray-700 mb-1">Target Loudness (LUFS)</label>
                          <input
                            type="number"
                            id="landrLoudness"
                            value={landrOptions.loudness}
                            onChange={(e) => setLandrOptions(prev => ({ ...prev, loudness: parseInt(e.target.value) }))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            min="-23" max="-6" step="1"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Matchering Specific Settings */}
                  {masteringServiceType === 'matchering' && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Matchering Options</h4>
                      <div>
                        <label htmlFor="matcheringReference" className="block text-sm font-medium text-gray-700 mb-1">
                          Reference Audio File
                        </label>
                        <input
                          type="file"
                          id="matcheringReference"
                          accept="audio/*"
                          onChange={(e) => setMatcheringReferenceFile(e.target.files ? e.target.files[0] : null)}
                          className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                        />
                        {matcheringReferenceFile && <p className="text-xs text-gray-500 mt-1">Selected: {matcheringReferenceFile.name}</p>}
                      </div>
                      {/* Placeholder for output format selection if needed */}
                       <div className="mt-2">
                         <p className="text-xs text-gray-600">Output will be 16-bit WAV by default. Advanced format selection can be added here.</p>
                       </div>
                    </div>
                  )}
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