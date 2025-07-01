import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Music, 
  Search, 
  Filter, 
  Play, 
  Pause, 
  Download, 
  MoreVertical,
  Upload,
  Grid,
  List
} from 'lucide-react';
import api from '../../services/api';
import { useAudio } from '../../contexts/AudioContext';
import LoadingSpinner from '../../components/UI/LoadingSpinner';

export default function AudioLibrary() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const { currentTrack, isPlaying, playTrack, pauseTrack } = useAudio();

  const { data: files, isLoading, refetch } = useQuery({
    queryKey: ['audio-files', searchQuery, selectedGenre],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (selectedGenre) params.append('genre', selectedGenre);
      
      const response = await api.get(`/files?${params.toString()}`);
      return response.data;
    }
  });

  const handlePlayPause = (audioUrl: string) => {
    if (currentTrack === audioUrl && isPlaying) {
      pauseTrack();
    } else {
      playTrack(audioUrl);
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const response = await api.get(`/files/${fileId}/download`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Music className="h-6 w-6 text-purple-600" />
            Audio Library
          </h1>
          <p className="text-gray-600 mt-1">
            Manage and organize your music collection
          </p>
        </div>
        
        <button className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center gap-2">
          <Upload className="h-4 w-4" />
          Upload Audio
        </button>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="h-5 w-5 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search your music..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>
          
          <select
            value={selectedGenre}
            onChange={(e) => setSelectedGenre(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Genres</option>
            <option value="pop">Pop</option>
            <option value="rock">Rock</option>
            <option value="jazz">Jazz</option>
            <option value="classical">Classical</option>
            <option value="electronic">Electronic</option>
          </select>
          
          <div className="flex border border-gray-300 rounded-lg">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-purple-100 text-purple-600' : 'text-gray-600'}`}
            >
              <Grid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-purple-100 text-purple-600' : 'text-gray-600'}`}
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Audio Files */}
      <div className="bg-white rounded-lg shadow-sm">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="large" />
          </div>
        ) : files?.length > 0 ? (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-6">
              {files.map((file: any) => (
                <div key={file.id} className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Music className="h-6 w-6 text-purple-600" />
                    </div>
                    <button className="text-gray-400 hover:text-gray-600">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  </div>
                  
                  <h3 className="font-medium text-gray-900 mb-1 truncate">
                    {file.title || file.original_filename}
                  </h3>
                  
                  <div className="text-sm text-gray-600 mb-3">
                    <div>{file.genre && <span className="capitalize">{file.genre}</span>}</div>
                    <div>{file.duration && formatDuration(file.duration)}</div>
                    <div>{formatFileSize(file.file_size)}</div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => handlePlayPause(`/api/v1/files/${file.id}/download`)}
                      className="flex-1 bg-purple-600 text-white py-2 px-3 rounded-lg hover:bg-purple-700 flex items-center justify-center gap-1"
                    >
                      {currentTrack === `/api/v1/files/${file.id}/download` && isPlaying ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </button>
                    
                    <button
                      onClick={() => handleDownload(file.id, file.original_filename)}
                      className="bg-gray-200 text-gray-700 py-2 px-3 rounded-lg hover:bg-gray-300"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {files.map((file: any) => (
                <div key={file.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Music className="h-5 w-5 text-purple-600" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 truncate">
                        {file.title || file.original_filename}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                        {file.genre && <span className="capitalize">{file.genre}</span>}
                        {file.duration && <span>{formatDuration(file.duration)}</span>}
                        <span>{formatFileSize(file.file_size)}</span>
                        <span>{new Date(file.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handlePlayPause(`/api/v1/files/${file.id}/download`)}
                        className="p-2 bg-purple-100 text-purple-600 rounded-lg hover:bg-purple-200"
                      >
                        {currentTrack === `/api/v1/files/${file.id}/download` && isPlaying ? (
                          <Pause className="h-4 w-4" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </button>
                      
                      <button
                        onClick={() => handleDownload(file.id, file.original_filename)}
                        className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      
                      <button className="p-2 text-gray-400 hover:text-gray-600">
                        <MoreVertical className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          <div className="text-center py-12">
            <Music className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No audio files found</h3>
            <p className="text-gray-600 mb-6">
              {searchQuery || selectedGenre 
                ? 'Try adjusting your search or filters'
                : 'Upload your first audio file to get started'
              }
            </p>
            <button className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
              Upload Audio
            </button>
          </div>
        )}
      </div>
    </div>
  );
}