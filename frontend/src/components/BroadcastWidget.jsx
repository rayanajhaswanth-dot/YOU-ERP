import React, { useState } from 'react';
import { Sparkles, Twitter, MessageCircle, Facebook, Loader2, Copy, Check } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function BroadcastWidget() {
  const [topic, setTopic] = useState('');
  const [drafts, setDrafts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(null);

  const handleDraft = async () => {
    if (!topic.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/dashboard/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_topic: topic })
      });
      
      if (response.ok) {
        const data = await response.json();
        setDrafts(data);
      }
    } catch (error) {
      console.error('Error drafting post:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, platform) => {
    navigator.clipboard.writeText(text);
    setCopied(platform);
    setTimeout(() => setCopied(null), 2000);
  };

  const platformIcons = {
    twitter: Twitter,
    whatsapp: MessageCircle,
    facebook: Facebook
  };

  const platformColors = {
    twitter: 'text-sky-400',
    whatsapp: 'text-green-400',
    facebook: 'text-blue-400'
  };

  return (
    <div 
      className="bg-[#1F2937] p-5 rounded-xl shadow-lg border border-gray-700"
      data-testid="broadcast-widget"
    >
      <h3 className="text-lg font-bold text-gray-200 mb-4 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[#FF9933]" />
        Quick Broadcast
      </h3>
      
      {/* Input Area */}
      <textarea
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Share an official update..."
        className="w-full bg-gray-900 text-white rounded-lg p-4 min-h-[100px] border-none focus:ring-1 focus:ring-[#FF9933] text-lg resize-none outline-none"
        data-testid="broadcast-input"
      />
      
      {/* Action Footer */}
      <div className="flex items-center justify-between mt-4">
        <div className="flex gap-2">
          <span className="text-xs text-gray-500">Platforms:</span>
          <Twitter className="h-4 w-4 text-gray-500" />
          <MessageCircle className="h-4 w-4 text-gray-500" />
          <Facebook className="h-4 w-4 text-gray-500" />
        </div>
        
        <button
          onClick={handleDraft}
          disabled={loading || !topic.trim()}
          className="flex items-center gap-2 bg-[#FF9933] text-black font-bold px-6 py-2 rounded-lg hover:bg-orange-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="draft-button"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          Draft with AI
        </button>
      </div>

      {/* AI Generated Drafts */}
      {drafts && (
        <div className="mt-6 space-y-3" data-testid="draft-results">
          <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            AI-Generated Drafts
          </h4>
          
          {Object.entries(drafts).map(([platform, text]) => {
            const Icon = platformIcons[platform];
            return (
              <div 
                key={platform}
                className="bg-gray-900 rounded-lg p-4 border border-gray-800"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${platformColors[platform]}`} />
                    <span className="text-xs font-semibold text-gray-400 uppercase">
                      {platform}
                    </span>
                  </div>
                  <button
                    onClick={() => copyToClipboard(text, platform)}
                    className="text-gray-500 hover:text-white transition"
                  >
                    {copied === platform ? (
                      <Check className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <p className="text-gray-300 text-sm">{text}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
