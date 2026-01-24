import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Mic, Square, Loader2, X, Volume2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function VoiceRecorder({ onTranscriptionComplete, onClose }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [transcriptionResult, setTranscriptionResult] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      toast.error('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const transcribeAudio = async () => {
    if (!audioBlob) return;
    
    setIsTranscribing(true);
    
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      
      const response = await axios.post(
        `${BACKEND_URL}/api/ai/transcribe`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      setTranscriptionResult(response.data);
      toast.success('Audio transcribed successfully!');
      
    } catch (error) {
      console.error('Error transcribing audio:', error);
      toast.error('Failed to transcribe audio. Please try again.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const useTranscription = () => {
    if (transcriptionResult && onTranscriptionComplete) {
      onTranscriptionComplete(transcriptionResult);
    }
  };

  const resetRecording = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    setTranscriptionResult(null);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm"
      data-testid="voice-recorder-modal"
    >
      <div className="executive-card p-8 w-full max-w-lg relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors"
          data-testid="close-voice-recorder"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="text-center mb-6">
          <h3 className="text-2xl font-semibold text-slate-50 mb-2">Voice Grievance</h3>
          <p className="text-slate-400 text-sm">Record your grievance in any Indian language</p>
        </div>

        {/* Recording Interface */}
        <div className="flex flex-col items-center space-y-6">
          {/* Microphone Button */}
          <div className="relative">
            <AnimatePresence>
              {isRecording && (
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1.5, opacity: 0.3 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ repeat: Infinity, duration: 1, repeatType: 'reverse' }}
                  className="absolute inset-0 bg-rose-500 rounded-full"
                />
              )}
            </AnimatePresence>
            
            {!audioBlob ? (
              <Button
                onClick={isRecording ? stopRecording : startRecording}
                data-testid={isRecording ? "stop-recording-btn" : "start-recording-btn"}
                className={`relative z-10 h-24 w-24 rounded-full ${
                  isRecording 
                    ? 'bg-rose-500 hover:bg-rose-600' 
                    : 'bg-orange-500 hover:bg-orange-600'
                } text-white shadow-lg`}
              >
                {isRecording ? (
                  <Square className="h-8 w-8" />
                ) : (
                  <Mic className="h-8 w-8" />
                )}
              </Button>
            ) : (
              <div className="flex items-center gap-4">
                <Button
                  onClick={resetRecording}
                  data-testid="reset-recording-btn"
                  className="bg-slate-700 hover:bg-slate-600 text-white rounded-full px-6"
                >
                  Record Again
                </Button>
              </div>
            )}
          </div>

          {/* Recording Time */}
          {isRecording && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center"
            >
              <p className="text-3xl font-mono text-rose-400">{formatTime(recordingTime)}</p>
              <p className="text-sm text-slate-400 mt-1">Recording...</p>
            </motion.div>
          )}

          {/* Audio Playback */}
          {audioUrl && !isRecording && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full space-y-4"
            >
              <div className="flex items-center gap-3 p-4 bg-slate-950 rounded-xl border border-slate-800">
                <Volume2 className="h-5 w-5 text-orange-500" />
                <audio 
                  src={audioUrl} 
                  controls 
                  className="flex-1 h-8"
                  data-testid="audio-playback"
                />
                <span className="text-sm text-slate-400">{formatTime(recordingTime)}</span>
              </div>

              {/* Transcribe Button */}
              {!transcriptionResult && (
                <Button
                  onClick={transcribeAudio}
                  disabled={isTranscribing}
                  data-testid="transcribe-btn"
                  className="w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full h-12"
                >
                  {isTranscribing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Transcribing with AI...
                    </>
                  ) : (
                    'Transcribe Audio'
                  )}
                </Button>
              )}
            </motion.div>
          )}

          {/* Transcription Result */}
          {transcriptionResult && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full space-y-4"
              data-testid="transcription-result"
            >
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                <div>
                  <span className="text-xs uppercase tracking-wider text-orange-500">Language Detected</span>
                  <p className="text-slate-200 font-medium">{transcriptionResult.language_detected}</p>
                </div>
                
                <div>
                  <span className="text-xs uppercase tracking-wider text-orange-500">Original Text</span>
                  <p className="text-slate-200">{transcriptionResult.original}</p>
                </div>
                
                {transcriptionResult.language_detected !== 'English' && (
                  <div>
                    <span className="text-xs uppercase tracking-wider text-orange-500">English Translation</span>
                    <p className="text-slate-200">{transcriptionResult.english_translation}</p>
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={useTranscription}
                  data-testid="use-transcription-btn"
                  className="flex-1 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full h-12"
                >
                  Use This Grievance
                </Button>
                <Button
                  onClick={resetRecording}
                  data-testid="record-again-btn"
                  className="bg-slate-700 hover:bg-slate-600 text-white rounded-full px-6 h-12"
                >
                  Record Again
                </Button>
              </div>
            </motion.div>
          )}

          {/* Language Support Info */}
          <div className="text-center text-xs text-slate-500 mt-4">
            <p>Supports: Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, and more</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
