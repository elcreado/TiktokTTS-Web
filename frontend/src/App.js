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
  
  // Constants
  const MAX_MESSAGES = 100; // Límite de mensajes para optimizar rendimiento
  
  // Refs
  const wsRef = useRef(null);
  const scrollAreaRef = useRef(null);
  const shouldAutoScroll = useRef(true);

  // TTS Setup
  const speak = (text, user) => {
    if (!ttsEnabled || !window.speechSynthesis) return;
    
    window.speechSynthesis.cancel(); // Cancel any ongoing speech
    
    const utterance = new SpeechSynthesisUtterance(`${user} dice: ${text}`);
    utterance.lang = 'es-ES'; // Spanish language
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.volume = 0.8;
    
    // Get available voices and prefer Spanish ones
    const voices = window.speechSynthesis.getVoices();
    const spanishVoice = voices.find(voice => 
      voice.lang.includes('es') || voice.name.includes('Spanish')
    );
    
    if (spanishVoice) {
      utterance.voice = spanishVoice;
    }
    
    window.speechSynthesis.speak(utterance);
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
          
          setChatMessages(prev => [newMessage, ...prev]);
          
          // TTS for new messages
          if (data.tts_enabled && ttsEnabled) {
            speak(data.message, data.user);
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

  const disconnectFromTikTok = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/disconnect`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
        setChatMessages([]);
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

  const toggleTTS = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/toggle-tts`, {
        method: 'POST',
      });

      if (!response.ok) {
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

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

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
                    <Button 
                      onClick={disconnectFromTikTok}
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
              </CardContent>
            </Card>
          </div>

          {/* Chat Display */}
          <div className="lg:col-span-2">
            <Card className="bg-black/40 backdrop-blur-sm border-white/10 h-[600px] flex flex-col">
              <CardHeader className="pb-4">
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
              </CardHeader>
              
              <CardContent className="flex-1 overflow-hidden p-0">
                <ScrollArea className="h-full px-6 pb-4">
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