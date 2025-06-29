import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Play, Pause, Download, Settings, Wand2, Clock, Music, Volume2, Loader2 } from 'lucide-react';
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
}

const AVAILABLE_MODELS = [
  { id: 'musicgen', name: 'MusicGen', description: 'Meta\'s music generation model', cost: 0.001 },
  { id: 'stable_audio', name: 'Stable Audio', description: 'High-quality audio generation', cost: 0.01 },
  { id: 'google_musiclm', name: 'MusicLM', description: 'Google\'s music language model', cost: 0.002 },
  { id: 'beethoven_ai', name: 'Beethoven AI', description: 'Classical composition specialist', cost: 0.08 },
  { id: 'mureka_ai', name: 'Mureka AI', description: 'Creative music generation', cost: 0.02 },
];

const GENRE_OPTIONS = [
  'pop', 'rock', 'jazz', 'classical', 'electronic', 'hip-hop', 
  'country', 'blues', 'folk', 'ambient', 'reggae', 'funk'
];

const MOOD_OPTIONS = [
  'happy', 'sad', 'energetic', 'calm', 'mysterious', 'romantic',
  'aggressive', 'peaceful', 'dramatic', 'uplifting', 'melancholic', 'epic'
];

export default function MusicGenerator() {
  const { user } = useAuth();
  const [prompt, setPrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState('musicgen');
  const [duration, setDuration] = useState(30);
  const [genre, setGenre] = useState('');
  const [mood, setMood] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [parameters, setParameters] = useState({
    temperature: 0.8,
    topK: 250,
    guidance: 7.5,
    seed: undefined as number | undefined,
  });
  const [generationHistory, setGenerationHistory] = useState<GenerationResult[]>([]);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);

  const generateMutation = useMutation({
    mutationFn: async (request: any) => {
      const response = await apiClient.post('/music/generate', request);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Music generation started!');
      setGenerationHistory(prev => [data, ...prev]);
      // Poll for completion
      pollGenerationStatus(data.job_id);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Generation failed');
    },
  });

  const pollGenerationStatus = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/music/generation/${jobId}/status`);
        const result = response.data;
        
        setGenerationHistory(prev => 
          prev.map(item => 
            item.id === jobId ? { ...item, ...result } : item
          )
        );

        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(interval);
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

    const request = {
      prompt: prompt.trim(),
      duration,
      genre: genre || undefined,
      mood: mood || undefined,
      style: 'professional'
    };

    generateMutation.mutate(request);
  };

  const togglePlayback = (audioUrl: string, generationId: string) => {
    if (currentlyPlaying === generationId) {
      setCurrentlyPlaying(null);
      // Pause audio
    } else {
      setCurrentlyPlaying(generationId);
      // Play audio
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
            
            {/* Prompt Input */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Music Prompt
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the music you want to generate... (e.g., 'Upbeat jazz piano with saxophone, energetic and modern')"
                  className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Quick Options */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Genre (Optional)
                  </label>
                  <select
                    value={genre}
                    onChange={(e) => setGenre(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">Auto-detect</option>
                    {GENRE_OPTIONS.map(g => (
                      <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Mood (Optional)
                  </label>
                  <select
                    value={mood}
                    onChange={(e) => setMood(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">Auto-detect</option>
                    {MOOD_OPTIONS.map(m => (
                      <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Duration (seconds)
                  </label>
                  <input
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    min="10"
                    max="300"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>

              {/* AI Model Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AI Model
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {AVAILABLE_MODELS.map((model) => (
                    <div
                      key={model.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedModel === model.id
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                      onClick={() => setSelectedModel(model.id)}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-medium text-gray-900">{model.name}</h4>
                          <p className="text-sm text-gray-600">{model.description}</p>
                        </div>
                        <span className="text-xs text-gray-500">${model.cost}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

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
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
                    <div className="grid grid-cols-2 gap-4">
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
                          onChange={(e) => setParameters(prev => ({
                            ...prev,
                            temperature: Number(e.target.value)
                          }))}
                          className="w-full"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Guidance: {parameters.guidance}
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="20"
                          step="0.5"
                          value={parameters.guidance}
                          onChange={(e) => setParameters(prev => ({
                            ...prev,
                            guidance: Number(e.target.value)
                          }))}
                          className="w-full"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Seed (Optional)
                      </label>
                      <input
                        type="number"
                        value={parameters.seed || ''}
                        onChange={(e) => setParameters(prev => ({
                          ...prev,
                          seed: e.target.value ? Number(e.target.value) : undefined
                        }))}
                        placeholder="Random seed for reproducible results"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending || !prompt.trim()}
                className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Music className="h-4 w-4" />
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
                        <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {generation.metadata?.prompt || 'Music generation'}
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
                      <div className="text-sm text-red-600">
                        Generation failed. Please try again.
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}