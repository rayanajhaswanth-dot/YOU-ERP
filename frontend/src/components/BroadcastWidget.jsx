import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Megaphone, Twitter, Facebook, MessageCircle, Sparkles, Loader2, Send } from "lucide-react";
import { useToast } from "../hooks/use-toast";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const BroadcastWidget = () => {
  const [topic, setTopic] = useState('');
  const [tone, setTone] = useState('professional');
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [drafts, setDrafts] = useState(null);
  const { toast } = useToast();

  // --- STEP 6 LOGIC: AI CONTENT GENERATION ---
  const handleGenerate = async () => {
    if (!topic) return;
    setLoading(true);
    setDrafts(null);

    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${BACKEND_URL}/api/dashboard/draft`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ topic, tone }),
      });

      if (!response.ok) throw new Error("AI Generation failed");

      const data = await response.json();
      setDrafts(data);
      toast({
        title: "Drafts Generated",
        description: "Review and edit before posting.",
      });
    } catch (error) {
      console.error(error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Could not generate drafts. Is the Backend running?",
      });
    } finally {
      setLoading(false);
    }
  };

  // --- STEP 7 LOGIC: META/TWITTER PUBLISHING ---
  const handlePost = async (platform, content) => {
    const encodedText = encodeURIComponent(content);

    // 1. Client-Side Intent Links (Twitter/WhatsApp) - "Zero Touch" implementation
    if (platform === 'twitter') {
        window.open(`https://twitter.com/intent/tweet?text=${encodedText}`, '_blank');
        toast({
          title: "Opening Twitter",
          description: "Complete the post in the new window.",
        });
        return;
    }
    if (platform === 'whatsapp') {
        window.open(`https://wa.me/?text=${encodedText}`, '_blank');
        toast({
          title: "Opening WhatsApp",
          description: "Select contacts to share with.",
        });
        return;
    }

    // 2. Server-Side API Call (Facebook) - Direct Graph API
    if (platform === 'facebook') {
        setPublishing(true);
        try {
            const token = localStorage.getItem('token');
            
            // Call the Step 7 Backend Endpoint
            const response = await fetch(`${BACKEND_URL}/api/broadcast/publish`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ content, platform: 'facebook' })
            });

            if (!response.ok) {
                // Handle specific backend errors
                if (response.status === 503) throw new Error("Credentials Missing");
                throw new Error("API Error");
            }
            
            toast({
                title: "Published!",
                description: "Successfully posted to Facebook Page.",
                className: "bg-green-600 border-none text-white"
            });

        } catch (error) {
            // --- FALLBACK: Manual Clipboard Copy ---
            console.warn("API Post failed, falling back to clipboard:", error);
            navigator.clipboard.writeText(content);
            window.open("https://facebook.com", '_blank');
            
            toast({
                title: error.message === "Credentials Missing" ? "Setup Required" : "Copied to Clipboard",
                description: "API keys missing. Opening Facebook for manual paste.",
            });
        } finally {
            setPublishing(false);
        }
    }
  };

  return (
    <Card className="col-span-1 border-orange-500/20 bg-slate-900/50 backdrop-blur h-[400px] flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
          <Megaphone className="h-5 w-5 text-orange-500" />
          Broadcast Center
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4 pr-2">
        {/* Input Section */}
        <div className="space-y-3">
          <Textarea 
            placeholder="What needs to be communicated? (e.g. 'Road work in Ward 5 completed')" 
            className="bg-slate-950 border-slate-800 text-white min-h-[80px]"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            data-testid="broadcast-topic-input"
          />
          <div className="flex gap-2">
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger className="w-[140px] bg-slate-950 border-slate-800 text-white" data-testid="broadcast-tone-select">
                <SelectValue placeholder="Tone" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
                <SelectItem value="empathetic">Empathetic</SelectItem>
                <SelectItem value="political">Political</SelectItem>
              </SelectContent>
            </Select>
            <Button 
              className="flex-1 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white"
              onClick={handleGenerate}
              disabled={loading || !topic}
              data-testid="broadcast-generate-btn"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
              {loading ? "Drafting..." : "Generate with AI"}
            </Button>
          </div>
        </div>

        {/* Drafts Section */}
        {drafts && (
          <div className="space-y-4 pt-2 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Twitter Draft */}
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950">
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2 text-sky-500 font-medium text-sm">
                  <Twitter className="h-4 w-4" /> Twitter (X)
                </div>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  className="h-6 text-xs text-sky-500 hover:text-sky-400 hover:bg-sky-950"
                  onClick={() => handlePost('twitter', drafts.twitter)}
                  data-testid="post-twitter-btn"
                >
                  <Send className="h-3 w-3 mr-1" /> Post
                </Button>
              </div>
              <Textarea 
                value={drafts.twitter} 
                onChange={(e) => setDrafts({...drafts, twitter: e.target.value})}
                className="text-xs bg-transparent border-none p-0 h-auto resize-none focus-visible:ring-0 text-slate-300"
              />
            </div>

            {/* WhatsApp Draft */}
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950">
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2 text-green-500 font-medium text-sm">
                  <MessageCircle className="h-4 w-4" /> WhatsApp
                </div>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  className="h-6 text-xs text-green-500 hover:text-green-400 hover:bg-green-950"
                  onClick={() => handlePost('whatsapp', drafts.whatsapp)}
                  data-testid="post-whatsapp-btn"
                >
                  <Send className="h-3 w-3 mr-1" /> Send
                </Button>
              </div>
              <Textarea 
                value={drafts.whatsapp} 
                onChange={(e) => setDrafts({...drafts, whatsapp: e.target.value})}
                className="text-xs bg-transparent border-none p-0 h-auto resize-none focus-visible:ring-0 text-slate-300"
              />
            </div>
            
             {/* Facebook Draft */}
             <div className="p-3 rounded-lg border border-slate-800 bg-slate-950">
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2 text-blue-500 font-medium text-sm">
                  <Facebook className="h-4 w-4" /> Facebook
                </div>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  className="h-6 text-xs text-blue-500 hover:text-blue-400 hover:bg-blue-950"
                  onClick={() => handlePost('facebook', drafts.facebook)}
                  disabled={publishing}
                  data-testid="post-facebook-btn"
                >
                  {publishing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3 mr-1" />}
                  {publishing ? "Posting..." : "Post Now"}
                </Button>
              </div>
              <Textarea 
                value={drafts.facebook} 
                onChange={(e) => setDrafts({...drafts, facebook: e.target.value})}
                className="text-xs bg-transparent border-none p-0 h-auto resize-none focus-visible:ring-0 text-slate-300"
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default BroadcastWidget;
