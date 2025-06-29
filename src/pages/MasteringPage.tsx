import React, { useState, useEffect } from 'react';
import { Upload, Music, Sliders, Download, Play, Pause } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { audioAPI } from '../services/api';
import AudioPlayer from '../components/audio/AudioPlayer';
import MasteringControls from '../components/audio/MasteringControls';
import DownloadButton from '../components/audio/DownloadButton';
import toast from 'react-hot-toast';

interface AudioFile {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  duration?: number;
  status: string;
  created_at: string;
  download_url?: string;
  stream_url?: string;
}

const MasteringPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<AudioFile | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const { data: audioFiles, isLoading, refetch } = useQuery({
    queryKey: ['audioFiles'],
    queryFn: () => audioAPI.getFiles(),
  });

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('audio/')) {
      toast.error('Please select an audio file');
      return;
    }

    // Validate file size (50MB limit for demo)
    if (file.size > 50 * 1024 * 1024) {
      toast.error('File size must be less than 50MB');
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(0);

      await audioAPI.uploadFile(file, (progress) => {
        setUploadProgress(progress);
      });

      toast.success('File uploaded successfully!');
      refetch(); // Refresh the file list
      
    } catch (error: any) {
      console.error('Upload failed:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      // Reset the input
      event.target.value = '';
    }
  };

  const handleMasteringComplete = (sessionId: string) => {
    toast.success('Mastering completed! Your track is ready for download.');
    // Optionally refresh the file list or update the UI
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          AI Music Mastering
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Upload your tracks and let our AI master them to professional standards
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* File Upload & Library */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Upload Audio
            </h2>
            
            {/* Upload Area */}
            <div className="mb-6">
              <label className="block">
                <input
                  type="file"
                  accept="audio/*"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  className="hidden"
                />
                <div className={`
                  border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
                  ${isUploading 
                    ? 'border-gray-300 dark:border-gray-600 cursor-not-allowed' 
                    : 'border-gray-300 dark:border-gray-600 hover:border-indigo-400 dark:hover:border-indigo-500'
                  }
                `}>
                  <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {isUploading ? 'Uploading...' : 'Click to upload or drag and drop'}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                    WAV, MP3, FLAC up to 50MB
                  </p>
                  
                  {isUploading && (
                    <div className="mt-4">
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${uploadProgress}%` }}
                        />
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        {uploadProgress}% uploaded
                      </p>
                    </div>
                  )}
                </div>
              </label>
            </div>

            {/* File List */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                Your Files
              </h3>
              
              {isLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                    </div>
                  ))}
                </div>
              ) : audioFiles?.data?.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {audioFiles.data.map((file: AudioFile) => (
                    <div
                      key={file.id}
                      onClick={() => setSelectedFile(file)}
                      className={`
                        p-3 rounded-lg border cursor-pointer transition-colors
                        ${selectedFile?.id === file.id
                          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }
                      `}
                    >
                      <div className="flex items-center space-x-3">
                        <Music className="h-8 w-8 text-gray-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {file.original_filename}
                          </p>
                          <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                            <span>{formatFileSize(file.file_size)}</span>
                            <span>•</span>
                            <span>{formatDuration(file.duration)}</span>
                            <span>•</span>
                            <span className={`
                              px-2 py-1 rounded-full text-xs
                              ${file.status === 'completed' 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                : file.status === 'processing'
                                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                              }
                            `}>
                              {file.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Music className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No audio files yet. Upload your first track to get started.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-2">
          {selectedFile ? (
            <div className="space-y-6">
              {/* Audio Player */}
              <div>
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Now Playing: {selectedFile.original_filename}
                </h2>
                <AudioPlayer
                  src={selectedFile.stream_url || `/api/v1/audio/${selectedFile.id}/stream`}
                  title={selectedFile.original_filename}
                  artist="Your Track"
                />
              </div>

              {/* Download Original */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      Original Track
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Download your original uploaded file
                    </p>
                  </div>
                  <DownloadButton
                    fileId={selectedFile.id}
                    fileName={selectedFile.original_filename}
                    variant="outline"
                  />
                </div>
              </div>

              {/* Mastering Controls */}
              <MasteringControls
                fileId={selectedFile.id}
                fileName={selectedFile.original_filename}
                onMasteringComplete={handleMasteringComplete}
              />
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
              <div className="text-center">
                <Sliders className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Select a Track to Master
                </h3>
                <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                  Choose an audio file from your library or upload a new track to start the AI mastering process.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Info Section */}
      <div className="mt-12 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900 dark:to-purple-900 rounded-lg p-8">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Professional AI Mastering
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Our advanced AI analyzes your track and applies professional mastering techniques including:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="bg-white dark:bg-gray-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                <Sliders className="h-8 w-8 text-indigo-600" />
              </div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">EQ & Dynamics</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Intelligent frequency balancing and dynamic range optimization
              </p>
            </div>
            <div className="text-center">
              <div className="bg-white dark:bg-gray-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                <Music className="h-8 w-8 text-indigo-600" />
              </div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">Stereo Enhancement</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Spatial processing for wider, more immersive sound
              </p>
            </div>
            <div className="text-center">
              <div className="bg-white dark:bg-gray-800 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                <Download className="h-8 w-8 text-indigo-600" />
              </div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">Loudness Optimization</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Industry-standard loudness levels for streaming platforms
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MasteringPage;