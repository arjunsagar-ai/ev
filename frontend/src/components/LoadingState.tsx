import React from 'react';
import { Loader2, Navigation, Radio } from 'lucide-react';

interface LoadingStateProps {
  step: 'gps' | 'routing';
}

export const LoadingState: React.FC<LoadingStateProps> = ({ step }) => {
  return (
    <div className="bg-white/90 backdrop-blur-sm border border-emerald-100 rounded-xl p-4 shadow-sm animate-pulse">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
          {step === 'gps' ? (
            <Radio className="w-5 h-5 animate-pulse" />
          ) : (
            <Navigation className="w-5 h-5 animate-spin" />
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
            <h4 className="text-sm font-semibold text-gray-800">
              {step === 'gps'
                ? 'Finding your location...'
                : 'Finding nearest feasible charging station...'}
            </h4>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {step === 'gps'
              ? 'Requesting GPS coordinates from your browser'
              : 'Snapping to road network & running Dijkstra routing'}
          </p>
        </div>
      </div>
    </div>
  );
};
