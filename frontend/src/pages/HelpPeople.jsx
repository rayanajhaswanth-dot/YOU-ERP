import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { Search, Filter, AlertTriangle, Plus, MapPin, BarChart3, Clock, Mic, ChevronDown, ChevronUp, CheckCircle, AlertCircle, List } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { toast } from "sonner";
import VoiceRecorder from '../components/VoiceRecorder';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../components/ui/collapsible";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// 11-SECTOR GOVERNANCE FRAMEWORK
const CATEGORIES = [
    "Water & Irrigation", "Agriculture", "Forests & Environment", 
    "Health & Sanitation", "Education", "Infrastructure & Roads", 
    "Law & Order", "Welfare Schemes", "Finance & Taxation", 
    "Urban & Rural Development", "Miscellaneous"
];

const HelpPeople = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterText, setFilterText] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);

  const [formData, setFormData] = useState({
    citizen_name: "",
    citizen_phone: "",
    location: "",
    category: "Miscellaneous",
    description: "",
    priority_level: "MEDIUM"
  });

  useEffect(() => {
    fetchGrievances();
  }, []);

  const fetchGrievances = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${BACKEND_URL}/api/grievances/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if(res.ok) setGrievances(await res.json());
    } catch(e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    try {
        const token = localStorage.getItem('token');
        
        // Manual Priority Map based on 11-Sector Framework
        let hours = 168;
        if(formData.priority_level === 'CRITICAL') hours = 4;
        else if(formData.priority_level === 'HIGH') hours = 24;
        else if(formData.priority_level === 'MEDIUM') hours = 72;
        
        const deadline = new Date(Date.now() + hours * 3600000).toISOString();
        const payload = {
          village: formData.location || "Unknown Ward",
          description: formData.description,
          issue_type: formData.category,
          ai_priority: formData.priority_level === 'CRITICAL' ? 10 : (formData.priority_level === 'HIGH' ? 8 : 5)
        };

        const res = await fetch(`${BACKEND_URL}/api/grievances/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            toast.success("Grievance Registered Successfully");
            setFormData({ citizen_name: "", citizen_phone: "", location: "", category: "Miscellaneous", description: "", priority_level: "MEDIUM" });
            fetchGrievances();
            setIsAddOpen(false);
        } else {
            toast.error("Registration Failed");
        }
    } catch(e) {
        toast.error("Registration Failed", { description: e.message });
    }
  };

  // Category to Priority mapping (11-Sector Framework)
  const getCategoryPriority = (category) => {
    if (["Law & Order", "Health & Sanitation"].includes(category)) return "CRITICAL";
    if (["Water & Irrigation", "Infrastructure & Roads", "Agriculture"].includes(category)) return "HIGH";
    if (["Welfare Schemes", "Education"].includes(category)) return "MEDIUM";
    return "LOW";
  };

  // --- KPIS ---
  const totalGrievances = grievances.length;
  const resolvedCount = grievances.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length;
  const pendingCount = grievances.filter(g => g.status !== 'resolved' && g.status !== 'RESOLVED').length;
  const longPendingCount = grievances.filter(g => {
      if (g.status === 'resolved' || g.status === 'RESOLVED') return false;
      const diffDays = Math.ceil(Math.abs(new Date() - new Date(g.created_at)) / (1000 * 60 * 60 * 24)); 
      return diffDays > 7;
  }).length;

  const topCritical = grievances
    .filter(g => (g.priority_level === 'CRITICAL' || g.priority === 'CRITICAL') && g.status !== 'resolved' && g.status !== 'RESOLVED')
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .slice(0, 3);

  const getCategoryData = () => {
      const counts = {};
      grievances.forEach(g => {
          const cat = g.category || g.issue_type || "Miscellaneous";
          counts[cat] = (counts[cat] || 0) + 1;
      });
      return Object.keys(counts)
        .map(key => ({ name: key, count: counts[key] }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);
  };

  const filteredList = grievances.filter(g => 
    (g.citizen_name || g.village || "").toLowerCase().includes(filterText.toLowerCase()) ||
    (g.location || g.village || "").toLowerCase().includes(filterText.toLowerCase()) ||
    (g.id || "").includes(filterText)
  );

  // Sorting
  const sortedList = [...filteredList].sort((a, b) => {
    if (sortBy === "priority") {
      const priorityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      return (priorityOrder[a.priority_level] || 3) - (priorityOrder[b.priority_level] || 3);
    }
    if (sortBy === "date") {
      return new Date(b.created_at) - new Date(a.created_at);
    }
    return 0;
  });

  return (
    <div className="p-6 space-y-8 text-white">
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <div className="p-2 bg-orange-900/20 rounded-lg">
              <AlertTriangle className="h-8 w-8 text-orange-500" />
          </div>
          <div>
              <h1 className="text-3xl font-bold tracking-tight">Help People Console</h1>
              <p className="text-slate-400 text-sm">11-Sector Governance Framework</p>
          </div>
      </div>

      {/* 1. KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-slate-900 border-slate-800 hover:border-slate-700">
              <CardContent className="p-5 flex justify-between items-center">
                  <div><p className="text-slate-400 text-xs font-bold uppercase">Total</p><p className="text-3xl font-bold text-white">{totalGrievances}</p></div>
                  <List className="h-8 w-8 text-blue-500 opacity-50" />
              </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800 hover:border-slate-700">
              <CardContent className="p-5 flex justify-between items-center">
                  <div><p className="text-slate-400 text-xs font-bold uppercase">Resolved</p><p className="text-3xl font-bold text-green-400">{resolvedCount}</p></div>
                  <CheckCircle className="h-8 w-8 text-green-500 opacity-50" />
              </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800 hover:border-slate-700">
              <CardContent className="p-5 flex justify-between items-center">
                  <div><p className="text-slate-400 text-xs font-bold uppercase">Pending</p><p className="text-3xl font-bold text-yellow-400">{pendingCount}</p></div>
                  <Clock className="h-8 w-8 text-yellow-500 opacity-50" />
              </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800 hover:border-slate-700">
              <CardContent className="p-5 flex justify-between items-center">
                  <div><p className="text-slate-400 text-xs font-bold uppercase">Long Pending</p><p className="text-3xl font-bold text-red-400">{longPendingCount}</p></div>
                  <AlertCircle className="h-8 w-8 text-red-500 opacity-50" />
              </CardContent>
          </Card>
      </div>

      {/* 2. TOP 3 CRITICAL */}
      <div>
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2 mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" /> Unresolved Critical Issues
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topCritical.length > 0 ? topCritical.map((issue) => (
                  <Card key={issue.id} className="bg-gradient-to-br from-slate-900 to-red-950/20 border-red-900/30 border hover:border-red-500/50 transition-all group">
                      <CardHeader className="pb-2">
                          <div className="flex justify-between items-start">
                              <Badge className="bg-red-600 text-white">CRITICAL</Badge>
                              <span className="text-xs text-red-400 font-mono">#{issue.id.slice(0,6)}</span>
                          </div>
                          <CardTitle className="text-white text-md mt-2 truncate">{issue.category || issue.issue_type}</CardTitle>
                      </CardHeader>
                      <CardContent>
                          <p className="text-slate-300 text-sm line-clamp-2 mb-2">{issue.description}</p>
                          <div className="flex items-center gap-2 text-xs text-slate-500"><MapPin className="h-3 w-3" /> {issue.location || issue.village}</div>
                      </CardContent>
                  </Card>
              )) : (
                  <div className="col-span-3 p-6 border border-dashed border-slate-800 rounded-lg text-center text-slate-500 italic bg-slate-900/50">All critical issues resolved.</div>
              )}
          </div>
      </div>

      {/* 3. ADD GRIEVANCE */}
      <Collapsible open={isAddOpen} onOpenChange={setIsAddOpen} className="border border-slate-700/50 rounded-xl bg-slate-900 shadow-md">
          <CollapsibleTrigger className="w-full">
              <div className="flex items-center justify-between p-5 bg-gradient-to-r from-slate-900 to-slate-800 hover:to-slate-900 transition-all cursor-pointer">
                  <h3 className="text-white font-bold flex items-center gap-3 text-lg">
                      <div className="bg-blue-600 rounded-full p-1"><Plus className="h-4 w-4 text-white" /></div> Register New Grievance
                  </h3>
                  {isAddOpen ? <ChevronUp className="h-5 w-5 text-slate-400" /> : <ChevronDown className="h-5 w-5 text-slate-400" />}
              </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
              <div className="p-6 border-t border-slate-800 space-y-6 bg-slate-950">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="space-y-2"><Label className="text-white">Complainant Name</Label><Input className="bg-slate-900 border-slate-700 text-white" placeholder="Name" value={formData.citizen_name} onChange={(e) => setFormData({...formData, citizen_name: e.target.value})} /></div>
                      <div className="space-y-2"><Label className="text-white">Contact</Label><Input className="bg-slate-900 border-slate-700 text-white" placeholder="+91..." value={formData.citizen_phone} onChange={(e) => setFormData({...formData, citizen_phone: e.target.value})} /></div>
                      <div className="space-y-2"><Label className="text-white">Area</Label><Input className="bg-slate-900 border-slate-700 text-white" placeholder="Ward/Village" value={formData.location} onChange={(e) => setFormData({...formData, location: e.target.value})} /></div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                          <Label className="text-white">Category (11-Sector Framework)</Label>
                          <Select onValueChange={(val) => {
                              const p = getCategoryPriority(val);
                              setFormData({...formData, category: val, priority_level: p});
                          }}>
                              <SelectTrigger className="bg-slate-900 border-slate-700 text-white"><SelectValue placeholder="Select Category" /></SelectTrigger>
                              <SelectContent className="bg-slate-900 border-slate-800 text-white max-h-[250px]">
                                  {CATEGORIES.map(cat => (
                                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                                  ))}
                              </SelectContent>
                          </Select>
                          <p className="text-xs text-slate-500 mt-1">
                            Auto-Priority: <Badge className={
                              formData.priority_level === 'CRITICAL' ? 'bg-red-600' : 
                              formData.priority_level === 'HIGH' ? 'bg-orange-600' : 
                              formData.priority_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-blue-600'
                            }>{formData.priority_level}</Badge>
                          </p>
                      </div>
                      <div className="space-y-2">
                          <Label className="text-white">Description</Label>
                          <div className="relative">
                              <Textarea className="bg-slate-900 border-slate-700 text-white min-h-[100px] pr-12" placeholder="Details..." value={formData.description} onChange={(e) => setFormData({...formData, description: e.target.value})} />
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                className="absolute bottom-2 right-2 h-8 w-8 p-0 hover:bg-slate-800"
                                onClick={() => setShowVoiceRecorder(true)}
                              >
                                <Mic className="h-4 w-4 text-orange-500" />
                              </Button>
                          </div>
                      </div>
                  </div>
                  <div className="flex justify-end gap-4 pt-2">
                      <Button variant="outline" className="border-slate-700 text-slate-300" onClick={() => setIsAddOpen(false)}>Cancel</Button>
                      <Button onClick={handleRegister} className="bg-orange-600 hover:bg-orange-700 text-white font-bold">Register Ticket</Button>
                  </div>
              </div>
          </CollapsibleContent>
      </Collapsible>

      {/* 4. SEARCH & GRAPH SPLIT */}
      <div className="flex flex-col lg:flex-row gap-6 min-h-[500px]">
          {/* LIST */}
          <div className="flex-1 space-y-4">
              <div className="flex gap-4 items-center bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                  <Search className="h-4 w-4 text-slate-500" />
                  <Input className="bg-transparent border-none text-white focus-visible:ring-0 placeholder:text-slate-600 p-0" placeholder="Search grievances..." value={filterText} onChange={(e) => setFilterText(e.target.value)} />
                  <div className="flex items-center gap-2 ml-auto">
                    <Filter className="h-4 w-4 text-slate-500" />
                    <Select onValueChange={setSortBy} defaultValue="priority">
                      <SelectTrigger className="w-[130px] bg-slate-950 border-slate-700 text-white text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="priority">Priority</SelectItem>
                        <SelectItem value="date">Date</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
              </div>
              <div className="grid gap-3 max-h-[600px] overflow-y-auto pr-2">
                  {sortedList.map((ticket) => (
                      <div key={ticket.id} className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center hover:bg-slate-800/50 transition-all">
                          <div>
                              <div className="flex items-center gap-3">
                                  <span className="text-white font-semibold">{ticket.citizen_name || ticket.village || "Anonymous"}</span>
                                  <Badge variant="outline" className="text-[10px] text-slate-400 border-slate-700">{ticket.category || ticket.issue_type}</Badge>
                                  <Badge className={
                                    ticket.priority_level === 'CRITICAL' ? 'bg-red-600' : 
                                    ticket.priority_level === 'HIGH' ? 'bg-orange-600' : 
                                    ticket.priority_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-blue-600'
                                  }>
                                      {ticket.priority_level || 'LOW'}
                                  </Badge>
                              </div>
                              <p className="text-sm text-slate-400 mt-1 line-clamp-1">{ticket.description}</p>
                              <div className="flex gap-4 mt-2 text-xs text-slate-500 font-mono">
                                  <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {ticket.location || ticket.village}</span>
                                  <span className={`uppercase font-bold ${ticket.status === 'resolved' || ticket.status === 'RESOLVED' ? 'text-green-500' : 'text-yellow-500'}`}>{ticket.status}</span>
                              </div>
                          </div>
                          <Button variant="secondary" size="sm" className="bg-slate-800 text-white">Manage</Button>
                      </div>
                  ))}
              </div>
          </div>

          {/* ANALYTICS GRAPH */}
          <div className="w-full lg:w-[450px]">
              <Card className="bg-slate-900 border-slate-800 h-full sticky top-6 shadow-xl">
                  <CardHeader className="border-b border-slate-800 pb-4">
                      <CardTitle className="text-md text-white flex items-center gap-2"><BarChart3 className="h-5 w-5 text-purple-500" /> Sector Analysis</CardTitle>
                  </CardHeader>
                  <CardContent className="h-[400px] pt-6">
                      <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={getCategoryData()} layout="vertical" margin={{ left: 10, right: 30 }}>
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                              <XAxis type="number" hide />
                              <YAxis dataKey="name" type="category" width={130} tick={{fill: '#e2e8f0', fontSize: 12, fontWeight: 500}} interval={0} axisLine={false} tickLine={false} />
                              <Tooltip cursor={{fill: '#1e293b', opacity: 0.4}} contentStyle={{backgroundColor: '#020617', border: '1px solid #1e293b', color: '#fff', borderRadius: '8px'}} />
                              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={20}>
                                  {getCategoryData().map((entry, index) => (
                                      <Cell key={`cell-${index}`} fill={['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'][index % 5]} />
                                  ))}
                              </Bar>
                          </BarChart>
                      </ResponsiveContainer>
                  </CardContent>
              </Card>
          </div>
      </div>

      {/* Voice Recorder Modal */}
      {showVoiceRecorder && (
        <VoiceRecorder 
          onTranscriptionComplete={(result) => {
            if (result?.text) {
              setFormData(prev => ({...prev, description: (prev.description + " " + result.text).trim()}));
            }
            setShowVoiceRecorder(false);
          }}
          onClose={() => setShowVoiceRecorder(false)}
        />
      )}

    </div>
  );
};

export default HelpPeople;
