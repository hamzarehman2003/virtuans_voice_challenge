import React from 'react';

const SourcePanel = ({ sources, isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-96 overflow-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <h3 className="text-lg font-bold text-gray-900">Source References</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-4">
          {sources && sources.length > 0 ? (
            sources.map((source, idx) => (
              <div
                key={idx}
                className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="mb-2">
                  <p className="font-semibold text-gray-900 text-sm">
                    {source.title || 'Untitled'}
                  </p>
                  <p className="text-xs text-gray-500">
                    Similarity: {(source.similarity * 100).toFixed(1)}%
                  </p>
                </div>
                <p className="text-sm text-gray-700 mb-3">
                  {source.preview}
                </p>
                {source.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                  >
                    View Source →
                  </a>
                )}
              </div>
            ))
          ) : (
            <p className="text-gray-500 text-center py-4">No sources available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default SourcePanel;
