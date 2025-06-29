import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Music, 
  Wand2, 
  TrendingUp, 
  Clock, 
  DollarSign, 
  Headphones,
  Play,
  Download
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { apiClient } from '../../services/api';
import LoadingSpinner from '../../components/UI/LoadingSpinner';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const { user } = useAuth();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['user-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/users/me/stats');
      return response.data;
    }
  });

  const { data: recentGenerations, isLoading: generationsLoading } = useQuery({
    queryKey: ['recent-generations'],
    queryFn: async () => {
      const response = await apiClient.get('/files?limit=5&sort_by=created_at');
      return response.data;
    }
  });

  const { data: agentStatus } = useQuery({
    queryKey: ['agent-status'],
    queryFn: async () => {
      const response = await apiClient.get('/music/agent/status');
      return response.data;
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold mb-2">
          Welcome back, {user?.firstName}! 🎵
        </h1>
        <p className="text-purple-100">
          Ready to create some amazing music? Your AI studio is ready to go.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Music className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Tracks</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.total_files || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Clock className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Processing Time</p>
              <p className="text-2xl font-bold text-gray-900">
                {Math.round((stats?.total_processing_time || 0) / 60)}m
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <DollarSign className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Credits Used</p>
              <p className="text-2xl font-bold text-gray-900">
                {(stats?.api_calls_this_month || 0)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-orange-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Success Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {agentStatus ? `${agentStatus.availability_percentage}%` : '---'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link to="/generate" className="w-full flex items-center gap-3 p-4 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors">
              <Wand2 className="h-5 w-5 text-purple-600" />
              <div className="text-left">
                <div className="font-medium text-gray-900">Generate New Music</div>
                <div className="text-sm text-gray-600">Create music from text prompts</div>
              </div>
            </Link>

            <Link to="/process" className="w-full flex items-center gap-3 p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors">
              <Headphones className="h-5 w-5 text-blue-600" />
              <div className="text-left">
                <div className="font-medium text-gray-900">Process Audio</div>
                <div className="text-sm text-gray-600">Enhance existing audio files</div>
              </div>
            </Link>

            <Link to="/library" className="w-full flex items-center gap-3 p-4 bg-green-50 hover:bg-green-100 rounded-lg transition-colors">
              <Music className="h-5 w-5 text-green-600" />
              <div className="text-left">
                <div className="font-medium text-gray-900">Browse Library</div>
                <div className="text-sm text-gray-600">View your music collection</div>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent Generations */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Generations</h2>
          
          {generationsLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : recentGenerations?.length > 0 ? (
            <div className="space-y-3">
              {recentGenerations.slice(0, 5).map((track: any) => (
                <div key={track.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="p-2 bg-purple-100 rounded">
                    <Music className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">
                      {track.title || track.filename}
                    </div>
                    <div className="text-sm text-gray-600">
                      {new Date(track.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <Play className="h-4 w-4" />
                    </button>
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Music className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No generations yet</p>
              <p className="text-sm">Start creating your first track!</p>
            </div>
          )}
        </div>
      </div>

      {/* AI Agent Status */}
      {agentStatus && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Agent Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                agentStatus.status === 'operational' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-yellow-100 text-yellow-800'
              }`}>
                {agentStatus.status}
              </div>
              <p className="text-sm text-gray-600 mt-1">Overall Status</p>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {agentStatus.available_services}/{agentStatus.total_services}
              </div>
              <p className="text-sm text-gray-600">Services Online</p>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {agentStatus.availability_percentage}%
              </div>
              <p className="text-sm text-gray-600">Availability</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}