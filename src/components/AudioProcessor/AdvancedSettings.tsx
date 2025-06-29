import React from 'react';

interface AdvancedSettingsProps {
  settings: {
    targetLUFS: number;
    limitThreshold: number;
    enhanceVocals: boolean;
    stereoWidth: number;
    bassBoost: number;
    trebleBoost: number;
  };
  onChange: (settings: any) => void;
}

export default function AdvancedSettings({ settings, onChange }: AdvancedSettingsProps) {
  return (
    <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Target LUFS: {settings.targetLUFS} dB
          </label>
          <input
            type="range"
            min="-24"
            max="-9"
            step="1"
            value={settings.targetLUFS}
            onChange={(e) => onChange({
              ...settings,
              targetLUFS: parseInt(e.target.value)
            })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>Quieter (-24dB)</span>
            <span>Louder (-9dB)</span>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Limiter Threshold: {settings.limitThreshold} dB
          </label>
          <input
            type="range"
            min="-6"
            max="0"
            step="0.5"
            value={settings.limitThreshold}
            onChange={(e) => onChange({
              ...settings,
              limitThreshold: parseFloat(e.target.value)
            })}
            className="w-full"
          />
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Stereo Width: {settings.stereoWidth}%
        </label>
        <input
          type="range"
          min="0"
          max="200"
          step="5"
          value={settings.stereoWidth}
          onChange={(e) => onChange({
            ...settings,
            stereoWidth: parseInt(e.target.value)
          })}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>Mono (0%)</span>
          <span>Wide (200%)</span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bass Boost: {settings.bassBoost > 0 ? '+' : ''}{settings.bassBoost} dB
          </label>
          <input
            type="range"
            min="-6"
            max="6"
            step="0.5"
            value={settings.bassBoost}
            onChange={(e) => onChange({
              ...settings,
              bassBoost: parseFloat(e.target.value)
            })}
            className="w-full"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Treble Boost: {settings.trebleBoost > 0 ? '+' : ''}{settings.trebleBoost} dB
          </label>
          <input
            type="range"
            min="-6"
            max="6"
            step="0.5"
            value={settings.trebleBoost}
            onChange={(e) => onChange({
              ...settings,
              trebleBoost: parseFloat(e.target.value)
            })}
            className="w-full"
          />
        </div>
      </div>
      
      <div className="flex items-center">
        <input
          type="checkbox"
          id="enhance-vocals"
          checked={settings.enhanceVocals}
          onChange={(e) => onChange({
            ...settings,
            enhanceVocals: e.target.checked
          })}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="enhance-vocals" className="ml-2 block text-sm text-gray-700">
          Enhance vocals (improves clarity and presence of vocal tracks)
        </label>
      </div>
    </div>
  );
}