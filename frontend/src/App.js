import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Switch } from './components/ui/switch';
import { Separator } from './components/ui/separator';
import { ScrollArea } from './components/ui/scroll-area';
import { toast } from 'sonner';
import { 
  Radio, 
  RadioOff, 
  Volume2, 
  VolumeX, 
  Users, 
  MessageCircle, 
  Settings,
  Play,
  Pause,
  Wifi,
  WifiOff
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  // States
  const [isConnected, setIsConnected] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [username, setUsername] = useState('');
  const [currentUsername, setCurrentUsername] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [ttsQueueLength, setTtsQueueLength] = useState(0);
  const [isProcessingTTSState, setIsProcessingTTSState] = useState(false);
  
  // Constants
  const MAX_MESSAGES = 100; // Límite de mensajes para optimizar rendimiento
  const MAX_TTS_QUEUE = 1; // Máximo 1 mensaje en cola (más el que se está reproduciendo) para evitar retrasos
  
  // Refs
  const wsRef = useRef(null);
  const scrollAreaRef = useRef(null);
  const shouldAutoScroll = useRef(true);
  const ttsQueue = useRef([]);
  const isProcessingTTS = useRef(false);

  // Enhanced TTS Setup with Robust Error Handling and Browser API Fix
  const speak = async (text, user) => {
    if (!ttsEnabled || !window.speechSynthesis) return;
    
    // Check if Speech Synthesis is available and working
    if (!window.speechSynthesis || window.speechSynthesis.speaking) {
      console.warn('⚠️ Speech Synthesis unavailable or already speaking');
      return;
    }

    const maxRetries = 2;
    let retryCount = 0;
    
    const attemptSpeak = () => {
      return new Promise((resolve) => {
        // Cancel any pending speech to prevent conflicts
        try {
          window.speechSynthesis.cancel();
          // Small delay to ensure cancellation completes
          setTimeout(() => {
            performSpeak(resolve);
          }, 100);
        } catch (e) {
          console.warn('Error cancelling speech:', e);
          performSpeak(resolve);
        }
      });
    };

    const performSpeak = (resolve) => {
      const utterance = new SpeechSynthesisUtterance(`${user} dice: ${text}`);
      utterance.lang = 'es-ES';
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.8;
      
      // Enhanced voice selection with better fallbacks
      const loadVoicesAndSpeak = () => {
        const voices = window.speechSynthesis.getVoices();
        console.log(`🔍 Available voices: ${voices.length}`);
        
        // Try multiple Spanish voice patterns
        const spanishVoice = voices.find(voice => 
          voice.lang.includes('es-ES') || 
          voice.lang.includes('es-MX') || 
          voice.lang.includes('es') ||
          voice.name.toLowerCase().includes('spanish') ||
          voice.name.toLowerCase().includes('español')
        );
        
        if (spanishVoice) {
          utterance.voice = spanishVoice;
          console.log(`🎯 Selected voice: ${spanishVoice.name} (${spanishVoice.lang})`);
        } else {
          console.warn('⚠️ No Spanish voice found, using default');
        }
        
        initiateSpeak(resolve);
      };

      // Load voices if not already loaded
      if (window.speechSynthesis.getVoices().length === 0) {
        window.speechSynthesis.addEventListener('voiceschanged', loadVoicesAndSpeak, { once: true });
        // Fallback if voiceschanged doesn't fire
        setTimeout(loadVoicesAndSpeak, 100);
      } else {
        loadVoicesAndSpeak();
      }
    };

    const initiateSpeak = (resolve) => {
      const utterance = new SpeechSynthesisUtterance(`${user} dice: ${text}`);
      utterance.lang = 'es-ES';
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.8;

      let hasResolved = false;
      let speechStarted = false;
      
      const handleSuccess = () => {
        if (!hasResolved) {
          hasResolved = true;
          console.log(`✅ TTS completed: "${text}" by ${user}`);
          resolve();
        }
      };
      
      const handleError = (error) => {
        if (!hasResolved) {
          hasResolved = true;
          console.error(`❌ TTS error (attempt ${retryCount + 1}):`, error);
          
          // Retry logic for browser API failures
          if (retryCount < maxRetries && error.error !== 'interrupted') {
            retryCount++;
            console.log(`🔄 Retrying TTS (attempt ${retryCount + 1}/${maxRetries + 1})`);
            setTimeout(() => {
              attemptSpeak().then(resolve);
            }, 500);
          } else {
            console.warn('⚠️ TTS failed after retries, continuing...');
            resolve();
          }
        }
      };
      
      // Event handlers
      utterance.onstart = () => {
        speechStarted = true;
        console.log(`🎤 TTS started: "${text}" by ${user}`);
      };
      
      utterance.onend = handleSuccess;
      utterance.onerror = handleError;
      
      // Enhanced timeout with speech detection
      const timeout = setTimeout(() => {
        if (!hasResolved) {
          hasResolved = true;
          if (speechStarted) {
            console.log(`⏰ TTS timeout after speech started: "${text}" by ${user}`);
            resolve();
          } else {
            console.warn(`⏰ TTS timeout without speech start: "${text}" by ${user}`);
            handleError({ error: 'timeout' });
          }
        }
      }, Math.max(text.length * 100, 5000)); // Increased timeout
      
      try {
        console.log(`🎤 Initiating TTS: "${text}" by ${user} (attempt ${retryCount + 1})`);
        window.speechSynthesis.speak(utterance);
        
        // Clear timeout on successful completion
        utterance.addEventListener('end', () => {
          clearTimeout(timeout);
        });
        
      } catch (error) {
        clearTimeout(timeout);
        handleError(error);
      }
    };

    // Start the speaking process
    return await attemptSpeak();
  };

  // Smart TTS Queue Management - Maximum 2 messages (1 playing + 1 waiting)
  const addToTTSQueue = (text, user) => {
    if (!ttsEnabled) return;
    
    const messageData = { 
      text, 
      user, 
      timestamp: Date.now(),
      id: Date.now() + Math.random()
    };
    
    console.log(`📨 NEW MESSAGE RECEIVED: "${text}" by ${user} (ID: ${messageData.id})`);
    console.log(`📊 Current state - isProcessingTTS: ${isProcessingTTS.current}, queueLength: ${ttsQueue.current.length}`);
    
    if (isProcessingTTS.current) {
      // TTS is currently playing a message
      if (ttsQueue.current.length === 0) {
        // No message waiting, add this one to queue
        console.log(`🎤 TTS is playing, adding message to queue: "${text}" by ${user} (ID: ${messageData.id})`);
        ttsQueue.current = [messageData];
        setTtsQueueLength(1);
      } else {
        // There's already a message waiting, replace it with the latest one
        console.log(`🎤 TTS is playing and queue is full, replacing waiting message with latest: "${text}" by ${user} (ID: ${messageData.id})`);
        const oldMessage = ttsQueue.current[0];
        console.log(`🗑️ Removing old waiting message: "${oldMessage.text}" by ${oldMessage.user} (ID: ${oldMessage.id})`);
        ttsQueue.current = [messageData]; // Replace the waiting message
        setTtsQueueLength(1);
      }
    } else {
      // TTS is not processing, start immediately
      console.log(`🎤 Adding message to empty TTS queue and starting: "${text}" by ${user} (ID: ${messageData.id})`);
      ttsQueue.current = [messageData];
      setTtsQueueLength(1);
      processTTSQueue();
    }
  };

  const processTTSQueue = async () => {
    // Prevent multiple concurrent processing
    if (isProcessingTTS.current) {
      console.log('🎤 TTS queue already processing, skipping...');
      return;
    }
    
    if (ttsQueue.current.length === 0) {
      console.log('🎤 TTS queue is empty');
      setIsProcessingTTSState(false);
      return;
    }
    
    console.log(`🎤 Starting TTS processing with ${ttsQueue.current.length} message(s)`);
    console.log(`📋 Queue contents:`, ttsQueue.current.map(m => `"${m.text}" by ${m.user} (ID: ${m.id})`));
    
    isProcessingTTS.current = true;
    setIsProcessingTTSState(true);
    
    try {
      while (ttsQueue.current.length > 0 && ttsEnabled) {
        // Take the first message from queue (FIFO - First In, First Out) 
        const message = ttsQueue.current.shift();
        setTtsQueueLength(ttsQueue.current.length);
        
        console.log(`🎤 Processing TTS message ${message.id}: "${message.text}" by ${message.user}`);
        console.log(`📊 Queue after shift - remaining messages: ${ttsQueue.current.length}`);
        
        try {
          // Wait for the current message to complete FULLY before proceeding
          console.log(`⏳ Starting TTS for message ${message.id}...`);
          await speak(message.text, message.user);
          console.log(`✅ Completed TTS message ${message.id}: "${message.text}" by ${message.user}`);
          
          // Shorter pause after completion to improve responsiveness
          await new Promise(resolve => setTimeout(resolve, 200));
          
        } catch (error) {
          console.error(`❌ Error processing TTS message ${message.id}:`, error);
          // Continue with next message even if current one fails
        }
        
        // Check if TTS was disabled during processing
        if (!ttsEnabled) {
          console.log('🔇 TTS disabled during processing, stopping queue');
          break;
        }
        
        // Continue with next message in queue if available
        if (ttsQueue.current.length > 0) {
          console.log(`📬 ${ttsQueue.current.length} message(s) remaining in queue`);
          console.log(`📋 Remaining queue:`, ttsQueue.current.map(m => `"${m.text}" by ${m.user} (ID: ${m.id})`));
        }
      }
    } catch (error) {
      console.error('❌ Error in TTS queue processing:', error);
    } finally {
      isProcessingTTS.current = false;
      setIsProcessingTTSState(false);
      setTtsQueueLength(ttsQueue.current.length);
      console.log(`🏁 TTS processing finished. Remaining messages: ${ttsQueue.current.length}`);
      
      // If there are still messages and TTS is enabled, continue processing
      // This handles cases where new messages arrived while we were processing
      if (ttsQueue.current.length > 0 && ttsEnabled) {
        console.log('🔄 More messages in queue, continuing...');
        setTimeout(() => processTTSQueue(), 100); // Reduced delay for better responsiveness
      }
    }
  };

  // Enhanced Clear TTS queue when TTS is disabled
  const clearTTSQueue = () => {
    console.log('🧹 Clearing TTS queue and stopping all speech...');
    
    // Clear the queue
    ttsQueue.current = [];
    setTtsQueueLength(0);
    
    // Aggressive cancellation of any ongoing speech
    if (window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
        // Wait a bit and cancel again to ensure it's really stopped
        setTimeout(() => {
          if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            console.log('🧹 Secondary speech cancellation performed');
          }
        }, 100);
      } catch (error) {
        console.warn('Error cancelling speech synthesis:', error);
      }
    }
    
    // Reset processing flags
    isProcessingTTS.current = false;
    setIsProcessingTTSState(false);
    
    console.log('✅ TTS queue cleared and speech stopped');
  };

  // Enhanced TTS test function with better diagnostics
  const testTTS = async () => {
    if (!ttsEnabled) return;
    
    console.log('🧪 Testing TTS functionality...');
    
    // Clear any existing speech first
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    
    // Test message
    const testMessage = "¡Hola! Esto es una prueba del sistema TTS.";
    const testUser = "Sistema";
    
    try {
      await speak(testMessage, testUser);
      console.log('✅ TTS test completed successfully');
      toast.success('Prueba TTS completada');
    } catch (error) {
      console.error('❌ TTS test failed:', error);
      toast.error('Error en prueba TTS: ' + error.message);
    }
  };

  // WebSocket Setup
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = BACKEND_URL.replace(/^https?:/, wsProtocol) + '/api/ws';
    
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket conectado');
      setConnectionStatus('websocket_connected');
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'chat_message':
          const newMessage = {
            id: Date.now() + Math.random(),
            user: data.user,
            message: data.message,
            timestamp: new Date(data.timestamp)
          };
          
          setChatMessages(prev => {
            const updated = [newMessage, ...prev];
            // Mantener solo los últimos MAX_MESSAGES mensajes
            return updated.slice(0, MAX_MESSAGES);
          });
          
          // TTS for new messages - add to queue instead of immediate playback
          if (data.tts_enabled && ttsEnabled) {
            addToTTSQueue(data.message, data.user);
          }
          break;
          
        case 'connection_status':
          setIsConnected(data.connected);
          if (data.connected) {
            setCurrentUsername(data.username);
            setConnectionStatus('tiktok_connected');
            toast.success(`Conectado a @${data.username}`);
          } else {
            setCurrentUsername('');
            setConnectionStatus('disconnected');
            if (data.error) {
              toast.error(`Error: ${data.error}`);
            } else {
              toast.info('Desconectado de TikTok Live');
            }
          }
          break;
          
        case 'tts_status':
          setTtsEnabled(data.enabled);
          toast.info(`TTS ${data.enabled ? 'activado' : 'desactivado'}`);
          break;
      }
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket desconectado');
      setConnectionStatus('disconnected');
      // Reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      toast.error('Error de conexión WebSocket');
    };
  };

  // API Functions
  const connectToTikTok = async () => {
    if (!username.trim()) {
      toast.error('Por favor ingresa un nombre de usuario');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: username.trim() }),
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error al conectar');
      }
    } catch (error) {
      toast.error('Error de conexión al servidor');
      console.error('Connection error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const disconnectFromTikTok = async (force = false) => {
    setIsLoading(true);
    try {
      const endpoint = force ? '/api/force-disconnect' : '/api/disconnect';
      const response = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
        setChatMessages([]);
        clearTTSQueue(); // Clear TTS queue on disconnect
      } else {
        toast.error('Error al desconectar');
      }
    } catch (error) {
      toast.error('Error de conexión al servidor');
      console.error('Disconnect error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Enhanced TTS toggle function
  const toggleTTS = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/toggle-tts`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        const newTTSState = data.tts_enabled;
        
        // If TTS is being disabled, clear the queue and stop current speech
        if (!newTTSState) {
          clearTTSQueue();
          toast.info('TTS desactivado - Cola de mensajes limpiada');
        } else {
          toast.info('TTS activado');
        }
      } else {
        toast.error('Error al cambiar TTS');
      }
    } catch (error) {
      toast.error('Error de conexión al servidor');
      console.error('TTS toggle error:', error);
    }
  };

  const testTTS = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'test_message'
      }));
    } else {
      toast.error('WebSocket no conectado');
    }
  };

  // Effects
  useEffect(() => {
    connectWebSocket();
    
    // Load available voices
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Auto-scroll functionality
  const scrollToBottom = () => {
    if (scrollAreaRef.current && shouldAutoScroll.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        setTimeout(() => {
          scrollElement.scrollTo({
            top: scrollElement.scrollHeight,
            behavior: 'smooth'
          });
        }, 100);
      }
    }
  };

  // Detectar cuando el usuario scrollea manualmente
  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    const isAtBottom = scrollHeight - scrollTop === clientHeight;
    
    // Si el usuario scrollea manualmente lejos del bottom, pausar auto-scroll
    if (scrollTop < scrollHeight - clientHeight - 50 && shouldAutoScroll.current) {
      shouldAutoScroll.current = false;
    }
    // Si el usuario scrollea de vuelta al bottom, reactivar auto-scroll
    else if (isAtBottom && !shouldAutoScroll.current) {
      shouldAutoScroll.current = true;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  useEffect(() => {
    const scrollElement = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollElement) {
      scrollElement.addEventListener('scroll', handleScroll);
      return () => scrollElement.removeEventListener('scroll', handleScroll);
    }
  }, [chatMessages.length]);

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'tiktok_connected':
        return <Radio className="w-4 h-4 text-green-500" />;
      case 'websocket_connected':
        return <Wifi className="w-4 h-4 text-blue-500" />;
      default:
        return <WifiOff className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    if (isConnected && currentUsername) {
      return `Conectado a @${currentUsername}`;
    }
    switch (connectionStatus) {
      case 'websocket_connected':
        return 'WebSocket conectado';
      case 'disconnected':
        return 'Desconectado';
      default:
        return 'Conectando...';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-purple-600 rounded-xl flex items-center justify-center">
                <MessageCircle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">TikTok Live TTS</h1>
                <p className="text-sm text-gray-300">Bot de voz para transmisiones en vivo</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Badge variant={isConnected ? "default" : "secondary"} className="flex items-center space-x-2">
                {getConnectionIcon()}
                <span className="text-xs">{getStatusText()}</span>
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Control Panel */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* Connection Card */}
            <Card className="bg-black/40 backdrop-blur-sm border-white/10">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <Settings className="w-5 h-5" />
                  <span>Configuración</span>
                </CardTitle>
                <CardDescription className="text-gray-300">
                  Conecta tu cuenta de TikTok Live
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-200">Usuario de TikTok</label>
                  <Input
                    placeholder="@usuario"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="bg-white/10 border-white/20 text-white placeholder-gray-400"
                    disabled={isConnected || isLoading}
                  />
                </div>
                
                <div className="flex space-x-2">
                  {!isConnected ? (
                    <Button 
                      onClick={connectToTikTok}
                      disabled={isLoading || !username.trim()}
                      className="flex-1 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700"
                    >
                      {isLoading ? (
                        <>
                          <div className="w-4 h-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2" />
                          Conectando...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-2" />
                          Conectar
                        </>
                      )}
                    </Button>
                  ) : (
                    <div className="flex space-x-2 w-full">
                      <Button 
                        onClick={() => disconnectFromTikTok(false)}
                        disabled={isLoading}
                        variant="destructive"
                        className="flex-1"
                      >
                        {isLoading ? (
                          <>
                            <div className="w-4 h-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2" />
                            Desconectando...
                          </>
                        ) : (
                          <>
                            <Pause className="w-4 h-4 mr-2" />
                            Desconectar
                          </>
                        )}
                      </Button>
                      
                      <Button 
                        onClick={() => disconnectFromTikTok(true)}
                        disabled={isLoading}
                        variant="outline"
                        size="sm"
                        className="border-red-500 text-red-500 hover:bg-red-500 hover:text-white"
                        title="Desconexión forzada si la normal no funciona"
                      >
                        ⚡
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* TTS Controls */}
            <Card className="bg-black/40 backdrop-blur-sm border-white/10">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  {ttsEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                  <span>Control de Voz</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-200">TTS Activado</span>
                  <Switch
                    checked={ttsEnabled}
                    onCheckedChange={toggleTTS}
                  />
                </div>
                
                <Separator className="bg-white/10" />
                
                <Button 
                  onClick={testTTS}
                  variant="outline"
                  className="w-full border-white/20 text-white hover:bg-white/10"
                  disabled={!ttsEnabled}
                >
                  <Volume2 className="w-4 h-4 mr-2" />
                  Probar TTS
                </Button>
              </CardContent>
            </Card>

            {/* Stats Card */}
            <Card className="bg-black/40 backdrop-blur-sm border-white/10">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <Users className="w-5 h-5" />
                  <span>Estadísticas</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">{chatMessages.length}</div>
                    <div className="text-xs text-gray-300">Mensajes</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">
                      {isConnected ? '1' : '0'}
                    </div>
                    <div className="text-xs text-gray-300">Conexiones</div>
                  </div>
                </div>
                
                {/* TTS Queue Status & Diagnostics */}
                {ttsEnabled && (
                  <div className="mt-4 pt-4 border-t border-white/10">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-300">Cola TTS:</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-medium">{ttsQueueLength}</span>
                        {isProcessingTTSState && (
                          <div className="w-3 h-3 animate-pulse bg-green-500 rounded-full" title="Procesando TTS"></div>
                        )}
                      </div>
                    </div>
                    
                    {/* TTS Queue Progress Bar */}
                    {ttsQueueLength > 0 && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-700 rounded-full h-1.5">
                          <div 
                            className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${Math.min((ttsQueueLength / MAX_TTS_QUEUE) * 100, 100)}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {isProcessingTTSState ? 'Reproduciendo mensaje...' : 'Mensaje en espera'}
                        </div>
                      </div>
                    )}
                    
                    {/* TTS Diagnostics */}
                    <div className="mt-3 space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Estado:</span>
                        <span className={`${isProcessingTTSState ? 'text-green-400' : 'text-gray-400'}`}>
                          {isProcessingTTSState ? '🔊 Activo' : '⏸️ Inactivo'}
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">API Speech:</span>
                        <span className={`${window.speechSynthesis ? 'text-green-400' : 'text-red-400'}`}>
                          {window.speechSynthesis ? '✅ Disponible' : '❌ No disponible'}
                        </span>
                      </div>
                      
                      {window.speechSynthesis && (
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-400">Voces ES:</span>
                          <span className="text-blue-400">
                            {window.speechSynthesis.getVoices().filter(v => v.lang.includes('es')).length} voces
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Chat Display */}
          <div className="lg:col-span-2">
            <Card className="bg-black/40 backdrop-blur-sm border-white/10 h-[600px] flex flex-col">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white flex items-center space-x-2">
                      <MessageCircle className="w-5 h-5" />
                      <span>Chat en Vivo</span>
                      {isConnected && (
                        <Badge variant="default" className="ml-2">
                          @{currentUsername}
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="text-gray-300">
                      Mensajes en tiempo real de TikTok Live {chatMessages.length > 0 && `(${chatMessages.length} mensajes)`}
                    </CardDescription>
                  </div>
                  
                  {chatMessages.length > 5 && (
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          shouldAutoScroll.current = !shouldAutoScroll.current;
                          if (shouldAutoScroll.current) {
                            scrollToBottom();
                          }
                        }}
                        className="border-white/20 text-white hover:bg-white/10 text-xs"
                      >
                        {shouldAutoScroll.current ? '⏸️ Pausar scroll' : '▶️ Auto scroll'}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setChatMessages([])}
                        className="border-white/20 text-white hover:bg-white/10 text-xs"
                      >
                        🗑️ Limpiar
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              
              <CardContent className="flex-1 overflow-hidden p-0">
                <ScrollArea ref={scrollAreaRef} className="h-full px-6 pb-4">
                  {chatMessages.length === 0 ? (
                    <div className="flex items-center justify-center h-[400px] text-gray-400">
                      <div className="text-center">
                        <MessageCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No hay mensajes aún</p>
                        <p className="text-sm">Conecta a un live de TikTok para ver mensajes</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3 py-2">
                      {chatMessages.slice().reverse().map((msg, index) => (
                        <div 
                          key={msg.id}
                          className="bg-white/5 rounded-lg p-3 border border-white/10 hover:bg-white/10 transition-colors animate-in slide-in-from-bottom-2 duration-300"
                          style={{ animationDelay: `${index * 50}ms` }}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-pink-400 text-sm">@{msg.user}</span>
                              <div className="w-1 h-1 bg-gray-500 rounded-full" />
                              <span className="text-xs text-gray-400">
                                {msg.timestamp?.toLocaleTimeString('es-ES', { 
                                  hour: '2-digit', 
                                  minute: '2-digit',
                                  second: '2-digit'
                                })}
                              </span>
                            </div>
                            <Badge variant="outline" className="text-xs px-2 py-0 border-white/20 text-gray-300">
                              #{chatMessages.length - index}
                            </Badge>
                          </div>
                          <p className="text-white text-sm leading-relaxed break-words">{msg.message}</p>
                        </div>
                      ))}
                      {chatMessages.length >= MAX_MESSAGES && (
                        <div className="text-center py-4">
                          <p className="text-xs text-gray-500">
                            Mostrando los últimos {MAX_MESSAGES} mensajes
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-black/20 backdrop-blur-sm border-t border-white/10 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="text-center text-gray-300 text-sm">
            <p>🎤 Bot TTS para TikTok Live - Escucha los mensajes en voz alta</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;