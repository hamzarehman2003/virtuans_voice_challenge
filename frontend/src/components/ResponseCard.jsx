import React from 'react';
import { FiVolume2, FiPause, FiSquare, FiCopy, FiCheck } from 'react-icons/fi';

const ResponseCard = ({ model, answer, audioUrl, loading, synthesizing, isPlaying, onTogglePlayPause, onStopAudio, score, firstTokenMs, totalMs }) => {
  const [copied, setCopied] = React.useState(false);

  const modelColors = {
    gemini: 'from-blue-50 to-blue-50 border-blue-200',
    deepseek: 'from-purple-50 to-purple-50 border-purple-200',
    kimi: 'from-pink-50 to-pink-50 border-pink-200',
  };

  const modelBadgeColors = {
    gemini: 'bg-blue-100 text-blue-800',
    deepseek: 'bg-purple-100 text-purple-800',
    kimi: 'bg-pink-100 text-pink-800',
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatMs = (ms) => {
    if (ms == null) return '—';
    const s = ms / 1000;
    return s < 10 ? `${s.toFixed(2)}s` : `${s.toFixed(1)}s`;
  };

  return (
    <div className={`flex flex-col h-full border-2 rounded-xl p-6 bg-gradient-to-br ${modelColors[model]}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${modelBadgeColors[model]}`}>
            {model.charAt(0).toUpperCase() + model.slice(1)}
          </span>
          <span className="text-xs text-gray-700 bg-white/70 border border-gray-200 rounded-full px-2 py-1">
            Score: {score ?? '—'}/10
          </span>
        </div>
        <div className="text-xs text-gray-600 text-right">
          <div>First: {formatMs(firstTokenMs)}</div>
          <div>Done: {formatMs(totalMs)}</div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-primary-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500">Generating response...</p>
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 mb-4">
            <p className="text-gray-700 leading-relaxed text-sm">
              {answer || 'No response received'}
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-2 border-t border-gray-200 pt-4">
            <button
              onClick={() => onTogglePlayPause(model)}
              disabled={!answer || synthesizing}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                synthesizing
                  ? 'bg-primary-400 text-white cursor-not-allowed'
                  : 'bg-primary-500 hover:bg-primary-600 text-white'
              } ${!answer ? 'bg-gray-300 cursor-not-allowed' : ''}`}
              title={isPlaying ? 'Pause audio' : 'Play audio response'}
            >
              {synthesizing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  <span className="hidden sm:inline">Generating...</span>
                </>
              ) : (
                <>
                  {isPlaying ? <FiPause size={16} /> : <FiVolume2 size={16} />}
                  <span className="hidden sm:inline">{isPlaying ? 'Pause' : 'Play'}</span>
                </>
              )}
            </button>
            <button
              onClick={() => onStopAudio(model)}
              disabled={!answer || synthesizing}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Stop audio"
            >
              <FiSquare size={16} />
              <span className="hidden sm:inline">Stop</span>
            </button>
            <button
              onClick={handleCopy}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <FiCheck size={16} className="text-success-600" />
              ) : (
                <FiCopy size={16} />
              )}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ResponseCard;
