import React, { useRef, useState } from 'react';
import { FiInfo } from 'react-icons/fi';
import Header from './components/Header';
import VoiceRecorder from './components/VoiceRecorder';
import QueryInput from './components/QueryInput';
import ResponseCard from './components/ResponseCard';
import SourcePanel from './components/SourcePanel';
import { synthesizeSpeech } from './utils/api';

function App() {
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const [query, setQuery] = useState('');
  const [responses, setResponses] = useState({
    gemini: null,
    deepseek: null,
    kimi: null,
  });
  const [loading, setLoading] = useState({
    gemini: false,
    deepseek: false,
    kimi: false,
  });
  const [synthesizing, setSynthesizing] = useState({
    gemini: false,
    deepseek: false,
    kimi: false,
  });
  const [sources, setSources] = useState([]);
  const [hasContext, setHasContext] = useState(true);
  const [showSources, setShowSources] = useState(false);
  const [audioUrls, setAudioUrls] = useState({
    gemini: null,
    deepseek: null,
    kimi: null,
  });
  const audioRefs = useRef({ gemini: null, deepseek: null, kimi: null });
  const [isPlaying, setIsPlaying] = useState({ gemini: false, deepseek: false, kimi: false });
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const sseRef = useRef(null);
  const requestStartRef = useRef(0);
  const [metrics, setMetrics] = useState({
    gemini: { firstTokenMs: null, totalMs: null },
    deepseek: { firstTokenMs: null, totalMs: null },
    kimi: { firstTokenMs: null, totalMs: null },
  });

  const scoreAnswer = (text) => {
    if (!text) return 0;
    const t = String(text);
    if (t.startsWith('Error:')) return 0;
    if (t.trim() === 'No context found.') return 1;
    let score = 2;
    if (t.length >= 80) score += 1;
    if (t.length >= 180) score += 1;
    if (t.includes('\n') || t.includes('- ') || t.includes('•')) score += 1;
    if (/(http|www\.)/i.test(t)) score += 1;
    return Math.min(score, 10);
  };

  const formatMs = (ms) => {
    if (ms == null) return '—';
    const s = ms / 1000;
    return s < 10 ? `${s.toFixed(2)}s` : `${s.toFixed(1)}s`;
  };

  const stopAllAudio = () => {
    (['gemini', 'deepseek', 'kimi']).forEach((m) => {
      const a = audioRefs.current[m];
      if (a) {
        a.pause();
        try {
          a.currentTime = 0;
        } catch {
          // ignore
        }
      }
    });
    setIsPlaying({ gemini: false, deepseek: false, kimi: false });
  };

  const stopStream = () => {
    if (sseRef.current) {
      try {
        sseRef.current.close();
      } catch {
        // ignore
      }
      sseRef.current = null;
    }
  };

  const handleTranscription = (transcription) => {
    setQuery(transcription);
  };

  const handleSubmit = async () => {
    if (!query.trim()) return;

    setError(null);
    stopStream();
    stopAllAudio();
    setResponses({ gemini: null, deepseek: null, kimi: null });
    setLoading({ gemini: true, deepseek: true, kimi: true });
    setAudioUrls({ gemini: null, deepseek: null, kimi: null });
    setMetrics({
      gemini: { firstTokenMs: null, totalMs: null },
      deepseek: { firstTokenMs: null, totalMs: null },
      kimi: { firstTokenMs: null, totalMs: null },
    });
    requestStartRef.current = performance.now();

    const url = `${API_BASE_URL}/qa/stream?question=${encodeURIComponent(query)}`;
    const es = new EventSource(url);
    sseRef.current = es;

    const answersSoFar = { gemini: '', deepseek: '', kimi: '' };

    es.addEventListener('meta', (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        setHasContext(Boolean(payload.has_context));
        setSources(payload.sources || []);
      } catch (e) {
        console.error('Failed to parse meta event', e);
      }
    });

    es.addEventListener('delta', (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        const model = payload.model;
        const delta = payload.delta || '';
        if (!model || !delta) return;

        setMetrics((prev) => {
          if (prev?.[model]?.firstTokenMs != null) return prev;
          const elapsed = performance.now() - requestStartRef.current;
          return { ...prev, [model]: { ...prev[model], firstTokenMs: elapsed } };
        });

        answersSoFar[model] = (answersSoFar[model] || '') + delta;
        setResponses((prev) => ({ ...prev, [model]: answersSoFar[model] }));
      } catch (e) {
        console.error('Failed to parse delta event', e);
      }
    });

    es.addEventListener('answer', (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        const model = payload.model;
        const text = payload.text;
        if (!model) return;

        // If we didn't stream deltas (e.g. error), set final text.
        if (!answersSoFar[model]) {
          setMetrics((prev) => {
            const elapsed = performance.now() - requestStartRef.current;
            const first = prev?.[model]?.firstTokenMs ?? elapsed;
            return { ...prev, [model]: { ...prev[model], firstTokenMs: first } };
          });
          answersSoFar[model] = text || 'No response';
          setResponses((prev) => ({ ...prev, [model]: answersSoFar[model] }));
        }
      } catch (e) {
        console.error('Failed to parse answer event', e);
      }
    });

    es.addEventListener('model_done', (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        const model = payload.model;
        if (!model) return;
        setMetrics((prev) => {
          const elapsed = performance.now() - requestStartRef.current;
          const first = prev?.[model]?.firstTokenMs ?? elapsed;
          return { ...prev, [model]: { ...prev[model], firstTokenMs: first, totalMs: elapsed } };
        });
        setLoading((prev) => ({ ...prev, [model]: false }));
      } catch (e) {
        console.error('Failed to parse model_done event', e);
      }
    });

    es.addEventListener('done', () => {
      setLoading({ gemini: false, deepseek: false, kimi: false });
      stopStream();

      setHistory((prev) => ([
        {
          query,
          responses: { ...answersSoFar },
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev.slice(0, 9),
      ]));
    });

    es.onerror = () => {
      setError('Streaming failed. Please check the backend server.');
      setLoading({ gemini: false, deepseek: false, kimi: false });
      stopStream();
    };
  };

  const ensureAudioForModel = async (model) => {
    if (audioRefs.current[model]) return audioRefs.current[model];

    const existingUrl = audioUrls[model];
    if (existingUrl) {
      const audio = new Audio(existingUrl);
      audio.onended = () => setIsPlaying(prev => ({ ...prev, [model]: false }));
      audioRefs.current[model] = audio;
      return audio;
    }

    if (!responses[model]) return null;

    setSynthesizing(prev => ({ ...prev, [model]: true }));
    try {
      const audioUrl = await synthesizeSpeech(responses[model], model);
      if (!audioUrl) return null;

      setAudioUrls(prev => ({ ...prev, [model]: audioUrl }));
      const audio = new Audio(audioUrl);
      audio.onended = () => setIsPlaying(prev => ({ ...prev, [model]: false }));
      audioRefs.current[model] = audio;
      return audio;
    } catch (err) {
      setError(`Failed to generate audio for ${model}`);
      return null;
    } finally {
      setSynthesizing(prev => ({ ...prev, [model]: false }));
    }
  };

  const handleTogglePlayPause = async (model) => {
    const audio = await ensureAudioForModel(model);
    if (!audio) return;

    // Pause anything else that might be playing
    (['gemini', 'deepseek', 'kimi']).forEach((m) => {
      if (m !== model) {
        const a = audioRefs.current[m];
        if (a && !a.paused) a.pause();
      }
    });

    if (audio.paused) {
      audio.play().then(() => {
        setIsPlaying({ gemini: false, deepseek: false, kimi: false, [model]: true });
      }).catch(err => {
        console.error('Error playing audio:', err);
        setIsPlaying(prev => ({ ...prev, [model]: false }));
      });
    } else {
      audio.pause();
      setIsPlaying(prev => ({ ...prev, [model]: false }));
    }
  };

  const handleStopAudio = (model) => {
    const audio = audioRefs.current[model];
    if (audio) {
      audio.pause();
      try {
        audio.currentTime = 0;
      } catch {
        // ignore
      }
    }
    setIsPlaying(prev => ({ ...prev, [model]: false }));
  };

  const handleClear = () => {
    stopStream();
    stopAllAudio();
    setQuery('');
    setResponses({ gemini: null, deepseek: null, kimi: null });
    setSources([]);
    setError(null);
    setAudioUrls({ gemini: null, deepseek: null, kimi: null });
    setMetrics({
      gemini: { firstTokenMs: null, totalMs: null },
      deepseek: { firstTokenMs: null, totalMs: null },
      kimi: { firstTokenMs: null, totalMs: null },
    });
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Info banner */}
        {!hasContext && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex gap-3">
            <FiInfo className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
            <p className="text-sm text-yellow-800">
              No relevant information found in the knowledge base. Please try rephrasing your question.
            </p>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800 font-medium">Error: {error}</p>
            <p className="text-xs text-red-700 mt-1">
              Make sure the backend server is running on http://localhost:8000
            </p>
          </div>
        )}

        {/* Voice Input Section */}
        <section className="mb-8 bg-gradient-to-r from-primary-50 to-primary-50 p-6 rounded-xl border border-primary-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Voice Input</h2>
          <VoiceRecorder
            onTranscription={handleTranscription}
            isLoading={Object.values(loading).some(l => l)}
            onClear={handleClear}
          />
          <QueryInput
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            isLoading={Object.values(loading).some(l => l)}
            disabled={Object.values(loading).some(l => l)}
          />
        </section>

        {/* Responses Section */}
        {(responses.gemini || responses.deepseek || responses.kimi) && (
          <section className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">AI Responses</h2>
              {sources && sources.length > 0 && (
                <button
                  onClick={() => setShowSources(true)}
                  className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  View {sources.length} sources →
                </button>
              )}
            </div>

            {(() => {
              const models = ['gemini', 'deepseek', 'kimi'];
              const hasAny = models.some((m) => responses[m] != null || loading[m]);
              if (!hasAny) return null;

              const scored = models.map((m) => ({
                model: m,
                score: scoreAnswer(responses[m]),
                firstTokenMs: metrics[m].firstTokenMs,
                totalMs: metrics[m].totalMs,
              }));
              const ranked = [...scored].sort((a, b) => (b.score - a.score) || ((a.totalMs ?? 1e18) - (b.totalMs ?? 1e18)));

              return (
                <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-gray-900">Model ranking</div>
                    <div className="text-xs text-gray-600">Score (0–10) + response times</div>
                  </div>
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {ranked.map((r, idx) => (
                      <div key={r.model} className="bg-white border border-gray-200 rounded-md p-3">
                        <div className="flex items-center justify-between">
                          <div className="text-sm font-semibold text-gray-900">
                            #{idx + 1} {r.model}
                          </div>
                          <div className="text-sm font-bold text-gray-900">{r.score}/10</div>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          First token: {formatMs(r.firstTokenMs)} · Done: {formatMs(r.totalMs)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ResponseCard
                model="gemini"
                answer={responses.gemini}
                audioUrl={audioUrls.gemini}
                loading={loading.gemini}
                synthesizing={synthesizing.gemini}
                isPlaying={isPlaying.gemini}
                onTogglePlayPause={handleTogglePlayPause}
                onStopAudio={handleStopAudio}
                score={scoreAnswer(responses.gemini)}
                firstTokenMs={metrics.gemini.firstTokenMs}
                totalMs={metrics.gemini.totalMs}
              />
              <ResponseCard
                model="deepseek"
                answer={responses.deepseek}
                audioUrl={audioUrls.deepseek}
                loading={loading.deepseek}
                synthesizing={synthesizing.deepseek}
                isPlaying={isPlaying.deepseek}
                onTogglePlayPause={handleTogglePlayPause}
                onStopAudio={handleStopAudio}
                score={scoreAnswer(responses.deepseek)}
                firstTokenMs={metrics.deepseek.firstTokenMs}
                totalMs={metrics.deepseek.totalMs}
              />
              <ResponseCard
                model="kimi"
                answer={responses.kimi}
                audioUrl={audioUrls.kimi}
                loading={loading.kimi}
                synthesizing={synthesizing.kimi}
                isPlaying={isPlaying.kimi}
                onTogglePlayPause={handleTogglePlayPause}
                onStopAudio={handleStopAudio}
                score={scoreAnswer(responses.kimi)}
                firstTokenMs={metrics.kimi.firstTokenMs}
                totalMs={metrics.kimi.totalMs}
              />
            </div>
          </section>
        )}

        {/* History Section */}
        {history.length > 0 && !responses.gemini && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Queries</h2>
            <div className="space-y-2">
              {history.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(item.query)}
                  className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors text-sm border border-gray-200"
                >
                  <div className="font-medium text-gray-900 line-clamp-1">{item.query}</div>
                  <div className="text-xs text-gray-500 mt-1">{item.timestamp}</div>
                </button>
              ))}
            </div>
          </section>
        )}
      </main>

      {/* Source Panel Modal */}
      <SourcePanel
        sources={sources}
        isOpen={showSources}
        onClose={() => setShowSources(false)}
      />

      {/* Footer */}
      <footer className="bg-gray-50 border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* <p className="text-center text-sm text-gray-600">
            Built with React + FastAPI | Powered by Gemini, DeepSeek & Kimi | Voice by Deepgram & Eleven Labs
          </p> */}
        </div>
      </footer>
    </div>
  );
}

export default App;
