import React from 'react';
import { AlertCircle, X } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  title?: string;
  onDismiss?: () => void;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  title = 'Notice',
  onDismiss,
  onRetry,
}) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-4 shadow-sm text-red-800">
      <div className="flex items-start">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div className="ml-3 flex-1">
          <h4 className="text-sm font-semibold text-red-900">
            {title}
          </h4>
          <p className="text-sm text-red-700 mt-1 leading-relaxed">
            {message}
          </p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center text-xs font-semibold text-red-800 hover:text-red-900 underline"
            >
              Try Again
            </button>
          )}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="ml-2 text-red-400 hover:text-red-600 rounded-lg p-1"
            aria-label="Dismiss error"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
