import React from 'react';
import { Link } from 'react-router-dom';
import { Music, Sparkles, Sliders, Download, Play, ArrowRight, Check } from 'lucide-react';

const HomePage: React.FC = () => {
  const features = [
    {
      icon: Sparkles,
      title: 'AI Music Generation',
      description: 'Create original music from text prompts using advanced AI models like MusicGen, Suno AI, and more.',
    },
    {
      icon: Sliders,
      title: 'Professional Mastering',
      description: 'Master your tracks with LANDR-powered AI that applies professional EQ, compression, and limiting.',
    },
    {
      icon: Music,
      title: 'Multi-Format Support',
      description: 'Upload and process WAV, MP3, FLAC, and other popular audio formats with ease.',
    },
    {
      icon: Download,
      title: 'Instant Downloads',
      description: 'Download your mastered tracks immediately in high-quality formats ready for distribution.',
    },
  ];

  const pricingPlans = [
    {
      name: 'Free',
      price: '$0',
      period: '/month',
      features: [
        '100 API calls per month',
        '10MB max file size',
        '1 concurrent session',
        '1GB storage',
        'Basic mastering presets',
      ],
      cta: 'Get Started',
      popular: false,
    },
    {
      name: 'Premium',
      price: '$19',
      period: '/month',
      features: [
        '1,000 API calls per month',
        '50MB max file size',
        '3 concurrent sessions',
        '10GB storage',
        'Advanced mastering options',
        'Priority processing',
      ],
      cta: 'Start Free Trial',
      popular: true,
    },
    {
      name: 'Pro',
      price: '$49',
      period: '/month',
      features: [
        '10,000 API calls per month',
        '100MB max file size',
        '10 concurrent sessions',
        '100GB storage',
        'Custom mastering presets',
        'API access',
        'Priority support',
      ],
      cta: 'Contact Sales',
      popular: false,
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-900 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Music className="h-8 w-8 text-indigo-600" />
              <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
                AI Music Studio
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/login"
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 px-3 py-2 rounded-md text-sm font-medium"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="relative z-10 pb-8 bg-white dark:bg-gray-900 sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32">
            <main className="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
              <div className="sm:text-center lg:text-left">
                <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 dark:text-white sm:text-5xl md:text-6xl">
                  <span className="block xl:inline">AI-Powered</span>{' '}
                  <span className="block text-indigo-600 xl:inline">Music Creation</span>
                </h1>
                <p className="mt-3 text-base text-gray-500 dark:text-gray-400 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                  Generate, master, and perfect your music with cutting-edge AI technology. 
                  From text-to-music generation to professional mastering, create studio-quality tracks in minutes.
                </p>
                <div className="mt-5 sm:mt-8 sm:flex sm:justify-center lg:justify-start">
                  <div className="rounded-md shadow">
                    <Link
                      to="/register"
                      className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 md:py-4 md:text-lg md:px-10"
                    >
                      Start Creating
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </Link>
                  </div>
                  <div className="mt-3 sm:mt-0 sm:ml-3">
                    <Link
                      to="/login"
                      className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 md:py-4 md:text-lg md:px-10"
                    >
                      <Play className="mr-2 h-5 w-5" />
                      Watch Demo
                    </Link>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </div>
        <div className="lg:absolute lg:inset-y-0 lg:right-0 lg:w-1/2">
          <div className="h-56 w-full bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 sm:h-72 md:h-96 lg:w-full lg:h-full flex items-center justify-center">
            <div className="text-center text-white">
              <Music className="h-24 w-24 mx-auto mb-4 opacity-80" />
              <p className="text-xl font-semibold">AI Music Studio</p>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-12 bg-gray-50 dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:text-center">
            <h2 className="text-base text-indigo-600 font-semibold tracking-wide uppercase">Features</h2>
            <p className="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Everything you need to create amazing music
            </p>
            <p className="mt-4 max-w-2xl text-xl text-gray-500 dark:text-gray-400 lg:mx-auto">
              Powered by the latest AI models from OpenAI, Anthropic, Google, and specialized music AI services.
            </p>
          </div>

          <div className="mt-10">
            <div className="space-y-10 md:space-y-0 md:grid md:grid-cols-2 md:gap-x-8 md:gap-y-10">
              {features.map((feature) => (
                <div key={feature.title} className="relative">
                  <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                    <feature.icon className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <p className="ml-16 text-lg leading-6 font-medium text-gray-900 dark:text-white">
                    {feature.title}
                  </p>
                  <p className="mt-2 ml-16 text-base text-gray-500 dark:text-gray-400">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Pricing Section */}
      <div className="bg-white dark:bg-gray-900">
        <div className="max-w-7xl mx-auto py-24 px-4 sm:px-6 lg:px-8">
          <div className="sm:flex sm:flex-col sm:align-center">
            <h1 className="text-5xl font-extrabold text-gray-900 dark:text-white sm:text-center">
              Pricing Plans
            </h1>
            <p className="mt-5 text-xl text-gray-500 dark:text-gray-400 sm:text-center">
              Start for free, upgrade as you grow
            </p>
          </div>
          <div className="mt-12 space-y-4 sm:mt-16 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-6 lg:max-w-4xl lg:mx-auto xl:max-w-none xl:mx-0 xl:grid-cols-3">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={`border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm divide-y divide-gray-200 dark:divide-gray-700 ${
                  plan.popular
                    ? 'border-indigo-500 dark:border-indigo-400 ring-2 ring-indigo-500 dark:ring-indigo-400'
                    : ''
                }`}
              >
                <div className="p-6">
                  {plan.popular && (
                    <p className="text-sm font-medium text-indigo-500 dark:text-indigo-400">Most Popular</p>
                  )}
                  <p className="text-lg leading-6 font-medium text-gray-900 dark:text-white">{plan.name}</p>
                  <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                    Perfect for {plan.name.toLowerCase()} users
                  </p>
                  <p className="mt-8">
                    <span className="text-4xl font-extrabold text-gray-900 dark:text-white">{plan.price}</span>
                    <span className="text-base font-medium text-gray-500 dark:text-gray-400">{plan.period}</span>
                  </p>
                  <Link
                    to="/register"
                    className={`mt-8 block w-full py-2 px-4 border border-transparent rounded-md text-sm font-semibold text-center ${
                      plan.popular
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                        : 'bg-indigo-50 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-200 hover:bg-indigo-100 dark:hover:bg-indigo-800'
                    }`}
                  >
                    {plan.cta}
                  </Link>
                </div>
                <div className="pt-6 pb-8 px-6">
                  <h3 className="text-xs font-medium text-gray-900 dark:text-white tracking-wide uppercase">
                    What's included
                  </h3>
                  <ul className="mt-6 space-y-4">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex space-x-3">
                        <Check className="flex-shrink-0 h-5 w-5 text-green-500" aria-hidden="true" />
                        <span className="text-sm text-gray-500 dark:text-gray-400">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-indigo-700">
        <div className="max-w-2xl mx-auto text-center py-16 px-4 sm:py-20 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
            <span className="block">Ready to create amazing music?</span>
            <span className="block">Start your free trial today.</span>
          </h2>
          <p className="mt-4 text-lg leading-6 text-indigo-200">
            Join thousands of musicians and producers using AI to create their next hit.
          </p>
          <Link
            to="/register"
            className="mt-8 w-full inline-flex items-center justify-center px-5 py-3 border border-transparent text-base font-medium rounded-md text-indigo-600 bg-white hover:bg-indigo-50 sm:w-auto"
          >
            Get Started Free
            <ArrowRight className="ml-2 h-5 w-5" />
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-900">
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 md:flex md:items-center md:justify-between lg:px-8">
          <div className="flex justify-center space-x-6 md:order-2">
            <div className="flex items-center">
              <Music className="h-6 w-6 text-indigo-600" />
              <span className="ml-2 text-lg font-bold text-gray-900 dark:text-white">
                AI Music Studio
              </span>
            </div>
          </div>
          <div className="mt-8 md:mt-0 md:order-1">
            <p className="text-center text-base text-gray-400">
              &copy; 2024 AI Music Studio. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;