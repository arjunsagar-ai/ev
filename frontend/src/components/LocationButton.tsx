import React from 'react';
import { LocateFixed, Loader2, RefreshCw } from 'lucide-react';

interface LocationButtonProps {
  onClick: () => void;
  isLoading: boolean;
  isError: boolean;
  loadingStep?: 'gps' | 'routing' | null;
  disabled?: boolean;
}

export const LocationButton: React.FC<LocationButtonProps> = ({
  onClick,
  isLoading,
  isError,
  loadingStep,
  disabled = false,
}) => {
  const getButtonLabel = () => {
    if (isLoading) {
      if (loadingStep === 'gps') {
        return 'Detecting location...';
      }
      return 'Finding charging station...';
    }
    if (isError) {
      return 'Try Again';
    }
    return 'Use My Location';
  };

  const getButtonIcon = () => {
    if (isLoading) {
      return <Loader2 className="w-5 h-5 animate-spin mr-2" />;
    }
    if (isError) {
      return <RefreshCw className="w-5 h-5 mr-2" />;
    }
    return <LocateFixed className="w-5 h-5 mr-2" />;
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isLoading || disabled}
      className={`w-full inline-flex items-center justify-center px-5 py-3.5 border border-transparent 
        text-base font-semibold rounded-xl shadow-md transition-all duration-200 focus:outline-none 
        focus:ring-2 focus:ring-offset-2 ${
          isError
            ? 'bg-amber-600 hover:bg-amber-700 text-white focus:ring-amber-500'
            : 'bg-emerald-600 hover:bg-emerald-700 text-white focus:ring-emerald-500'
        } ${isLoading || disabled ? 'opacity-75 cursor-not-allowed' : 'active:scale-[0.98]'}`}
    >
      {getButtonIcon()}
      <span>{getButtonLabel()}</span>
    </button>
  );
};
