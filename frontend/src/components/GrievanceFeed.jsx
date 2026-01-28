import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { AlertTriangle, Clock, MapPin, Send, CheckCircle, Loader2 } from "lucide-react";
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GrievanceFeed = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);

  // CTO UPDATE: RBAC LOGIC
  // Retrieve role to determine if user can manage tickets
  const userRole = localStorage.getItem('user_role')?.toLowerCase() || 'citizen';
  // CTO NOTE: Updated to include 'leader' and 'politician' per user request for write access
  const canManage = ['osd', 'registrar', 'leader', 'politician'].includes(userRole);

  useEffect(() => {
    fetchGrievances();
    // Poll every 30 seconds for real-time updates
    const interval = setInterval(fetchGrievances, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchGrievances = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${BACKEND_URL}/api/dashboard/grievances`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        // Filter for Critical/High priority for the Feed
        const criticalData = Array.isArray(data) 
          ? data.filter(t => t.priority_level === 'CRITICAL' || t.priority_level === 'HIGH')
          : [];
        setGrievances(criticalData);
      }
    } catch (error) {
      console.error("Feed Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = (item) => {
    // PRD Feature B: Deep Link Assignment
    const message = 
      `🚨 *URGENT TASK ASSIGNMENT*\n\n` +
      `*Issue:* ${item.issue_type || 'General Issue'}\n` +
      `*Location:* ${item.village || 'Constituency'}\n` +
      `*Priority:* ${item.priority_level || 'HIGH'}\n\n` +
      `*Description:* ${item.description}\n\n` +
      `Please resolve this immediately and share proof of completion.`;

    const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
    window.open(url, '_blank');
    toast.success("Task Delegated - WhatsApp assignment link generated.");
  };

  return (
    <Card className="col-span-1 h-[400px] flex flex-col border-orange-500/20 bg-slate-900/50 backdrop-blur">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Active Fires
            <Badge variant="outline" className="ml-2 border-red-500/50 text-red-400">
              {grievances.length} Critical
            </Badge>
          </CardTitle>
          {/* CTO NOTE: Visual Indicator of Mode */}
          {!canManage && (
            <Badge variant="secondary" className="bg-slate-800 text-slate-400 text-xs">
              View Only
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full px-4 pb-4">
          {loading ? (
             <div className="flex justify-center items-center h-40">
               <Loader2 className="h-6 w-6 animate-spin text-orange-500" />
             </div>
          ) : grievances.length === 0 ? (
            <div className="text-center text-slate-500 mt-10">
              <CheckCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No critical issues active.</p>
            </div>
          ) : (
            <div className="space-y-3 pt-2">
              {grievances.map((ticket, index) => (
                <div key={ticket.id || index} className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 hover:bg-slate-900 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div className="space-y-1">
                      <h4 className="font-medium text-slate-200 text-sm">{ticket.issue_type || 'General Issue'}</h4>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <MapPin className="h-3 w-3" /> {ticket.village || ticket.location || "Unknown Loc"}
                        <span className="text-slate-700">|</span>
                        <Clock className="h-3 w-3" /> {ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : 'N/A'}
                      </div>
                    </div>
                    <Badge className={
                      ticket.priority_level === 'CRITICAL' ? "bg-red-900/30 text-red-400 border-red-900" : "bg-orange-900/30 text-orange-400 border-orange-900"
                    }>
                      {ticket.priority_level || 'HIGH'}
                    </Badge>
                  </div>
                  
                  <p className="text-xs text-slate-500 line-clamp-2 mb-2">{ticket.description}</p>
                  
                  {/* CTO UPDATE: Only OSD/Registrar/Leader/Politician can see these buttons */}
                  {canManage && (
                    <div className="flex gap-2 mt-3">
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="w-full h-8 text-xs border-orange-500/30 text-orange-400 hover:bg-orange-950"
                        onClick={() => handleAssign(ticket)}
                        data-testid={`assign-btn-${ticket.id}`}
                      >
                        <Send className="h-3 w-3 mr-1" /> Assign Officer
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default GrievanceFeed;
