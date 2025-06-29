import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, TrendingUp, Clock, DollarSign, Music, Calendar } from 'lucide-react';
import { apiClient } from '../../services/api';
import LoadingSpinner from '../../components/UI/LoadingSpinner';

const TIME_PERIODS = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 3 months' }
];

export default function Analytics() {
  const [selectedPeriod, setSelectedPeriod] = useState('30');

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get(`/analytics/usage?period=last_${selectedPeriod}_days`);
      return response.data;
    }
  });

  const { data: costs } = useQuery({
    queryKey: ['cost-analytics', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get(`/analytics/costs?days=${selectedPeriod}`);
      return response.data;
    }
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-purple-600" />
              Analytics Dashboard
            </h1>
            <p className="text-gray-600 mt-1">
              Track your music creation and processing analytics
            </p>
          </div>
          
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            {TIME_PERIODS.map(period => (
              <option key={period.value} value={period.value}>
                {period.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="large" />
        </div>
      ) : (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Music className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Jobs</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {analytics?.total_jobs || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Success Rate</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {analytics?.successful_jobs && analytics?.total_jobs 
                      ? Math.round((analytics.successful_jobs / analytics.total_jobs) * 100)
                      : 0}%
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Clock className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Avg. Time</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {analytics?.average_processing_time 
                      ? `${Math.round(analytics.average_processing_time)}s`
                      : '0s'}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <DollarSign className="h-6 w-6 text-orange-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${costs?.total_cost?.toFixed(2) || '0.00'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Charts and Detailed Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Popular Workflows */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Popular Workflows</h2>
              
              <div className="space-y-4">
                {analytics?.popular_workflows?.map((workflow: any, index: number) => (
                  <div key={workflow.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                        <span className="text-sm font-medium text-purple-600">
                          {index + 1}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 capitalize">
                          {workflow.name.replace('_', ' ')}
                        </p>
                        <p className="text-sm text-gray-600">
                          {workflow.usage_count} uses
                        </p>
                      </div>
                    </div>
                    
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-purple-600 h-2 rounded-full"
                        style={{ 
                          width: `${(workflow.usage_count / Math.max(...analytics.popular_workflows.map((w: any) => w.usage_count))) * 100}%` 
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Model Performance */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Performance</h2>
              
              <div className="space-y-4">
                {Object.entries(analytics?.model_performance || {}).map(([model, performance]: [string, any]) => (
                  <div key={model} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-medium text-gray-900 capitalize">
                        {model.replace('_', ' ')}
                      </h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        performance.success_rate > 0.9 
                          ? 'bg-green-100 text-green-800'
                          : performance.success_rate > 0.8
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {Math.round(performance.success_rate * 100)}% success
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Avg. Time:</span>
                        <span className="ml-1 font-medium">{performance.avg_time}s</span>
                      </div>
                      <div>
                        <span className="text-gray-600">Reliability:</span>
                        <span className="ml-1 font-medium">
                          {Math.round(performance.success_rate * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Cost Breakdown */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Cost Breakdown by Service</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(costs?.service_breakdown || {}).map(([service, cost]) => (
                <div key={service} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 capitalize text-sm">
                      {service.replace('_', ' ')}
                    </span>
                    <span className="font-semibold text-gray-900">
                      ${(cost as number).toFixed(3)}
                    </span>
                  </div>
                  
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                    <div 
                      className="bg-purple-600 h-1.5 rounded-full"
                      style={{ 
                        width: `${((cost as number) / costs.total_cost) * 100}%` 
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}