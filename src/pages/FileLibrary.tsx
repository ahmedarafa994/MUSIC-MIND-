import { useState } from 'react';
import { FileAudio, Search, Filter, Play, Pause, Download, Trash2, Music, Headphones } from 'lucide-react';

// Mock data - would be replaced with actual API calls
const mockFiles = [
  { 
    id: 'file_123456', 
    filename: 'jazz_piano.mp3', 
    type: 'generation',
    size: '4.2 MB',
    duration: '1:30',
    date: '2023-11-15',
    url: 'https://example.com/audio.mp3'
  },
  { 
    id: 'file_123457', 
    filename: 'vocal_track_mastered.wav', 
    type: 'mastering',
    size: '8.7 MB',
    duration: '2:45',
    date: '2023-11-14',
    url: 'https://example.com/audio.mp3'
  },
  { 
    id: 'file_123458', 
    filename: 'electronic_beat.mp3', 
    type: 'generation',
    size: '3.1 MB',
    duration: '1:15',
    date: '2023-11-13',
    url: 'https://example.com/audio.mp3'
  },
  { 
    id: 'file_123459', 
    filename: 'guitar_recording_enhanced.wav', 
    type: 'mastering',
    size: '12.4 MB',
    duration: '3:20',
    date: '2023-11-12',
    url: 'https://example.com/audio.mp3'
  },
];

export default function FileLibrary() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  
  const filteredFiles = mockFiles.filter(file => {
    const matchesSearch = file.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType ? file.type === filterType : true;
    return matchesSearch && matchesFilter;
  });
  
  const togglePlayback = (fileId: string) => {
    if (currentlyPlaying === fileId) {
      setCurrentlyPlaying(null);
    } else {
      setCurrentlyPlaying(fileId);
    }
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <FileAudio className="h-6 w-6 text-blue-600" />
          File Library
        </h1>
        <p className="text-gray-600 mt-1">
          Manage your generated music and processed audio files
        </p>
      </div>
      
      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="relative w-full md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search files..."
              className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={() => setFilterType(null)}
              className={`px-3 py-1 rounded-md text-sm ${
                filterType === null
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterType('generation')}
              className={`px-3 py-1 rounded-md text-sm ${
                filterType === 'generation'
                  ? 'bg-purple-100 text-purple-800'
                  : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
              }`}
            >
              Generated
            </button>
            <button
              onClick={() => setFilterType('mastering')}
              className={`px-3 py-1 rounded-md text-sm ${
                filterType === 'mastering'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
              }`}
            >
              Processed
            </button>
          </div>
        </div>
      </div>
      
      {/* File List */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Your Files</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  File
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredFiles.length > 0 ? (
                filteredFiles.map((file) => (
                  <tr key={file.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          {file.type === 'generation' ? (
                            <div className="bg-purple-100 p-2 rounded-lg">
                              <Music className="h-5 w-5 text-purple-600" />
                            </div>
                          ) : (
                            <div className="bg-green-100 p-2 rounded-lg">
                              <Headphones className="h-5 w-5 text-green-600" />
                            </div>
                          )}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{file.filename}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        file.type === 'generation'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {file.type === 'generation' ? 'Generated' : 'Processed'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {file.size}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {file.duration}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {file.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <button 
                          onClick={() => togglePlayback(file.id)}
                          className="text-gray-400 hover:text-gray-500"
                        >
                          {currentlyPlaying === file.id ? (
                            <Pause className="h-5 w-5" />
                          ) : (
                            <Play className="h-5 w-5" />
                          )}
                        </button>
                        <button className="text-gray-400 hover:text-gray-500">
                          <Download className="h-5 w-5" />
                        </button>
                        <button className="text-gray-400 hover:text-red-500">
                          <Trash2 className="h-5 w-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center">
                    <FileAudio className="h-12 w-12 text-gray-300 mx-auto mb-2" />
                    <p className="text-gray-500">No files found</p>
                    <p className="text-sm text-gray-400">
                      {searchQuery ? 'Try a different search term' : 'Generate or process some audio files'}
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}