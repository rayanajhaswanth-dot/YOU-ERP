import React, { useState } from 'react';
import { Sparkles, Send, Edit3, X, MessageCircle, Facebook, Twitter } from 'lucide-react';

const BroadcastWidget = () => {
  const [topic, setTopic] = useState('');
  const [isDrafting, setIsDrafting] = useState(false);
  const [drafts, setDrafts] = useState(null); // null = no drafts yet
  const [status, setStatus] = useState('IDLE'); // IDLE, DRAFTING, READY, POSTED
  const [isExpanded, setIsExpanded] = useState(false); // COLLAPSIBLE STATE

  const handleDraft = async () => {
    if (!topic.trim()) return;
    
    setIsDrafting(true);
    setStatus('DRAFTING');

    try {
      // Call the Mock AI Endpoint we created in dashboard_routes.py
      const response = await fetch('/api/dashboard/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_topic: topic })
      });

      if (!response.ok) throw new Error("Drafting failed");
      
      const data = await response.json();
      setDrafts(data);
      setStatus('READY');
    } catch (err) {
      console.error("Drafting Error:", err);
      // Fallback for simulation if backend is unreachable
      setDrafts({
        twitter: `🚨 UPDATE: ${topic}. We are committed to immediate action! #ConstituencyFirst`,
        whatsapp: `🙏 Namaste. Important update regarding: ${topic}. Your Sevak, [Leader Name].`,
        facebook: `OFFICIAL STATEMENT: We have taken note of ${topic} and are working on it.`
      });
      setStatus('READY');
    } finally {
      setIsDrafting(false);
    }
  };

  const handlePost = (platform) => {
    // In a real app, this would hit an API. For MVP, we simulate success.
    alert(`Published to ${platform} successfully!`);
  };

  const resetWidget = () => {
      setStatus('IDLE');
      setDrafts(null);
      setTopic('');
      setIsExpanded(false);
  };

  // --- COMPACT VIEW (Default) ---
  if (!isExpanded) {
      return (
        <div 
            onClick={() => setIsExpanded(true)}
            className="bg-[#1F2937] p-4 rounded-xl shadow-lg border border-gray-700 w-full mb-8 cursor-pointer hover:border-[#FF9933] transition-all group flex items-center gap-4"
        >
            <div className="bg-[#111827] p-2 rounded-full border border-gray-700 group-hover:border-[#FF9933]">
                <Edit3 className="text-[#FF9933]" size={20} />
            </div>
            <span className="text-gray-400 font-medium text-lg">
                Start a quick broadcast...
            </span>
        </div>
      );
  }

  // --- EXPANDED VIEW ---
  return (
    <div className="bg-[#1F2937] p-6 rounded-xl shadow-lg border border-gray-700 w-full mb-8 relative animate-in fade-in zoom-in-95 duration-200">
      
      {/* CLOSE BUTTON */}
      <button 
        onClick={resetWidget}
        className="absolute top-4 right-4 text-gray-500 hover:text-white"
      >
        <X size={20} />
      </button>

      {/* HEADER */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
          <Sparkles className="text-[#FF9933]" size={20} />
          Broadcast Center
        </h2>
        <span className="text-xs text-gray-500 uppercase tracking-widest font-semibold pr-8">AI Drafter Active</span>
      </div>

      {/* INPUT AREA */}
      <div className="relative">
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What would you like to announce today? (e.g., 'Inaugurated new road in Ward 4')"
          className="w-full bg-[#111827] text-white rounded-lg p-4 min-h-[100px] border border-gray-700 focus:border-[#FF9933] focus:ring-1 focus:ring-[#FF9933] outline-none transition-all resize-none"
          disabled={status === 'POSTED'}
          autoFocus
        />
        
        {/* ACTION BAR */}
        <div className="flex justify-end mt-3">
            {status === 'IDLE' || status === 'READY' ? (
                <button
                    onClick={handleDraft}
                    disabled={!topic.trim() || isDrafting}
                    className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all ${
                        !topic.trim() 
                        ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                        : 'bg-[#FF9933] text-black hover:bg-orange-400 hover:shadow-[0_0_10px_rgba(255,153,51,0.3)]'
                    }`}
                >
                    {isDrafting ? (
                        <>Processing...</>
                    ) : (
                        <><Sparkles size={18} /> Draft with AI</>
                    )}
                </button>
            ) : (
                <button 
                    onClick={() => { setStatus('IDLE'); setDrafts(null); setTopic(''); }}
                    className="text-gray-400 hover:text-white text-sm"
                >
                    Start New Post
                </button>
            )}
        </div>
      </div>

      {/* DRAFTS DISPLAY (Only shows after drafting) */}
      {status === 'READY' && drafts && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* TWITTER CARD */}
            <div className="bg-[#111827] p-4 rounded-lg border border-gray-800 hover:border-gray-600 transition-colors group">
                <div className="flex items-center gap-2 mb-3 text-blue-400">
                    <Twitter size={16} />
                    <span className="text-xs font-bold uppercase">Twitter / X</span>
                </div>
                <p className="text-gray-300 text-sm mb-4 leading-relaxed min-h-[60px]">
                    {drafts.twitter}
                </p>
                <button 
                    onClick={() => handlePost('Twitter')}
                    className="w-full py-2 bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded font-medium text-xs hover:bg-blue-500 hover:text-white transition-colors flex justify-center items-center gap-2"
                >
                    <Send size={12} /> Post Tweet
                </button>
            </div>

            {/* WHATSAPP CARD */}
            <div className="bg-[#111827] p-4 rounded-lg border border-gray-800 hover:border-gray-600 transition-colors group">
                <div className="flex items-center gap-2 mb-3 text-green-400">
                    <MessageCircle size={16} />
                    <span className="text-xs font-bold uppercase">WhatsApp</span>
                </div>
                <p className="text-gray-300 text-sm mb-4 leading-relaxed min-h-[60px]">
                    {drafts.whatsapp}
                </p>
                <button 
                    onClick={() => handlePost('WhatsApp')}
                    className="w-full py-2 bg-green-500/10 text-green-400 border border-green-500/30 rounded font-medium text-xs hover:bg-green-500 hover:text-white transition-colors flex justify-center items-center gap-2"
                >
                    <Send size={12} /> Blast to Groups
                </button>
            </div>

            {/* FACEBOOK CARD */}
            <div className="bg-[#111827] p-4 rounded-lg border border-gray-800 hover:border-gray-600 transition-colors group">
                <div className="flex items-center gap-2 mb-3 text-blue-600">
                    <Facebook size={16} />
                    <span className="text-xs font-bold uppercase">Facebook</span>
                </div>
                <p className="text-gray-300 text-sm mb-4 leading-relaxed min-h-[60px]">
                    {drafts.facebook}
                </p>
                <button 
                    onClick={() => handlePost('Facebook')}
                    className="w-full py-2 bg-blue-600/10 text-blue-500 border border-blue-600/30 rounded font-medium text-xs hover:bg-blue-600 hover:text-white transition-colors flex justify-center items-center gap-2"
                >
                    <Send size={12} /> Share Update
                </button>
            </div>

        </div>
      )}
    </div>
  );
};

export default BroadcastWidget;
