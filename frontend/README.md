# Sunmarke Voice Agent - Frontend

Professional React UI for voice-enabled AI Q&A system.

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

The app will open at `http://localhost:3000`

Make sure the backend is running on `http://localhost:8000`

## Environment Variables

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

Edit as needed:
- `VITE_API_URL`: Backend API URL (default: `http://localhost:8000`)

## Build

```bash
npm run build
```

## Features

- 🎤 Real-time voice recording
- 🤖 3-model AI comparison (Gemini, DeepSeek, Kimi)
- 📝 Transcription display
- 🔊 Audio playback for responses
- 📚 Source reference panel
- 💾 Query history
- 🎨 Clean, professional UI

## Project Structure

```
src/
├── components/
│   ├── Header.jsx           # App header
│   ├── VoiceRecorder.jsx    # Voice recording component
│   ├── QueryInput.jsx       # Query input textarea
│   ├── ResponseCard.jsx     # Individual model response card
│   └── SourcePanel.jsx      # Source references modal
├── utils/
│   ├── api.js              # API client & endpoints
│   └── audioRecorder.js    # Audio recording hook
├── App.jsx                 # Main app component
├── index.css               # Tailwind CSS
└── main.jsx               # React entry point
```

## Technologies

- React 18
- Vite
- Tailwind CSS
- React Icons
- Axios

## API Endpoints Required

Backend must provide:

- `POST /qa` - Submit question, get 3 model responses
- `POST /transcribe` - Audio to text (optional for voice recording)
- `POST /synthesize` - Text to speech for audio playback (optional)
