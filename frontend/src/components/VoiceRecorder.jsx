import React from 'react';
import { FiMic, FiMicOff, FiSend, FiTrash2 } from 'react-icons/fi';
import { useAudioRecorder } from '../utils/audioRecorder';
import { transcribeAudio } from '../utils/api';

const VoiceRecorder = ({ onTranscription, isLoading, onClear }) => {
  const [isRecording, setIsRecording] = React.useState(false);
  const [isProcessing, setIsProcessing] = React.useState(false);
  const [recordingTime, setRecordingTime] = React.useState(0);
  const { startRecording, stopRecording, isRecording: getIsRecording } = useAudioRecorder();
  const recordingTimerRef = React.useRef(null);

  const handleStartRecording = async () => {
    const success = await startRecording();
    if (success) {
      setIsRecording(true);
      setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1);
      }, 1000);
    } else {
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const handleStopRecording = async () => {
    clearInterval(recordingTimerRef.current);
    setIsRecording(false);
    setIsProcessing(true);

    try {
      const audioBlob = await stopRecording();
      if (audioBlob) {
        const transcription = await transcribeAudio(audioBlob);
        onTranscription(transcription);
      }
    } catch (error) {
      console.error('Transcription error:', error);
      alert('Failed to transcribe audio. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center gap-3 mb-6">
      <button
        onClick={isRecording ? handleStopRecording : handleStartRecording}
        disabled={isLoading || isProcessing}
        className={`flex-shrink-0 p-4 rounded-full transition-all duration-200 ${
          isRecording
            ? 'bg-danger-500 hover:bg-danger-600 text-white animate-pulse'
            : 'bg-primary-500 hover:bg-primary-600 text-white'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
        title={isRecording ? 'Stop recording' : 'Start recording'}
      >
        {isRecording ? (
          <FiMicOff size={24} />
        ) : (
          <FiMic size={24} />
        )}
      </button>

      {isRecording && (
        <div className="text-sm font-semibold text-danger-600 min-w-[50px]">
          {formatTime(recordingTime)}
        </div>
      )}

      {isProcessing && (
        <div className="text-sm text-primary-600 font-medium">
          Transcribing...
        </div>
      )}

      <button
        onClick={onClear}
        disabled={isLoading || isRecording}
        className="ml-auto p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title="Clear"
      >
        <FiTrash2 size={20} />
      </button>
    </div>
  );
};

export default VoiceRecorder;
