import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { Search, Filter, AlertTriangle, Plus, MapPin, BarChart3, Clock, Mic, ChevronDown, ChevronUp, CheckCircle, Clock4, List } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { toast } from "sonner";
import VoiceRecorder from '../components/VoiceRecorder';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../components/ui/collapsible";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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
    category: "General",
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
        
        const deadlineHours = formData.priority_level === 'CRITICAL' ? 4 : (formData.priority_level === 'HIGH' ? 24 : 168);
        const deadline = new Date(Date.now() + deadlineHours * 3600000).toISOString();

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
            setFormData({ citizen_name: "", citizen_phone: "", location: "", category: "General", description: "", priority_level: "MEDIUM" });
            fetchGrievances();
            setIsAddOpen(false);
        } else {
            toast.error("Registration Failed");
        }
    } catch(e) {
        toast.error("Registration Failed", { description: e.message });
    }
  };

  // --- KPIS CALCULATION ---
  const totalGrievances = grievances.length;
  const resolvedCount = grievances.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length;
  const pendingCount = grievances.filter(g => g.status !== 'resolved' && g.status !== 'RESOLVED').length;
  const longPendingCount = grievances.filter(g => {
      if (g.status === 'resolved' || g.status === 'RESOLVED') return false;
      const created = new Date(g.created_at);
      const diffTime = Math.abs(new Date() - created);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
      return diffDays > 7;
  }).length;

  // Top 3 Critical Unresolved
  const topCritical = grievances
    .filter(g => (g.priority_level === 'CRITICAL' || g.priority === 'CRITICAL') && g.status !== 'resolved' && g.status !== 'RESOLVED')
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .slice(0, 3);

  // Graph Data
  const getCategoryData = () => {
      const counts = {};
      grievances.forEach(g => {
          const cat = g.category || g.issue_type || "General";
          counts[cat] = (counts[cat] || 0) + 1;
      });
      const data = Object.keys(counts).map(key => ({ name: key, count: counts[key] }));
      return data.sort((a, b) => b.count - a.count).slice(0, 5);
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
      <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-orange-500" />
          <div>
              <h1 className="text-3xl font-bold">Help People Console</h1>
              <p className="text-slate-400 text-sm">Grievance Redressal & Citizen Support</p>
          </div>
      </div>

      {/* 1. KPIs ROW */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 flex items-center justify-between">
                  <div>
                      <p className="text-slate-400 text-xs uppercase font-bold">Total Grievances</p>
                      <p className="text-2xl font-bold text-white mt-1">{totalGrievances}</p>
                  </div>
                  <List className="h-8 w-8 text-blue-500 opacity-50" />
              </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 flex items-center justify-between">
                  <div>
                      <p className="text-slate-400 text-xs uppercase font-bold">Resolved</p>
                      <p className="text-2xl font-bold text-green-400 mt-1">{resolvedCount}</p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-green-500 opacity-50" />
              </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 flex items-center justify-between">
                  <div>
                      <p className="text-slate-400 text-xs uppercase font-bold">Pending</p>
                      <p className="text-2xl font-bold text-yellow-400 mt-1">{pendingCount}</p>
                  </div>
                  <Clock className="h-8 w-8 text-yellow-500 opacity-50" />
              </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 flex items-center justify-between">
                  <div>
                      <p className="text-slate-400 text-xs uppercase font-bold">Long Pending (&gt;7 Days)</p>
                      <p className="text-2xl font-bold text-red-400 mt-1">{longPendingCount}</p>
                  </div>
                  <Clock4 className="h-8 w-8 text-red-500 opacity-50" />
              </CardContent>
          </Card>
      </div>

      {/* 2. TOP 3 CRITICAL ISSUES */}
      <div>
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2 mb-3">
              Priority 1: Unresolved Critical Issues
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topCritical.length > 0 ? topCritical.map((issue) => (
                  <Card key={issue.id} className="bg-red-950/20 border-red-900/50 border relative overflow-hidden hover:border-red-500 transition-colors">
                      <div className="absolute top-0 right-0 p-2 opacity-10">
                          <AlertTriangle className="h-20 w-20 text-red-500" />
                      </div>
                      <CardHeader className="pb-2">
                          <div className="flex justify-between items-start">
                              <Badge className="bg-red-600 text-white animate-pulse">CRITICAL</Badge>
                              <span className="text-xs text-red-300 font-mono">ID: {issue.id.slice(0,6)}</span>
                          </div>
                          <CardTitle className="text-white text-md mt-2 line-clamp-1">{issue.category || issue.issue_type}</CardTitle>
                      </CardHeader>
                      <CardContent>
                          <p className="text-slate-300 text-sm line-clamp-2 mb-2">{issue.description}</p>
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                              <MapPin className="h-3 w-3" /> {issue.location || issue.village}
                          </div>
                      </CardContent>
                  </Card>
              )) : (
                  <div className="col-span-3 p-6 border border-dashed border-slate-800 rounded-lg text-center text-slate-500 italic bg-slate-900/50">
                      No critical issues pending. All clear.
                  </div>
              )}
          </div>
      </div>

      {/* 3. ADD GRIEVANCE (EXPANSION) */}
      <Collapsible open={isAddOpen} onOpenChange={setIsAddOpen} className="border border-slate-800 rounded-lg bg-slate-900 overflow-hidden">
          <div className="flex items-center justify-between p-4 bg-slate-900 cursor-pointer hover:bg-slate-800/50 transition-colors" onClick={() => setIsAddOpen(!isAddOpen)}>
              <h3 className="text-white font-bold flex items-center gap-2">
                  <Plus className="h-5 w-5 text-blue-500" /> 
                  Register New Grievance
              </h3>
              {isAddOpen ? <ChevronUp className="h-5 w-5 text-slate-400" /> : <ChevronDown className="h-5 w-5 text-slate-400" />}
          </div>
          
          <CollapsibleContent>
              <div className="p-6 pt-2 border-t border-slate-800 space-y-6 bg-slate-950/50">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="space-y-2">
                          <Label className="text-slate-300">Complainant Name</Label>
                          <Input className="bg-slate-900 border-slate-700 text-white" placeholder="Full Name" value={formData.citizen_name} onChange={(e) => setFormData({...formData, citizen_name: e.target.value})} />
                      </div>
                      <div className="space-y-2">
                          <Label className="text-slate-300">Contact Number</Label>
                          <Input className="bg-slate-900 border-slate-700 text-white" placeholder="+91..." value={formData.citizen_phone} onChange={(e) => setFormData({...formData, citizen_phone: e.target.value})} />
                      </div>
                      <div className="space-y-2">
                          <Label className="text-slate-300">Area / Ward</Label>
                          <Input className="bg-slate-900 border-slate-700 text-white" placeholder="e.g. Ward 5" value={formData.location} onChange={(e) => setFormData({...formData, location: e.target.value})} />
                      </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                          <Label className="text-slate-300">Issue Category</Label>
                          <Select onValueChange={(val) => {
                              let p = "MEDIUM";
                              if(["Electricity", "Safety", "Fire"].includes(val)) p = "CRITICAL";
                              if(["Water", "Sewage"].includes(val)) p = "HIGH";
                              setFormData({...formData, category: val, priority_level: p});
                          }}>
                              <SelectTrigger className="bg-slate-900 border-slate-700 text-white"><SelectValue placeholder="Select Category" /></SelectTrigger>
                              <SelectContent>
                                  <SelectItem value="Electricity">Electricity</SelectItem>
                                  <SelectItem value="Water">Water Supply</SelectItem>
                                  <SelectItem value="Safety">Public Safety / Fire</SelectItem>
                                  <SelectItem value="Roads">Roads & Infrastructure</SelectItem>
                                  <SelectItem value="Sanitation">Sanitation</SelectItem>
                                  <SelectItem value="General">General</SelectItem>
                              </SelectContent>
                          </Select>
                      </div>
                      <div className="space-y-2">
                          <Label className="text-slate-300">Description</Label>
                          <div className="relative">
                              <Textarea className="bg-slate-900 border-slate-700 text-white min-h-[80px] pr-12" placeholder="Details..." value={formData.description} onChange={(e) => setFormData({...formData, description: e.target.value})} />
                              {/* Voice Input Button Inside Text Area */}
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
                  <div className="flex justify-end">
                      <Button onClick={handleRegister} className="bg-orange-600 hover:bg-orange-700 text-white font-bold">Register Ticket</Button>
                  </div>
              </div>
          </CollapsibleContent>
      </Collapsible>

      {/* 4. SEARCH & FILTER */}
      <div className="flex gap-4 items-center bg-slate-900 p-4 rounded-lg border border-slate-800">
          <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-500" />
              <Input 
                  className="pl-10 bg-slate-950 border-slate-700 text-white focus:ring-blue-500" 
                  placeholder="Search by Name, Category, ID..."
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
              />
          </div>
          <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-500" />
              <Select onValueChange={setSortBy} defaultValue="priority">
                  <SelectTrigger className="w-[150px] bg-slate-950 border-slate-700 text-white"><SelectValue /></SelectTrigger>
                  <SelectContent>
                      <SelectItem value="priority">Sort by Priority</SelectItem>
                      <SelectItem value="date">Sort by Date</SelectItem>
                      <SelectItem value="status">Sort by Status</SelectItem>
                  </SelectContent>
              </Select>
          </div>
      </div>

      {/* 5. SPLIT VIEW: LIST + GRAPH */}
      <div className="flex flex-col lg:flex-row gap-6 min-h-[500px]">
          
          {/* LEFT: All Grievances List */}
          <div className="flex-1 space-y-4">
              <h3 className="text-white font-bold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-500" /> All Grievances ({sortedList.length})
              </h3>
              <div className="grid gap-3 max-h-[600px] overflow-y-auto pr-2">
                  {sortedList.map((ticket) => (
                      <div key={ticket.id} className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center hover:border-slate-700 transition-colors group">
                          <div>
                              <div className="flex items-center gap-3">
                                  <span className="text-white font-medium text-lg">{ticket.citizen_name || ticket.village || "Anonymous"}</span>
                                  <Badge variant="outline" className="text-xs text-slate-400 border-slate-700">{ticket.category || ticket.issue_type}</Badge>
                                  <Badge className={
                                    ticket.priority_level === 'CRITICAL' ? 'bg-red-600' : 
                                    ticket.priority_level === 'HIGH' ? 'bg-orange-600' : 
                                    ticket.priority_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-blue-600'
                                  }>
                                      {ticket.priority_level || 'LOW'}
                                  </Badge>
                              </div>
                              <p className="text-sm text-slate-400 mt-1 line-clamp-1">{ticket.description}</p>
                              <div className="flex gap-4 mt-2 text-xs text-slate-500">
                                  <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {ticket.location || ticket.village}</span>
                                  <span className="font-mono bg-slate-950 px-1 rounded">ID: {ticket.id?.slice(0,6)}</span>
                                  <span className={`uppercase font-bold ${ticket.status === 'resolved' || ticket.status === 'RESOLVED' ? 'text-green-500' : 'text-yellow-500'}`}>
                                      {ticket.status}
                                  </span>
                              </div>
                          </div>
                          <Button variant="secondary" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                              Manage
                          </Button>
                      </div>
                  ))}
              </div>
          </div>

          {/* RIGHT: Analytics Graph (Improved Visuals) */}
          <div className="w-full lg:w-[400px]">
              <Card className="bg-slate-900 border-slate-800 h-full sticky top-6 shadow-xl">
                  <CardHeader className="border-b border-slate-800 pb-4">
                      <CardTitle className="text-md text-white flex items-center gap-2">
                          <BarChart3 className="h-5 w-5 text-purple-500" /> 
                          Issue Category Analysis
                      </CardTitle>
                  </CardHeader>
                  <CardContent className="h-[400px] pt-6">
                      <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={getCategoryData()} layout="vertical" margin={{ left: 40, right: 20 }}>
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                              <XAxis type="number" hide />
                              <YAxis 
                                  dataKey="name" 
                                  type="category" 
                                  width={100} 
                                  tick={{fill: '#cbd5e1', fontSize: 12, fontWeight: 500}} 
                                  interval={0}
                                  axisLine={false}
                                  tickLine={false}
                              />
                              <Tooltip 
                                  cursor={{fill: '#1e293b', opacity: 0.4}}
                                  contentStyle={{backgroundColor: '#020617', border: '1px solid #1e293b', color: '#fff', borderRadius: '8px'}} 
                              />
                              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={32}>
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
              setFormData(prev => ({...prev, description: prev.description + " " + result.text}));
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
