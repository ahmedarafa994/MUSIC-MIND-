import { BarChart3, Music, Headphones, Clock, ArrowUp } from 'lucide-react';
import { Link } from 'react-router-dom';

// Mock data - would come from API in real implementation
const stats = [
  { name: 'Total Generations', value: '24', icon: Music, change: '+12%', color: 'bg-purple-500' },
  { name: 'Audio Processed', value: '18', icon: Headphones, change: '+8%', color: 'bg-blue-500' },
  { name: 'Processing Time', value: '2.4h', icon: Clock, change: '-5%', color: 'bg-green-500' },
  { name: 'Storage Used', value: '128MB', icon: BarChart3, change: '+15%', color: 'bg-orange-500' },
];

const recentActivity = [
  { id: 1, type: 'generation', title: 'Jazz piano with saxophone', status: 'completed', date: '2023-11-15' },
  { id: 2, type: 'mastering', title: 'Vocal track enhancement', status: 'completed', date: '2023-11-14' },
  { id: 3, type: 'generation', title: 'Electronic dance music', status: 'processing', date: '2023-11-14' },
  { id: 4, type: 'mastering', title: 'Guitar recording mastering', status: 'failed', date: '2023-11-13' },
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold">Welcome to AI Music Studio</h1>
        <p className="mt-1 opacity-90">
          Create, process, and master music with the power of AI
        </p>
        <div className="mt-4 flex space-x-4">
          <Link
            to="/generate"
            className="bg-white bg-opacity-20 hover:bg-opacity-30 px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Generate Music
          </Link>
          <Link
            to="/mastering"
            className="bg-white bg-opacity-20 hover:bg-opacity-30 px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Master Audio
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
            <div className="mt-4">
              <span className="text-sm text-green-600 font-medium flex items-center">
                {stat.change} <ArrowUp className="h-3 w-3 ml-1" />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Recent Activity</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${
                    activity.type === 'generation' ? 'bg-purple-100' : 'bg-blue-100'
                  }`}>
                    {activity.type === 'generation' ? (
                      <Music className="h-4 w-4 text-purple-600" />
                    ) : (
                      <Headphones className="h-4 w-4 text-blue-600" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                    <p className="text-xs text-gray-500">{activity.date}</p>
                  </div>
                </div>
                <div>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    activity.status === 'completed' 
                      ? 'bg-green-100 text-green-800'
                      : activity.status === 'processing'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {activity.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}