import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCard, DollarSign, Calendar, TrendingUp, Download } from 'lucide-react';
import { apiClient } from '../../services/api';
import LoadingSpinner from '../../components/UI/LoadingSpinner';

const SUBSCRIPTION_PLANS = [
  {
    name: 'Free',
    price: 0,
    credits: 100,
    features: ['100 credits/month', 'Basic AI models', 'Standard quality', 'Community support']
  },
  {
    name: 'Premium',
    price: 19,
    credits: 1000,
    features: ['1,000 credits/month', 'All AI models', 'High quality', 'Priority support', 'Advanced features']
  },
  {
    name: 'Pro',
    price: 49,
    credits: 5000,
    features: ['5,000 credits/month', 'All AI models', 'Maximum quality', '24/7 support', 'Custom workflows', 'API access']
  }
];

export default function Billing() {
  const { data: usage, isLoading: usageLoading } = useQuery({
    queryKey: ['usage-analytics'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/costs?days=30');
      return response.data;
    }
  });

  const { data: invoices, isLoading: invoicesLoading } = useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      // Mock data for now
      return [
        {
          id: 'inv_001',
          date: '2024-01-01',
          amount: 19.00,
          status: 'paid',
          description: 'Premium Plan - January 2024'
        },
        {
          id: 'inv_002',
          date: '2023-12-01',
          amount: 19.00,
          status: 'paid',
          description: 'Premium Plan - December 2023'
        }
      ];
    }
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <CreditCard className="h-6 w-6 text-purple-600" />
          Billing & Usage
        </h1>
        <p className="text-gray-600 mt-1">
          Manage your subscription and view usage analytics
        </p>
      </div>

      {/* Usage Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <DollarSign className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">This Month</p>
              <p className="text-2xl font-bold text-gray-900">
                ${usage?.total_cost?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Credits Used</p>
              <p className="text-2xl font-bold text-gray-900">
                {Object.values(usage?.service_breakdown || {}).reduce((a: number, b: number) => a + b, 0).toFixed(0)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Calendar className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Next Billing</p>
              <p className="text-2xl font-bold text-gray-900">Jan 15</p>
            </div>
          </div>
        </div>
      </div>

      {/* Subscription Plans */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Subscription Plans</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SUBSCRIPTION_PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`border rounded-lg p-6 ${
                plan.name === 'Premium' 
                  ? 'border-purple-500 bg-purple-50' 
                  : 'border-gray-200'
              }`}
            >
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                <div className="mt-2">
                  <span className="text-3xl font-bold text-gray-900">${plan.price}</span>
                  <span className="text-gray-600">/month</span>
                </div>
                <p className="text-sm text-gray-600 mt-1">{plan.credits} credits included</p>
              </div>
              
              <ul className="mt-6 space-y-3">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center text-sm text-gray-600">
                    <div className="w-1.5 h-1.5 bg-purple-600 rounded-full mr-3" />
                    {feature}
                  </li>
                ))}
              </ul>
              
              <button
                className={`w-full mt-6 py-2 px-4 rounded-lg font-medium ${
                  plan.name === 'Premium'
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {plan.name === 'Premium' ? 'Current Plan' : 
                 plan.name === 'Free' ? 'Downgrade' : 'Upgrade'}
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Usage Breakdown */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Usage Breakdown</h2>
          
          {usageLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(usage?.service_breakdown || {}).map(([service, cost]) => (
                <div key={service} className="flex justify-between items-center">
                  <span className="text-gray-600 capitalize">{service.replace('_', ' ')}</span>
                  <span className="font-medium text-gray-900">${(cost as number).toFixed(3)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Invoices */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Invoices</h2>
            <button className="text-purple-600 hover:text-purple-700 text-sm font-medium">
              View All
            </button>
          </div>
          
          {invoicesLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="space-y-4">
              {invoices?.map((invoice: any) => (
                <div key={invoice.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">${invoice.amount.toFixed(2)}</p>
                    <p className="text-sm text-gray-600">{invoice.description}</p>
                    <p className="text-xs text-gray-500">{new Date(invoice.date).toLocaleDateString()}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      invoice.status === 'paid' 
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {invoice.status}
                    </span>
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}