import React, { useState, useRef } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Play, Pause, Download, Settings, Wand2, Clock, Music, Volume2, RotateCcw, Trash2 } from 'lucide-react';
import { apiClient } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

interface GenerationRequest {
  prompt: string;
  duration: number;
  model: string;
  parameters: {
    temperature: number;
    topK: number;
    guidance: number;
    seed?: number;
  };
}

interface GenerationResult {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  audioUrl?: string;
  metadata?: any;
  cost: number;
  executionTime: number;
  prompt: string;
  model: string;
  createdAt: string;
  progress?: number;
}

const AVAILABLE_MODELS = [
  { id: 'musicgen', name: 'MusicGen', description: 'Meta\'s music generation model', cost: 0.001, maxDuration: 300 },
  { id: 'stable_audio', name: 'Stable Audio', description: 'High-quality audio generation', cost: 0.01, maxDuration: 90 },
  { id: 'google_musiclm', name: 'MusicLM', description: 'Google\'s music language model', cost: 0.002, maxDuration: 300 },
  { id: 'beethoven_ai', name: 'Beethoven AI', description: 'Classical music generation', cost: 0.08, maxDuration: 480 },
  { id: 'mureka_ai', name: 'Mureka AI', description: 'Creative music generation', cost: 0.02, maxDuration: 240 },
];

const PROMPT_EXAMPLES = [
  "Upbeat jazz piano with saxophone, energetic and modern",
  "Relaxing ambient music with soft synthesizers and nature sounds",
  "Epic orchestral soundtrack with dramatic strings and brass",
  "Electronic dance music with heavy bass and energetic beats",
  "Acoustic guitar ballad, emotional and heartfelt",
  "Classical piano piece in the style of Chopin",
  "Lo-fi hip hop beats for studying, chill and atmospheric",
  "Rock anthem with electric guitars and powerful drums"
];

export default function MusicGenerator() {
  const { user } = useAuth();
  const audioRef = useRef<HTMLAudioElement>(null);
  
  const [prompt, setPrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState('musicgen');
  const [duration, setDuration] = useState(30);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [parameters, setParameters] = useState({
    temperature: 0.8,
    topK: 250,
    guidance: 7.5,
    seed: undefined as number | undefined,
  });
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);

  // Fetch generation history
  const { data: generationHistory = [], refetch } = useQuery({
    queryKey: ['generations'],
    queryFn: async () => {
      const response = await apiClient.get('/music/generations');
      return response.data;
    },
  });

  const generateMutation = useMutation({
    mutationFn: async (request: GenerationRequest) => {
      const response = await apiClient.post('/music/generate', request);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Music generation started!');
      refetch();
      pollGenerationStatus(data.id);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Generation failed');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (generationId: string) => {
      await apiClient.delete(`/music/generations/${generationId}`);
    },
    onSuccess: () => {
      toast.success('Generation deleted');
      refetch();
    },
    onError: () => {
      toast.error('Failed to delete generation');
    },
  });

  const pollGenerationStatus = async (generationId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/music/generations/${generationId}/status`);
        const result = response.data;
        
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(interval);
          refetch();
          if (result.status === 'completed') {
            toast.success('Music generation completed!');
          } else {
            toast.error('Music generation failed');
          }
        }
      } catch (error) {
        clearInterval(interval);
        console.error('Polling error:', error);
      }
    }, 2000);
  };

  const handleGenerate = () => {
    if (!prompt.trim()) {
      toast.error('Please enter a prompt');
      return;
    }

    if (user && user.creditsRemaining <= 0) {
      toast.error('Insufficient credits. Please upgrade your plan.');
      return;
    }

    const selectedModelData = AVAILABLE_MODELS.find(m => m.id === selectedModel);
    if (selectedModelData && duration > selectedModelData.maxDuration) {
      toast.error(`Duration exceeds maximum for ${selectedModelData.name} (${selectedModelData.maxDuration}s)`);
      return;
    }

    const request: GenerationRequest = {
      prompt: prompt.trim(),
      duration,
      model: selectedModel,
      parameters,
    };

    generateMutation.mutate(request);
  };

  const togglePlayback = (audioUrl: string, generationId: string) => {
    if (currentlyPlaying === generationId) {
      setCurrentlyPlaying(null);
      if (audioRef.current) {
        audioRef.current.pause();
      }
    } else {
      setCurrentlyPlaying(generationId);
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play();
      }
    }
  };

  const downloadAudio = async (audioUrl: string, filename: string) => {
    try {
      const response = await fetch(audioUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Download started');
    } catch (error) {
      toast.error('Download failed');
    }
  };

  const selectedModelData = AVAILABLE_MODELS.find(m => m.id === selectedModel);
  const estimatedCost = selectedModelData ? selectedModelData.cost * (duration / 30) : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Wand2 className="h-6 w-6 text-purple-600" />
              AI Music Generator
            </h1>
            <p className="text-gray-600 mt-1">
              Generate music from text prompts using advanced AI models
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Credits Remaining</p>
            <p className="text-2xl font-bold text-purple-600">{user?.creditsRemaining || 0}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Generation Form */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Generate Music</h2>
            
            <div className="space-y-4">
              {/* Prompt Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Music Prompt
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the music you want to generate..."
                  className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
                
                {/* Prompt Examples */}
                <div className="mt-2">
                  <p className="text-xs text-gray-500 mb-2">Try these examples:</p>
                  <div className="flex flex-wrap gap-1">
                    {PROMPT_EXAMPLES.slice(0, 4).map((example, index) => (
                      <button
                        key={index}
                        onClick={() => setPrompt(example)}
                        className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
                      >
                        {example.slice(0, 30)}...
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Model Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AI Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} - ${model.cost.toFixed(3)}/generation
                    </option>
                  ))}
                </select>
                {selectedModelData && (
                  <p className="text-xs text-gray-500 mt-1">
                    {selectedModelData.description} • Max duration: {selectedModelData.maxDuration}s
                  </p>
                )}
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Duration: {duration} seconds
                </label>
                <input
                  type="range"
                  min="10"
                  max={selectedModelData?.maxDuration || 300}
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>10s</span>
                  <span>{selectedModelData?.maxDuration || 300}s</span>
                </div>
              </div>

              {/* Advanced Parameters */}
              <div>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-sm text-purple-600 hover:text-purple-700"
                >
                  <Settings className="h-4 w-4" />
                  Advanced Parameters
                </button>
                
                {showAdvanced && (
                  <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Temperature: {parameters.temperature}
                      </label>
                      <input
                        type="range"
                        min="0.1"
                        max="2.0"
                        step="0.1"
                        value={parameters.temperature}
                        onChange={(e) => setParameters(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                        className="w-full"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Top K: {parameters.topK}
                      </label>
                      <input
                        type="range"
                        min="1"
                        max="500"
                        value={parameters.topK}
                        onChange={(e) => setParameters(prev => ({ ...prev, topK: parseInt(e.target.value) }))}
                        className="w-full"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Guidance Scale: {parameters.guidance}
                      </label>
                      <input
                        type="range"
                        min="1"
                        max="20"
                        step="0.5"
                        value={parameters.guidance}
                        onChange={(e) => setParameters(prev => ({ ...prev, guidance: parseFloat(e.target.value) }))}
                        className="w-full"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Seed (optional)
                      </label>
                      <input
                        type="number"
                        value={parameters.seed || ''}
                        onChange={(e) => setParameters(prev => ({ ...prev, seed: e.target.value ? parseInt(e.target.value) : undefined }))}
                        placeholder="Random seed for reproducible results"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
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

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending || !prompt.trim()}
                className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {generateMutation.isPending ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating...
                  </>
                ) : (
                  <>
                    <Music className="h-5 w-5" />
                    Generate Music
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Generation History */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Recent Generations</h2>
            
            {generationHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Music className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No generations yet</p>
                <p className="text-sm">Start by creating your first track!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {generationHistory.map((generation) => (
                  <div
                    key={generation.id}
                    className="p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          generation.status === 'completed' ? 'bg-green-500' :
                          generation.status === 'processing' ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`} />
                        <span className="text-sm font-medium capitalize">
                          {generation.status}
                        </span>
                      </div>
                      
                      {generation.status === 'processing' && (
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-gray-500">
                            {generation.progress ? `${Math.round(generation.progress)}%` : 'Processing...'}
                          </span>
                          <svg className="animate-spin h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        </div>
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {generation.prompt || 'Music generation'}
                    </p>
                    
                    {generation.status === 'completed' && generation.audioUrl && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => togglePlayback(generation.audioUrl!, generation.id)}
                          className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200"
                        >
                          {currentlyPlaying === generation.id ? (
                            <Pause className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </button>
                        
                        <button
                          onClick={() => downloadAudio(generation.audioUrl!, `generated-${generation.id}.wav`)}
                          className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        
                        <button
                          onClick={() => deleteMutation.mutate(generation.id)}
                          className="p-2 bg-red-50 text-red-500 rounded-lg hover:bg-red-100"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                        
                        <div className="flex-1 text-right">
                          <div className="text-xs text-gray-500">
                            <Clock className="h-3 w-3 inline mr-1" />
                            {generation.executionTime}s
                          </div>
                          <div className="text-xs text-gray-500">
                            ${generation.cost.toFixed(3)}
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {generation.status === 'failed' && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            setPrompt(generation.prompt || '');
                            setSelectedModel(generation.model || 'musicgen');
                          }}
                          className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200"
                          title="Retry with same settings"
                        >
                          <RotateCcw className="h-4 w-4" />
                        </button>
                        
                        <button
                          onClick={() => deleteMutation.mutate(generation.id)}
                          className="p-2 bg-red-50 text-red-500 rounded-lg hover:bg-red-100"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                        
                        <div className="flex-1">
                          <p className="text-sm text-red-600">
                            Generation failed. Please try again.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Hidden audio element for playback */}
      <audio ref={audioRef} />
    </div>
  );
}