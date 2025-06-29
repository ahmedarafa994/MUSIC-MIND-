import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';
import toast from 'react-hot-toast';

interface FileUploaderProps {
  onFileDrop: (file: File) => void;
}

export default function FileUploader({ onFileDrop }: FileUploaderProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      if (!file.type.startsWith('audio/')) {
        toast.error('Please select an audio file');
        return;
      }
      
      if (file.size > 100 * 1024 * 1024) { // 100MB limit
        toast.error('File size must be less than 100MB');
        return;
      }
      
      onFileDrop(file);
    }
  }, [onFileDrop]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']
    },
    maxFiles: 1
  });

  return (
    <div 
      {...getRootProps()} 
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-blue-400 bg-blue-50'
          : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
      }`}
    >
      <input {...getInputProps()} id="audio-upload" />
      <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
      {isDragActive ? (
        <p className="text-blue-600 font-medium">Drop the audio file here...</p>
      ) : (
        <div>
          <p className="text-gray-600 font-medium mb-2">
            Drag & drop an audio file here, or click to select
          </p>
          <p className="text-sm text-gray-500">
            Supports MP3, WAV, FLAC, AAC, OGG, M4A (max 100MB)
          </p>
        </div>
      )}
    </div>
  );
}