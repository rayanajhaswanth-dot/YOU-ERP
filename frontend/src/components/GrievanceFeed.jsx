import React, { useEffect, useState } from 'react';
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { AlertCircle, Clock, MapPin, Phone, ArrowRight, Send, Copy } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GrievanceFeed = () => {
  const [grievances, setGrievances] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [assigneePhone, setAssigneePhone] = useState("");
  const [generatedLink, setGeneratedLink] = useState("");

  // Configuration - Ideally from ENV, hardcoded for PRD compliance demonstration
  const BOT_NUMBER = "919876543210"; 

  useEffect(() => {
    fetchGrievances();
  }, []);

  const fetchGrievances = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${BACKEND_URL}/api/grievances/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setGrievances(data);
      }
    } catch (error) {
      console.error("Feed Error:", error);
    }
  };

  // --- FEATURE B: DEEP LINK GENERATION LOGIC ---
  const generateDeepLink = async () => {
    if (!assigneePhone || assigneePhone.length < 10) {
      toast.error("Invalid Number", { description: "Please enter a valid 10-digit mobile number." });
      return;
    }

    const ticket = selectedTicket;
    
    // 1. Construct the Message as per PRD
    const issueSummary = ticket.description.substring(0, 60);
    const location = ticket.location || "Ward Unknown";
    const deadline = ticket.priority === 'CRITICAL' ? '4 HOURS' : (ticket.priority === 'HIGH' ? '24 Hours' : '7 Days');
    
    // The "Magic String" format required by PRD
    const messageText = `URGENT Task: ${issueSummary}... at ${location}. Priority: ${ticket.priority}. Deadline: ${deadline}. Click here to close: https://wa.me/${BOT_NUMBER}?text=Fixed_${ticket.id}`;
    
    // 2. Encode for URL
    const encodedMessage = encodeURIComponent(messageText);
    
    // 3. Create the Universal WhatsApp Link
    const link = `https://wa.me/${assigneePhone}?text=${encodedMessage}`;
    
    setGeneratedLink(link);

    // 4. Optimistic Update (Update Backend)
    try {
        const token = localStorage.getItem('token');
        await fetch(`${BACKEND_URL}/api/grievances/${ticket.id}/assign`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: 'assigned', assigned_official_phone: assigneePhone })
        });
        toast.success("Official Assigned", { description: "Ticket status updated. Send the link now." });
        fetchGrievances(); 
    } catch (e) {
        console.error("Assignment Sync Error", e);
    }
  };

  const openWhatsAppSafe = () => {
      // FIX FOR BLOCKED FRAME: Open in new tab with security tags
      window.open(generatedLink, '_blank', 'noopener,noreferrer');
  };

  const copyToClipboard = () => {
      navigator.clipboard.writeText(generatedLink);
      toast.success("Copied!", { description: "Link copied to clipboard." });
  };

  // --- TIMEZONE FIX HELPER ---
  const formatDeadline = (isoString) => {
      if (!isoString) return "No Deadline";
      const date = new Date(isoString);
      // This automatically uses the browser's local timezone (IST)
      return date.toLocaleString('en-IN', { 
          month: 'short', 
          day: 'numeric', 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: true 
      });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white flex items-center gap-2">
        <AlertCircle className="h-5 w-5 text-orange-500" />
        Briefing Room (Live Feed)
      </h2>

      <div className="grid gap-4">
        {grievances.map((ticket) => (
          <Card key={ticket.id} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
            <CardContent className="p-4">
              <div className="flex flex-col md:flex-row justify-between items-start gap-4">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={ticket.priority === 'CRITICAL' ? 'destructive' : 'default'} className="uppercase text-[10px] tracking-wider font-bold">
                      {ticket.priority}
                    </Badge>
                    <span className="text-slate-500 text-xs flex items-center gap-1 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      <Clock className="h-3 w-3" /> Due: {formatDeadline(ticket.deadline_timestamp)}
                    </span>
                  </div>
                  <p className="text-white font-medium text-sm leading-relaxed">{ticket.description}</p>
                  <div className="flex items-center gap-4 text-xs text-slate-400 mt-3">
                    <span className="flex items-center gap-1 text-blue-400"><MapPin className="h-3 w-3" /> {ticket.location || "Ward Unknown"}</span>
                    <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {ticket.citizen_phone || "Hidden"}</span>
                  </div>
                </div>

                {/* Action Button: OSD Flow */}
                {ticket.status === 'pending' || ticket.status === 'open' ? (
                  <Button 
                    size="sm" 
                    className="bg-blue-600 hover:bg-blue-700 text-white shrink-0 mt-2 md:mt-0 w-full md:w-auto"
                    onClick={() => { setSelectedTicket(ticket); setGeneratedLink(""); setAssigneePhone(""); }}
                  >
                    Assign Official <ArrowRight className="ml-1 h-3 w-3" />
                  </Button>
                ) : (
                  <Badge variant="outline" className="border-green-900 text-green-500 bg-green-900/10 mt-2 md:mt-0">
                    {ticket.status === 'assigned' ? 'Assigned' : 'Resolved'}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Assignment Modal (The Deep Link Engine) */}
      <Dialog open={!!selectedTicket} onOpenChange={() => setSelectedTicket(null)}>
        <DialogContent className="bg-slate-950 border-slate-800 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Task #{selectedTicket?.id?.slice(0,4)}</DialogTitle>
            <DialogDescription className="text-slate-400">
              Select the Junior Engineer (JE) responsible for this ward.
            </DialogDescription>
          </DialogHeader>

          {!generatedLink ? (
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Official's Mobile Number (JE)</Label>
                <div className="flex gap-2">
                    <div className="bg-slate-900 border border-slate-800 flex items-center px-3 text-slate-400 text-sm rounded">+91</div>
                    <Input 
                    placeholder="9988776655" 
                    className="bg-slate-900 border-slate-800 text-white"
                    value={assigneePhone}
                    onChange={(e) => setAssigneePhone(e.target.value)}
                    maxLength={10}
                    />
                </div>
              </div>
              <Button onClick={generateDeepLink} className="w-full bg-orange-500 hover:bg-orange-600 font-bold">
                Generate Deep Link
              </Button>
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <div className="p-3 bg-green-900/10 border border-green-900/50 rounded text-center">
                <p className="text-green-400 text-xs font-bold mb-1 uppercase tracking-wider">Deep Link Generated</p>
                <div className="text-[10px] text-slate-400 bg-black/30 p-2 rounded break-all font-mono">
                    {generatedLink.substring(0, 60)}...
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                  <Button 
                    variant="outline"
                    className="w-full border-slate-700 text-slate-300 hover:bg-slate-800"
                    onClick={copyToClipboard}
                  >
                    <Copy className="h-4 w-4 mr-2" /> Copy Link
                  </Button>
                  <Button 
                    className="w-full bg-[#25D366] hover:bg-[#20bd5a] text-white font-bold"
                    onClick={openWhatsAppSafe}
                  >
                    <Send className="h-4 w-4 mr-2" /> WhatsApp
                  </Button>
              </div>
              <p className="text-[10px] text-slate-500 text-center">
                  *Clicking 'WhatsApp' opens a new tab to bypass browser security blocks.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GrievanceFeed;
