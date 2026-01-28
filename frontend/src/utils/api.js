import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const submitQuestion = async (question) => {
  try {
    const response = await apiClient.post('/qa', { question });
    return response.data;
  } catch (error) {
    console.error('Error submitting question:', error);
    throw error;
  }
};

export const transcribeAudio = async (audioBlob) => {
  try {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.wav');
    
    const response = await axios.post(`${API_BASE_URL}/transcribe`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.transcription;
  } catch (error) {
    console.error('Error transcribing audio:', error);
    throw error;
  }
};

export const synthesizeSpeech = async (text, model) => {
  try {
    // Validate input
    if (!text || typeof text !== 'string') {
      throw new Error('Invalid text input for synthesis');
    }
    
    if (!model) {
      throw new Error('Model name is required for synthesis');
    }
    
    console.log(`🔊 Requesting synthesis for ${model}: ${text.substring(0, 50)}...`);
    
    const response = await apiClient.post('/synthesize', { 
      text: text.trim(), 
      model 
    });
    
    if (response.data.audio_base64) {
      // Convert base64 to blob
      const binaryString = atob(response.data.audio_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      console.log(`✅ Audio synthesized successfully for ${model}`);
      return url;
    }
    
    throw new Error('No audio data received from server');
  } catch (error) {
    console.error('❌ Error synthesizing speech:', error);
    if (error.response) {
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
    }
    throw error;
  }
};

