import React from 'react';
import { FiSend } from 'react-icons/fi';

const QueryInput = ({ value, onChange, onSubmit, isLoading, disabled }) => {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="flex gap-2 mb-6">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Ask a question about Sunmarke School..."
        disabled={disabled}
        rows="2"
        className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all resize-none disabled:bg-gray-50 disabled:text-gray-500"
      />
      <button
        onClick={onSubmit}
        disabled={!value.trim() || isLoading || disabled}
        className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-semibold transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap h-fit"
      >
        {isLoading ? (
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
        ) : (
          <FiSend size={18} />
        )}
        <span className="hidden sm:inline">Ask</span>
      </button>
    </div>
  );
};

export default QueryInput;
