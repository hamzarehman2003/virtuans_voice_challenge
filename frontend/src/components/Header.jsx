import React from 'react';

const Header = () => {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">🎤</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Sunmarke Voice Agent</h1>
              {/* <p className="text-sm text-gray-500">AI-powered Q&A with 3 model comparison</p> */}
            </div>
          </div>
          <div className="hidden sm:block text-right">
            {/* <p className="text-xs text-gray-500">Powered by Gemini, DeepSeek & Kimi</p> */}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
