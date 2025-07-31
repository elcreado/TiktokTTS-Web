# Frontend Refactoring Plan

## Current Structure
- Single App.js file with ~1000+ lines
- All functionality in one component

## Refactored Structure
- components/
  - TikTokConnection/ - Connection interface
  - TTSControls/ - TTS controls and settings
  - ChatDisplay/ - Chat messages display
  - StatusBar/ - Connection and system status
- hooks/
  - useWebSocket/ - WebSocket connection logic
  - useTTS/ - TTS functionality
  - useTikTokConnection/ - TikTok connection management
- services/
  - api.js - API calls to backend
  - websocket.js - WebSocket management
  - tts.js - TTS queue and speech synthesis
- utils/
  - constants.js - App constants
  - helpers.js - Utility functions

## Benefits
- Better separation of concerns
- Easier testing and maintenance
- Reusable components
- Cleaner code organization