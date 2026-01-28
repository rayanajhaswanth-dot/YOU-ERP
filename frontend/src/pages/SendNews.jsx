import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Input } from "../components/ui/input";
import { Checkbox } from "../components/ui/checkbox";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Megaphone, Sparkles, Loader2, Send, Image as ImageIcon, Instagram, Twitter, Facebook, MessageCircle, Copy } from "lucide-react";
import { useToast } from "../hooks/use-toast";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SendNews = () => {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [tone, setTone] = useState('professional');
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [image, setImage] = useState(null);
  const [aiOptions, setAiOptions] = useState(null);
  
  // Platform Selection State
  const [platforms, setPlatforms] = useState({
    facebook: false,
    twitter: false,
    whatsapp: false,
    instagram: false
  });

  const { toast } = useToast();

  const handleGenerate = async () => {
    if (!topic) return;
    setLoading(true);
    setAiOptions(null);

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
      setAiOptions(data);
      
      toast({ title: "AI Drafts Ready", description: "Select a version below to edit." });
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: "AI drafting failed." });
    } finally {
      setLoading(false);
    }
  };

  const applyDraft = (text) => {
    setContent(text);
    toast({ title: "Applied", description: "Draft copied to editor." });
  };

  const handleBroadcast = async () => {
    if (!content) return;
    if (!Object.values(platforms).some(p => p)) {
      toast({ variant: "destructive", title: "Select a Platform", description: "Choose at least one destination." });
      return;
    }

    setPublishing(true);
    const token = localStorage.getItem('token');

    // 1. FACEBOOK (API Post)
    if (platforms.facebook) {
      try {
        const formData = new FormData();
        formData.append('content', content);
        formData.append('platform', 'facebook');
        if (image) formData.append('image', image);

        const response = await fetch(`${BACKEND_URL}/api/posts/publish`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });

        if (!response.ok) {
          if (response.status === 503) {
            navigator.clipboard.writeText(content);
            window.open("https://facebook.com", '_blank');
            toast({ title: "Copied to Clipboard", description: "FB credentials missing. Paste manually." });
          } else {
            throw new Error("FB API Error");
          }
        } else {
          toast({ className: "bg-green-600 text-white border-none", title: "Facebook", description: "Published successfully." });
        }
      } catch (e) {
        navigator.clipboard.writeText(content);
        window.open("https://facebook.com", '_blank');
        toast({ title: "Copied to Clipboard", description: "Opening Facebook for manual posting." });
      }
    }

    // 2. TWITTER (Intent Link - 280 Char Limit)
    if (platforms.twitter) {
      const text = encodeURIComponent(content.substring(0, 280));
      window.open(`https://twitter.com/intent/tweet?text=${text}`, '_blank');
      toast({ title: "Opening Twitter", description: "Complete your post in the new window." });
    }

    // 3. WHATSAPP (Intent Link)
    if (platforms.whatsapp) {
      const text = encodeURIComponent(content);
      window.open(`https://wa.me/?text=${text}`, '_blank');
      toast({ title: "Opening WhatsApp", description: "Select contacts to share with." });
    }

    // 4. INSTAGRAM (Clipboard & Open)
    if (platforms.instagram) {
      navigator.clipboard.writeText(content);
      window.open("https://www.instagram.com/", '_blank');
      toast({ title: "Instagram", description: "Caption copied. Opening Instagram..." });
    }

    setPublishing(false);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Send News & Updates</h1>
        <p className="text-slate-400">The centralized broadcasting console for all channels.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* LEFT: Drafting Engine */}
        <Card className="md:col-span-2 border-orange-500/20 bg-slate-900/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Sparkles className="h-5 w-5 text-orange-500" /> Content Creator
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* AI Input Area */}
            <div className="space-y-2 p-4 border border-slate-800 rounded-lg bg-slate-950/30">
              <Label className="text-slate-300">Rough Draft / Topic / Greetings</Label>
              <div className="flex gap-2">
                <Input 
                  placeholder="E.g., 'Happy Diwali to all citizens' or 'Road work completed in Ward 5'" 
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="bg-slate-950 border-slate-800 text-white"
                  data-testid="news-topic-input"
                />
                 <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger className="w-[140px] bg-slate-950 border-slate-800 text-white" data-testid="news-tone-select">
                    <SelectValue placeholder="Tone" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="political">Political</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                    <SelectItem value="empathetic">Empathetic</SelectItem>
                    <SelectItem value="festive">Festive</SelectItem>
                  </SelectContent>
                </Select>
                <Button 
                  onClick={handleGenerate} 
                  disabled={loading || !topic} 
                  className="bg-orange-600 hover:bg-orange-700 text-white"
                  data-testid="news-draft-btn"
                >
                  {loading ? <Loader2 className="animate-spin" /> : "Refine with AI"}
                </Button>
              </div>
            </div>

            {/* AI Options Selection (Visible only after generation) */}
            {aiOptions && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 animate-in fade-in slide-in-from-top-2">
                  {/* Option 1: Twitter Style */}
                  <div 
                      onClick={() => applyDraft(aiOptions.twitter)}
                      className="cursor-pointer p-3 rounded border border-slate-800 bg-slate-950 hover:border-sky-500 hover:bg-sky-900/10 transition-colors group"
                      data-testid="ai-option-twitter"
                  >
                      <div className="flex items-center gap-2 text-sky-500 mb-2 font-bold text-xs uppercase">
                          <Twitter className="h-3 w-3" /> Short (Twitter)
                      </div>
                      <p className="text-xs text-slate-300 line-clamp-4">{aiOptions.twitter}</p>
                      <div className="mt-2 text-xs text-sky-500 opacity-0 group-hover:opacity-100 flex items-center gap-1">
                          <Copy className="h-3 w-3" /> Click to Apply
                      </div>
                  </div>

                  {/* Option 2: WhatsApp Style */}
                  <div 
                      onClick={() => applyDraft(aiOptions.whatsapp)}
                      className="cursor-pointer p-3 rounded border border-slate-800 bg-slate-950 hover:border-green-500 hover:bg-green-900/10 transition-colors group"
                      data-testid="ai-option-whatsapp"
                  >
                      <div className="flex items-center gap-2 text-green-500 mb-2 font-bold text-xs uppercase">
                          <MessageCircle className="h-3 w-3" /> Direct (WhatsApp)
                      </div>
                      <p className="text-xs text-slate-300 line-clamp-4">{aiOptions.whatsapp}</p>
                      <div className="mt-2 text-xs text-green-500 opacity-0 group-hover:opacity-100 flex items-center gap-1">
                          <Copy className="h-3 w-3" /> Click to Apply
                      </div>
                  </div>

                  {/* Option 3: Facebook Style */}
                  <div 
                      onClick={() => applyDraft(aiOptions.facebook)}
                      className="cursor-pointer p-3 rounded border border-slate-800 bg-slate-950 hover:border-blue-500 hover:bg-blue-900/10 transition-colors group"
                      data-testid="ai-option-facebook"
                  >
                      <div className="flex items-center gap-2 text-blue-500 mb-2 font-bold text-xs uppercase">
                          <Facebook className="h-3 w-3" /> Detailed (Facebook)
                      </div>
                      <p className="text-xs text-slate-300 line-clamp-4">{aiOptions.facebook}</p>
                      <div className="mt-2 text-xs text-blue-500 opacity-0 group-hover:opacity-100 flex items-center gap-1">
                          <Copy className="h-3 w-3" /> Click to Apply
                      </div>
                  </div>
              </div>
            )}

            <Label className="text-slate-300 mt-4 block">Final Post Content</Label>
            <Textarea 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="min-h-[150px] bg-slate-950 border-slate-800 text-white text-base focus:ring-orange-500"
              placeholder="Select an AI option above or type your own message..."
              data-testid="news-content-textarea"
            />

            <div className="flex items-center gap-4 p-4 border border-slate-800 rounded-lg bg-slate-950/50">
               <div className="bg-slate-800 p-2 rounded-full">
                  <ImageIcon className="h-6 w-6 text-slate-400" />
               </div>
               <div className="flex-1">
                 <Label htmlFor="image-upload" className="cursor-pointer text-sm font-medium text-slate-300 hover:text-orange-400">
                   {image ? image.name : "Upload Image / Reel (Optional)"}
                 </Label>
                 <Input 
                   id="image-upload" 
                   type="file" 
                   className="hidden" 
                   accept="image/*,video/*"
                   onChange={(e) => setImage(e.target.files[0])}
                   data-testid="news-image-upload"
                 />
               </div>
               {image && (
                 <Button variant="ghost" size="sm" onClick={() => setImage(null)} className="text-red-400 hover:text-red-300">
                   Remove
                 </Button>
               )}
            </div>
          </CardContent>
        </Card>

        {/* RIGHT: Distribution Control */}
        <Card className="border-orange-500/20 bg-slate-900/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Megaphone className="h-5 w-5 text-orange-500" /> Distribution
            </CardTitle>
            <CardDescription>Select platforms to blast.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center space-x-3 p-3 border border-slate-800 rounded bg-slate-950">
                <Checkbox 
                  id="fb" 
                  checked={platforms.facebook} 
                  onCheckedChange={(c) => setPlatforms(prev => ({...prev, facebook: c}))} 
                  className="border-slate-600 data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600"
                  data-testid="platform-facebook"
                />
                <Label htmlFor="fb" className="flex items-center gap-2 text-white cursor-pointer">
                  <Facebook className="h-4 w-4 text-blue-500" /> Facebook Page
                </Label>
              </div>

              <div className="flex items-center space-x-3 p-3 border border-slate-800 rounded bg-slate-950">
                <Checkbox 
                  id="tw" 
                  checked={platforms.twitter} 
                  onCheckedChange={(c) => setPlatforms(prev => ({...prev, twitter: c}))}
                  className="border-slate-600 data-[state=checked]:bg-sky-500 data-[state=checked]:border-sky-500"
                  data-testid="platform-twitter"
                />
                <Label htmlFor="tw" className="flex items-center gap-2 text-white cursor-pointer">
                  <Twitter className="h-4 w-4 text-sky-500" /> Twitter / X
                </Label>
              </div>

              <div className="flex items-center space-x-3 p-3 border border-slate-800 rounded bg-slate-950">
                <Checkbox 
                  id="wa" 
                  checked={platforms.whatsapp} 
                  onCheckedChange={(c) => setPlatforms(prev => ({...prev, whatsapp: c}))}
                  className="border-slate-600 data-[state=checked]:bg-green-500 data-[state=checked]:border-green-500"
                  data-testid="platform-whatsapp"
                />
                <Label htmlFor="wa" className="flex items-center gap-2 text-white cursor-pointer">
                  <MessageCircle className="h-4 w-4 text-green-500" /> WhatsApp
                </Label>
              </div>

              {/* Instagram */}
              <div className="flex items-center space-x-3 p-3 border border-slate-800 rounded bg-slate-950">
                <Checkbox 
                  id="ig" 
                  checked={platforms.instagram} 
                  onCheckedChange={(c) => setPlatforms(prev => ({...prev, instagram: c}))}
                  className="border-slate-600 data-[state=checked]:bg-pink-600 data-[state=checked]:border-pink-600"
                  data-testid="platform-instagram"
                />
                <Label htmlFor="ig" className="flex items-center gap-2 text-white cursor-pointer">
                  <Instagram className="h-4 w-4 text-pink-500" /> Instagram
                </Label>
              </div>
            </div>

            <Button 
              className="w-full h-12 text-lg font-bold bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 shadow-lg shadow-orange-900/20 text-white"
              onClick={handleBroadcast}
              disabled={publishing || !content}
              data-testid="broadcast-now-btn"
            >
              {publishing ? <Loader2 className="mr-2 animate-spin" /> : <Send className="mr-2" />}
              {publishing ? "Broadcasting..." : "BROADCAST NOW"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SendNews;
