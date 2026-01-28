// Persistent recorder state
const recorderState = {
  mediaRecorder: null,
  audioChunks: [],
  stream: null
};

export const useAudioRecorder = () => {
  const startRecording = async () => {
    try {
      // Stop any existing recording first
      if (recorderState.stream) {
        recorderState.stream.getTracks().forEach(track => track.stop());
      }
      
      recorderState.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recorderState.mediaRecorder = new MediaRecorder(recorderState.stream);
      recorderState.audioChunks = [];

      recorderState.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recorderState.audioChunks.push(event.data);
        }
      };

      recorderState.mediaRecorder.start();
      return true;
    } catch (error) {
      console.error('Error accessing microphone:', error);
      return false;
    }
  };

  const stopRecording = () => {
    return new Promise((resolve) => {
      if (recorderState.mediaRecorder && recorderState.mediaRecorder.state !== 'inactive') {
        recorderState.mediaRecorder.onstop = () => {
          const audioBlob = new Blob(recorderState.audioChunks, { type: 'audio/wav' });
          // Stop all tracks
          if (recorderState.stream) {
            recorderState.stream.getTracks().forEach(track => track.stop());
            recorderState.stream = null;
          }
          resolve(audioBlob);
        };
        recorderState.mediaRecorder.stop();
      } else {
        resolve(null);
      }
    });
  };

  const isRecording = () => recorderState.mediaRecorder?.state === 'recording';

  return { startRecording, stopRecording, isRecording };
};
