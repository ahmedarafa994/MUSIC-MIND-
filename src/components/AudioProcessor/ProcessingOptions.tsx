import React from 'react';
import { Volume2, Zap, Sliders, AudioWaveform as Waveform } from 'lucide-react';

interface ProcessingOption {
  id: string;
  name: string;
  description: string;
  cost: number;
  icon: React.ElementType;
  color: string;
}

interface ProcessingOptionsProps {
  options: ProcessingOption[];
  selectedOption: string;
  onSelect: (id: string) => void;
}

export default function ProcessingOptions({ 
  options, 
  selectedOption, 
  onSelect 
}: ProcessingOptionsProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-3">
        Processing Operation
      </label>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {options.map((option) => {
          const Icon = option.icon;
          return (
            <div
              key={option.id}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedOption === option.id
                  ? `border-${option.color}-500 bg-${option.color}-50`
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onClick={() => onSelect(option.id)}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-${option.color}-100`}>
                  <Icon className={`h-5 w-5 text-${option.color}-600`} />
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">{option.name}</h4>
                  <p className="text-sm text-gray-600">{option.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}