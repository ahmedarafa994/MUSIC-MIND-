import { Link, useLocation } from 'react-router-dom';
import { Home, Music, Headphones, FileAudio, Settings } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Music Generator', href: '/generate', icon: Music },
  { name: 'Audio Mastering', href: '/mastering', icon: Headphones },
  { name: 'File Library', href: '/library', icon: FileAudio },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  
  return (
    <div className="hidden md:flex md:flex-col md:fixed md:w-64 md:inset-y-0 md:pt-16 bg-white border-r border-gray-200">
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
        <nav className="mt-5 flex-1 px-2 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`
                  group flex items-center px-2 py-2 text-sm font-medium rounded-md
                  ${isActive
                    ? 'bg-purple-100 text-purple-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }
                `}
              >
                <item.icon
                  className={`
                    mr-3 flex-shrink-0 h-6 w-6
                    ${isActive ? 'text-purple-500' : 'text-gray-400 group-hover:text-gray-500'}
                  `}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
      
      <div className="flex-shrink-0 p-4">
        <div className="bg-purple-50 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-purple-800">Pro Tip</h3>
          <p className="mt-1 text-sm text-purple-700">
            Try using detailed prompts for better music generation results.
          </p>
        </div>
      </div>
    </div>
  );
}