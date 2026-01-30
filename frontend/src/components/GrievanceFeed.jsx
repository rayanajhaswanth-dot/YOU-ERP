import React, { useEffect, useState } from 'react';
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Clock, MapPin, Phone, ArrowRight, Send, Copy } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GrievanceFeed = ({ filteredData }) => {
  const [grievances, setGrievances] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [assigneePhone, setAssigneePhone] = useState("");
  const [generatedLink, setGeneratedLink] = useState("");
  
  // Configuration
  const BOT_NUMBER = "919876543210"; 

  // Effect to handle prop-based data OR fetch fresh data
  useEffect(() => {
    if (filteredData) {
      setGrievances(filteredData);
    } else {
      fetchGrievances();
    }
  }, [filteredData]);

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

  // --- Feature B: Deep Link Logic ---
  const formatDeadline = (isoString) => {
      if (!isoString) return "No Deadline";
      const date = new Date(isoString);
      return date.toLocaleString('en-IN', { 
          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true 
      });
  };

  const generateDeepLink = async () => {
      if (!assigneePhone || assigneePhone.length < 10) {
        toast.error("Invalid Number", { description: "Enter 10-digit mobile number." });
        return;
      }
      const ticket = selectedTicket;
      const issueSummary = ticket.description.substring(0, 60);
      const location = ticket.location || "Ward Unknown";
      const deadline = ticket.priority === 'CRITICAL' ? '4 HOURS' : (ticket.priority === 'HIGH' ? '24 Hours' : '7 Days');
      
      const messageText = `URGENT Task: ${issueSummary}... at ${location}. Priority: ${ticket.priority}. Deadline: ${deadline}. Click here to close: https://wa.me/${BOT_NUMBER}?text=Fixed_${ticket.id}`;
      const encodedMessage = encodeURIComponent(messageText);
      const link = `https://wa.me/${assigneePhone}?text=${encodedMessage}`;
      setGeneratedLink(link);
      
      // Optimistic Backend Update
      try {
        const token = localStorage.getItem('token');
        await fetch(`${BACKEND_URL}/api/grievances/${ticket.id}/assign`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ status: 'assigned', assigned_official_phone: assigneePhone })
        });
        toast.success("Official Assigned", { description: "Ticket status updated." });
      } catch(e) { console.error(e); }
  };
  
  const copyToClipboard = () => {
      navigator.clipboard.writeText(generatedLink);
      toast.success("Copied!", { description: "Link copied to clipboard." });
  };

  const openWhatsAppSafe = () => {
      window.open(generatedLink, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="grid gap-3">
        {grievances.map((ticket) => (
          <Card key={ticket.id} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors group">
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
                  <div className="flex items-center gap-4 text-xs text-slate-400 mt-2">
                    <span className="flex items-center gap-1 text-blue-400"><MapPin className="h-3 w-3" /> {ticket.location || "Ward Unknown"}</span>
                    <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {ticket.citizen_phone || "Hidden"}</span>
                  </div>
                </div>

                {/* Action Button */}
                {ticket.status === 'pending' || ticket.status === 'open' || ticket.status === 'PENDING' ? (
                  <Button 
                    size="sm" 
                    className="bg-blue-600 hover:bg-blue-700 text-white shrink-0 w-full md:w-auto md:opacity-0 md:group-hover:opacity-100 transition-opacity"
                    onClick={() => { setSelectedTicket(ticket); setGeneratedLink(""); setAssigneePhone(""); }}
                  >
                    Assign <ArrowRight className="ml-1 h-3 w-3" />
                  </Button>
                ) : (
                  <Badge variant="outline" className="border-green-900 text-green-500 bg-green-900/10">
                    {ticket.status}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}

        {/* Modal Logic */}
        <Dialog open={!!selectedTicket} onOpenChange={() => setSelectedTicket(null)}>
            <DialogContent className="bg-slate-950 border-slate-800 text-white sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Assign Task</DialogTitle>
                    <DialogDescription className="text-slate-400">Generate WhatsApp Deep Link</DialogDescription>
                </DialogHeader>
                {!generatedLink ? (
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label>Official's Mobile (10 digits)</Label>
                            <Input 
                                placeholder="9988776655" 
                                className="bg-slate-900 border-slate-800 text-white"
                                value={assigneePhone}
                                onChange={(e) => setAssigneePhone(e.target.value)}
                                maxLength={10}
                            />
                        </div>
                        <Button onClick={generateDeepLink} className="w-full bg-orange-500 hover:bg-orange-600">Generate Link</Button>
                    </div>
                ) : (
                    <div className="space-y-4 py-2">
                        <div className="p-3 bg-green-900/10 border border-green-900/50 rounded text-center">
                            <p className="text-green-400 text-xs font-bold mb-1">Link Ready</p>
                            <div className="text-[10px] text-slate-400 bg-black/30 p-2 rounded break-all font-mono">{generatedLink.substring(0,50)}...</div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <Button variant="outline" onClick={copyToClipboard}><Copy className="h-4 w-4 mr-2" /> Copy</Button>
                            <Button className="bg-[#25D366] hover:bg-[#20bd5a]" onClick={openWhatsAppSafe}><Send className="h-4 w-4 mr-2" /> WhatsApp</Button>
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    </div>
  );
};

export default GrievanceFeed;
