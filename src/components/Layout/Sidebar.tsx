import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  Upload,
  Music,
  Sliders,
  Sparkles,
  Library,
  User,
  Settings,
  BarChart3,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/app/dashboard', icon: Home },
  { name: 'Upload', href: '/app/upload', icon: Upload },
  { name: 'Library', href: '/app/library', icon: Library },
  { name: 'Generate Music', href: '/app/generate', icon: Sparkles },
  { name: 'Mastering', href: '/app/mastering', icon: Sliders },
  { name: 'Analytics', href: '/app/analytics', icon: BarChart3 },
];

const secondaryNavigation = [
  { name: 'Profile', href: '/app/profile', icon: User },
  { name: 'Settings', href: '/app/settings', icon: Settings },
];

const Sidebar: React.FC = () => {
  return (
    <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
      <div className="flex-1 flex flex-col min-h-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-4">
            <div className="flex items-center">
              <Music className="h-8 w-8 text-indigo-600" />
              <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
                AI Music Studio
              </span>
            </div>
          </div>
          
          <nav className="mt-8 flex-1 px-2 space-y-1">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-900 dark:text-indigo-100'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                  }`
                }
              >
                <item.icon
                  className="mr-3 flex-shrink-0 h-5 w-5"
                  aria-hidden="true"
                />
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>
        
        <div className="flex-shrink-0 flex border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="flex flex-col space-y-1 w-full">
            {secondaryNavigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-900 dark:text-indigo-100'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                  }`
                }
              >
                <item.icon
                  className="mr-3 flex-shrink-0 h-4 w-4"
                  aria-hidden="true"
                />
                {item.name}
              </NavLink>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;