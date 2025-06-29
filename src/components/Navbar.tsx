import { Music, Bell, User, Menu } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function Navbar() {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  
  return (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex-shrink-0 flex items-center">
              <Music className="h-8 w-8 text-purple-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">AI Music Studio</span>
            </Link>
          </div>
          
          <div className="flex items-center">
            {/* Notifications */}
            <div className="relative ml-3">
              <button
                className="p-1 rounded-full text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                onClick={() => setShowNotifications(!showNotifications)}
              >
                <span className="sr-only">View notifications</span>
                <Bell className="h-6 w-6" />
              </button>
              
              {showNotifications && (
                <div className="origin-top-right absolute right-0 mt-2 w-80 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-700">Notifications</p>
                  </div>
                  <div className="max-h-60 overflow-y-auto">
                    <div className="px-4 py-2 hover:bg-gray-50">
                      <p className="text-sm font-medium text-gray-900">Music generation complete</p>
                      <p className="text-xs text-gray-500">Your jazz track is ready</p>
                    </div>
                    <div className="px-4 py-2 hover:bg-gray-50">
                      <p className="text-sm font-medium text-gray-900">Audio mastering complete</p>
                      <p className="text-xs text-gray-500">Your file has been processed</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* Profile dropdown */}
            <div className="relative ml-3">
              <div>
                <button
                  className="max-w-xs bg-white flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                >
                  <span className="sr-only">Open user menu</span>
                  <div className="h-8 w-8 rounded-full bg-purple-100 flex items-center justify-center">
                    <User className="h-5 w-5 text-purple-600" />
                  </div>
                </button>
              </div>
              
              {showUserMenu && (
                <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
                  <Link to="/settings" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    Settings
                  </Link>
                  <button className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}