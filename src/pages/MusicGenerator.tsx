import { useState } from 'react';
import { Wand2, Music, Play, Pause, Download, Settings, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

// Mock data - would be replaced with actual API calls
const MUSIC_STYLES = [
  { id: 'pop', name: 'Pop', description: 'Catchy melodies and mainstream appeal' },
  { id: 'rock', name: 'Rock', description: 'Guitar-driven with strong rhythms' },
  { id: 'jazz', name: 'Jazz', description: 'Improvisation and complex harmonies' },
  { id: 'classical', name: 'Classical', description: 'Orchestral and traditional forms' },
  { id: 'electronic', name: 'Electronic', description: 'Synthesized sounds and beats' },
  { id: 'hip-hop', name: 'Hip Hop', description: 'Rhythmic beats and urban style' },
  { id: 'folk', name: 'Folk', description: 'Acoustic and traditional melodies' },
  { id: 'ambient', name: 'Ambient', description: 'Atmospheric and meditative' },
];

const DURATIONS = [
  { value: 30, label: '30 seconds', cost: 0.02 },
  { value: 60, label: '1 minute', cost: 0.05 },
  { value: 120, label: '2 minutes', cost: 0.08 },
  { value: 180, label: '3 minutes', cost: 0.12 },
  { value: 300, label: '5 minutes', cost: 0.20 },
];

const SAMPLE_PROMPTS = [
  "Upbeat jazz music with saxophone and piano for a coffee shop",
  "Epic orchestral music for a movie trailer with dramatic crescendos",
  "Relaxing ambient music with nature sounds for meditation",
  "Energetic electronic dance music with heavy bass drops",
  "Acoustic folk song with guitar and harmonica, storytelling style",
  "Classical piano piece in the style of Chopin, melancholic and beautiful",
];

export default function MusicGenerator() {
  const [prompt, setPrompt] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('pop');
  const [selectedDuration, setSelectedDuration] = useState(60);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedTracks, setGeneratedTracks] = useState([
    { 
      id: 'gen_123456', 
      title: 'Jazz piano with saxophone', 
      status: 'completed', 
      date: '2023-11-15',
      duration: 60,
      audioUrl: 'https://example.com/audio.mp3'
    },
    { 
      id: 'gen_123457', 
      title: 'Electronic dance music', 
      status: 'processing', 
      date: '2023-11-14',
      duration: 120,
      progress: 65
    }
  ]);
  
  const handleGenerate = () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }
    
    setIsGenerating(true);
    
    // Simulate API call
    setTimeout(() => {
      setGeneratedTracks(prev => [
        {
          id: `gen_${Math.random().toString(36).substr(2, 9)}`,
          title: prompt,
          status: 'processing',
          date: new Date().toISOString().split('T')[0],
          duration: selectedDuration,
          progress: 0
        },
        ...prev
      ]);
      
      setIsGenerating(false);
      toast.success('Music generation started!');
      
      // Simulate progress updates
      const interval = setInterval(() => {
        setGeneratedTracks(prev => {
          const updated = [...prev];
          const processingTrack = updated.find(t => t.status === 'processing');
          
          if (processingTrack) {
            if (!processingTrack.progress) processingTrack.progress = 0;
            processingTrack.progress += 10;
            
            if (processingTrack.progress >= 100) {
              processingTrack.status = 'completed';
              processingTrack.audioUrl = 'https://example.com/audio.mp3';
              clearInterval(interval);
              toast.success('Music generation completed!');
            }
          } else {
            clearInterval(interval);
          }
          
          return updated;
        });
      }, 1000);
    }, 1500);
  };
  
  const useSamplePrompt = (sample: string) => {
    setPrompt(sample);
  };
  
  const selectedDurationObj = DURATIONS.find(d => d.value === selectedDuration);
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Wand2 className="h-6 w-6" />
          AI Music Generator
        </h1>
        <p className="mt-1 opacity-90">
          Create original music from text descriptions using advanced AI
        </p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Generation Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Prompt Input */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Describe Your Music</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Music Description
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the music you want to create... (e.g., 'Upbeat jazz music with saxophone for a coffee shop atmosphere')"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  rows={4}
                  maxLength={500}
                />
                <p className="text-sm text-gray-500 mt-1">
                  {prompt.length}/500 characters
                </p>
              </div>
              
              {/* Sample Prompts */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Try these examples:
                </p>
                <div className="flex flex-wrap gap-2">
                  {SAMPLE_PROMPTS.slice(0, 3).map((sample, index) => (
                    <button
                      key={index}
                      onClick={() => useSamplePrompt(sample)}
                      className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-full transition-colors"
                    >
                      {sample.substring(0, 30)}...
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          
          {/* Style and Duration */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Style & Duration</h2>
            
            <div className="space-y-6">
              {/* Music Style */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Music Style
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {MUSIC_STYLES.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      className={`p-3 text-left border rounded-lg transition-colors ${
                        selectedStyle === style.id
                          ? 'border-purple-500 bg-purple-50 text-purple-700'
                          : 'border-gray-200 hover:border-purple-300'
                      }`}
                    >
                      <p className="font-medium text-sm">{style.name}</p>
                      <p className="text-xs text-gray-500 mt-1">{style.description}</p>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Duration
                </label>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {DURATIONS.map((duration) => (
                    <button
                      key={duration.value}
                      onClick={() => setSelectedDuration(duration.value)}
                      className={`p-3 text-center border rounded-lg transition-colors ${
                        selectedDuration === duration.value
                          ? 'border-purple-500 bg-purple-50 text-purple-700'
                          : 'border-gray-200 hover:border-purple-300'
                      }`}
                    >
                      <p className="font-medium text-sm">{duration.label}</p>
                      <p className="text-xs text-green-600 mt-1">
                        ${duration.cost.toFixed(2)}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            {/* Advanced Settings */}
            <div className="mt-6 border-t pt-4">
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
                        Temperature (0.8)
                      </label>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        defaultValue="0.8"
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500">Controls creativity vs consistency</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Guidance Scale (3.0)
                      </label>
                      <input
                        type="range"
                        min="1.0"
                        max="10.0"
                        step="0.5"
                        defaultValue="3.0"
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500">How closely to follow the prompt</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="useStructure"
                      defaultChecked={true}
                      className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                    />
                    <label htmlFor="useStructure" className="text-sm text-gray-700">
                      Use musical structure (intro, verse, chorus, etc.)
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Generation Summary & Controls */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Generation Summary</h2>
            
            <div className="space-y-4">
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="bg-purple-100 p-2 rounded-lg">
                    <Music className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 capitalize">{selectedStyle} Music</p>
                    <p className="text-sm text-gray-500">{selectedDurationObj?.label}</p>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-purple-100">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Estimated Cost:</span>
                    <span className="font-medium text-gray-900">${selectedDurationObj?.cost.toFixed(2)}</span>
                  </div>
                </div>
              </div>
              
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="h-5 w-5 animate-spin" />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="h-5 w-5" />
                    <span>Generate Music</span>
                  </>
                )}
              </button>
            </div>
          </div>
          
          {/* Recently Generated */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Recently Generated</h2>
            
            <div className="space-y-4">
              {generatedTracks.length > 0 ? (
                generatedTracks.map((track) => (
                  <div key={track.id} className="border rounded-lg p-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-gray-900">{track.title}</p>
                        <p className="text-xs text-gray-500">{track.date} • {track.duration}s</p>
                      </div>
                      <div>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          track.status === 'completed' 
                            ? 'bg-green-100 text-green-800'
                            : track.status === 'processing'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {track.status}
                        </span>
                      </div>
                    </div>
                    
                    {track.status === 'processing' && track.progress !== undefined && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-purple-600 h-2 rounded-full" 
                            style={{ width: `${track.progress}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{track.progress}% complete</p>
                      </div>
                    )}
                    
                    {track.status === 'completed' && track.audioUrl && (
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
                  <Music className="h-12 w-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">No generations yet</p>
                  <p className="text-sm text-gray-400">Start by generating some music!</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}