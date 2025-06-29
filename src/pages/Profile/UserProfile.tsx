import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { User, Mail, Phone, MapPin, Calendar, Edit2, Save, X } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { apiClient } from '../../services/api';
import toast from 'react-hot-toast';
import LoadingSpinner from '../../components/UI/LoadingSpinner';

export default function UserProfile() {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    phone: '',
    country: '',
    bio: ''
  });

  const { data: profile, isLoading } = useQuery({
    queryKey: ['user-profile'],
    queryFn: async () => {
      const response = await apiClient.get('/users/me');
      return response.data;
    },
    onSuccess: (data) => {
      setFormData({
        firstName: data.firstName || '',
        lastName: data.lastName || '',
        email: data.email || '',
        phone: data.phone || '',
        country: data.country || '',
        bio: data.bio || ''
      });
    }
  });

  const updateMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.put('/users/me', data);
      return response.data;
    },
    onSuccess: (data) => {
      updateUser(data);
      setIsEditing(false);
      toast.success('Profile updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Update failed');
    }
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSave = () => {
    updateMutation.mutate(formData);
  };

  const handleCancel = () => {
    setFormData({
      firstName: profile?.firstName || '',
      lastName: profile?.lastName || '',
      email: profile?.email || '',
      phone: profile?.phone || '',
      country: profile?.country || '',
      bio: profile?.bio || ''
    });
    setIsEditing(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <User className="h-8 w-8 text-purple-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {profile?.firstName} {profile?.lastName}
              </h1>
              <p className="text-gray-600">{profile?.email}</p>
              <div className="flex items-center gap-4 mt-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  profile?.subscriptionTier === 'premium' 
                    ? 'bg-purple-100 text-purple-800'
                    : profile?.subscriptionTier === 'pro'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {profile?.subscriptionTier?.toUpperCase() || 'FREE'} Plan
                </span>
                {profile?.isVerified && (
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                    Verified
                  </span>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <button
                  onClick={handleSave}
                  disabled={updateMutation.isPending}
                  className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center gap-2"
                >
                  {updateMutation.isPending ? (
                    <LoadingSpinner size="small" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 flex items-center gap-2"
                >
                  <X className="h-4 w-4" />
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center gap-2"
              >
                <Edit2 className="h-4 w-4" />
                Edit Profile
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Information */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Profile Information</h2>
          
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  First Name
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                ) : (
                  <p className="text-gray-900">{profile?.firstName || 'Not provided'}</p>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Last Name
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                ) : (
                  <p className="text-gray-900">{profile?.lastName || 'Not provided'}</p>
                )}
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-gray-400" />
                <p className="text-gray-900">{profile?.email}</p>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number
              </label>
              {isEditing ? (
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Enter your phone number"
                />
              ) : (
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-gray-400" />
                  <p className="text-gray-900">{profile?.phone || 'Not provided'}</p>
                </div>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Country
              </label>
              {isEditing ? (
                <input
                  type="text"
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Enter your country"
                />
              ) : (
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-400" />
                  <p className="text-gray-900">{profile?.country || 'Not provided'}</p>
                </div>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bio
              </label>
              {isEditing ? (
                <textarea
                  name="bio"
                  value={formData.bio}
                  onChange={handleChange}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Tell us about yourself..."
                />
              ) : (
                <p className="text-gray-900">{profile?.bio || 'No bio provided'}</p>
              )}
            </div>
          </div>
        </div>

        {/* Account Stats */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Account Stats</h3>
            
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-600">Credits Remaining</span>
                <span className="font-semibold text-purple-600">
                  {profile?.creditsRemaining || 0}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Member Since</span>
                <span className="text-gray-900">
                  {profile?.createdAt ? new Date(profile.createdAt).toLocaleDateString() : 'N/A'}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Last Login</span>
                <span className="text-gray-900">
                  {profile?.lastLogin ? new Date(profile.lastLogin).toLocaleDateString() : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Subscription</h3>
            
            <div className="text-center">
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium mb-3 ${
                profile?.subscriptionTier === 'premium' 
                  ? 'bg-purple-100 text-purple-800'
                  : profile?.subscriptionTier === 'pro'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {profile?.subscriptionTier?.toUpperCase() || 'FREE'} Plan
              </div>
              
              <p className="text-gray-600 text-sm mb-4">
                {profile?.subscriptionTier === 'free' 
                  ? 'Upgrade to unlock more features'
                  : 'Thank you for being a premium member!'
                }
              </p>
              
              <button className="w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700">
                {profile?.subscriptionTier === 'free' ? 'Upgrade Plan' : 'Manage Subscription'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}