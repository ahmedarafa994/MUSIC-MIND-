import { useState } from 'react';
import { Settings as SettingsIcon, User, CreditCard, Bell, Key, Save } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('profile');
  
  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'billing', name: 'Billing', icon: CreditCard },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'api', name: 'API Keys', icon: Key },
  ];
  
  const [profile, setProfile] = useState({
    name: 'John Doe',
    email: 'john@example.com',
    bio: 'Music producer and sound engineer',
  });
  
  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setProfile(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleSaveProfile = () => {
    // Simulate API call
    setTimeout(() => {
      toast.success('Profile updated successfully');
    }, 500);
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <SettingsIcon className="h-6 w-6 text-gray-600" />
          Settings
        </h1>
        <p className="text-gray-600 mt-1">
          Manage your account settings and preferences
        </p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center px-3 py-2 w-full rounded-md text-sm font-medium ${
                  activeTab === tab.id
                    ? 'bg-purple-100 text-purple-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <tab.icon
                  className={`mr-3 flex-shrink-0 h-6 w-6 ${
                    activeTab === tab.id ? 'text-purple-500' : 'text-gray-400'
                  }`}
                />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
        
        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm p-6 lg:col-span-3">
          {activeTab === 'profile' && (
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-6">Profile Settings</h2>
              
              <div className="space-y-6">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={profile.name}
                    onChange={handleProfileChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={profile.email}
                    onChange={handleProfileChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label htmlFor="bio" className="block text-sm font-medium text-gray-700 mb-1">
                    Bio
                  </label>
                  <textarea
                    id="bio"
                    name="bio"
                    rows={4}
                    value={profile.bio}
                    onChange={handleProfileChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <button
                    onClick={handleSaveProfile}
                    className="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-md transition-colors flex items-center space-x-2"
                  >
                    <Save className="h-4 w-4" />
                    <span>Save Changes</span>
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'billing' && (
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-6">Billing & Subscription</h2>
              
              <div className="bg-gray-50 p-4 rounded-lg mb-6">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Current Plan</p>
                    <p className="text-2xl font-bold text-purple-600">Free Tier</p>
                    <p className="text-sm text-gray-500 mt-1">10 credits remaining</p>
                  </div>
                  <button className="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                    Upgrade Plan
                  </button>
                </div>
              </div>
              
              <div className="space-y-6">
                <div>
                  <h3 className="text-md font-medium text-gray-900 mb-3">Available Plans</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="border rounded-lg p-4">
                      <p className="font-medium text-gray-900">Basic</p>
                      <p className="text-2xl font-bold text-gray-900 mt-2">$9.99<span className="text-sm font-normal text-gray-500">/month</span></p>
                      <ul className="mt-4 space-y-2 text-sm text-gray-600">
                        <li>100 credits/month</li>
                        <li>Standard quality</li>
                        <li>Email support</li>
                      </ul>
                    </div>
                    
                    <div className="border-2 border-purple-500 rounded-lg p-4 relative">
                      <div className="absolute top-0 right-0 bg-purple-500 text-white text-xs font-bold px-2 py-1 rounded-bl-lg">
                        POPULAR
                      </div>
                      <p className="font-medium text-gray-900">Pro</p>
                      <p className="text-2xl font-bold text-gray-900 mt-2">$19.99<span className="text-sm font-normal text-gray-500">/month</span></p>
                      <ul className="mt-4 space-y-2 text-sm text-gray-600">
                        <li>300 credits/month</li>
                        <li>High quality</li>
                        <li>Priority support</li>
                      </ul>
                    </div>
                    
                    <div className="border rounded-lg p-4">
                      <p className="font-medium text-gray-900">Enterprise</p>
                      <p className="text-2xl font-bold text-gray-900 mt-2">$49.99<span className="text-sm font-normal text-gray-500">/month</span></p>
                      <ul className="mt-4 space-y-2 text-sm text-gray-600">
                        <li>1000 credits/month</li>
                        <li>Maximum quality</li>
                        <li>24/7 support</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-md font-medium text-gray-900 mb-3">Payment Methods</h3>
                  
                  <div className="border rounded-lg p-4 flex justify-between items-center">
                    <div className="flex items-center">
                      <div className="bg-blue-100 p-2 rounded-md">
                        <CreditCard className="h-6 w-6 text-blue-600" />
                      </div>
                      <div className="ml-4">
                        <p className="font-medium text-gray-900">•••• •••• •••• 4242</p>
                        <p className="text-sm text-gray-500">Expires 12/25</p>
                      </div>
                    </div>
                    <div>
                      <button className="text-sm text-purple-600 hover:text-purple-700">
                        Edit
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'notifications' && (
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-6">Notification Settings</h2>
              
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Email Notifications</p>
                    <p className="text-sm text-gray-500">Receive updates about your account and processing</p>
                  </div>
                  <div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" defaultChecked />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                    </label>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Processing Notifications</p>
                    <p className="text-sm text-gray-500">Get notified when your audio processing is complete</p>
                  </div>
                  <div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" defaultChecked />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                    </label>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Marketing Emails</p>
                    <p className="text-sm text-gray-500">Receive updates about new features and promotions</p>
                  </div>
                  <div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'api' && (
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-6">API Keys</h2>
              
              <div className="space-y-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">
                    Use API keys to access the AI Music Studio API programmatically. 
                    Keep your API keys secure and never share them publicly.
                  </p>
                </div>
                
                <div className="border rounded-lg overflow-hidden">
                  <div className="px-4 py-3 bg-gray-50 border-b">
                    <p className="font-medium text-gray-900">Your API Keys</p>
                  </div>
                  
                  <div className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">Production Key</p>
                        <p className="text-sm text-gray-500 mt-1">Created on Nov 10, 2023</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                          mk_•••••••••••••••••••••••••
                        </span>
                        <button className="text-sm text-purple-600 hover:text-purple-700">
                          Reveal
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <button className="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                  Generate New API Key
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}