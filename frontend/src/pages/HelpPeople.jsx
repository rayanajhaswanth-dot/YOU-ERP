import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { Search, Filter, AlertTriangle, Plus, MapPin, BarChart3, Clock, Mic } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { toast } from "sonner";
import VoiceRecorder from '../components/VoiceRecorder';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const HelpPeople = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterText, setFilterText] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);

  // Form State (Logic 11)
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
        
        // Auto-calculate timestamp
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
        } else {
            toast.error("Registration Failed");
        }
    } catch(e) {
        toast.error("Registration Failed", { description: e.message });
    }
  };

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
      return Object.keys(counts)
        .map(key => ({ name: key, count: counts[key] }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 4);
  };

  // Filtering
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
      <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-orange-500" />
              Help People Console
          </h1>
          <p className="text-slate-400 mt-1">Grievance Redressal & Citizen Support</p>
      </div>

      {/* 1. KPIs: TOP 3 PRIORITY ISSUES */}
      <div className="space-y-3">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2">
              Priority 1: Unresolved Critical Issues
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topCritical.length > 0 ? topCritical.map((issue) => (
                  <Card key={issue.id} className="bg-red-950/10 border-red-900/50 border relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-2 opacity-20">
                          <AlertTriangle className="h-16 w-16 text-red-500" />
                      </div>
                      <CardHeader className="pb-2">
                          <div className="flex justify-between">
                              <Badge className="bg-red-600 text-white">CRITICAL</Badge>
                              <span className="text-xs text-red-300 font-mono">#{issue.id.slice(0,6)}</span>
                          </div>
                          <CardTitle className="text-white text-md mt-2 line-clamp-1">{issue.category || issue.issue_type}</CardTitle>
                      </CardHeader>
                      <CardContent>
                          <p className="text-slate-400 text-sm line-clamp-2 mb-2">{issue.description}</p>
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                              <MapPin className="h-3 w-3" /> {issue.location || issue.village}
                          </div>
                      </CardContent>
                  </Card>
              )) : (
                  <div className="col-span-3 p-6 border border-dashed border-slate-800 rounded-lg text-center text-slate-500 italic">
                      No critical issues pending. All clear.
                  </div>
              )}
          </div>
      </div>

      {/* 2. ADD ENTRY FORM (Logic 11) */}
      <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3 border-b border-slate-800 bg-slate-900/50">
              <CardTitle className="text-white flex items-center gap-2">
                  <Plus className="h-5 w-5 text-blue-500" /> 
                  Register New Grievance
              </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                      <Label>Complainant Name</Label>
                      <Input 
                          className="bg-slate-950 border-slate-800" 
                          placeholder="Full Name"
                          value={formData.citizen_name}
                          onChange={(e) => setFormData({...formData, citizen_name: e.target.value})}
                      />
                  </div>
                  <div className="space-y-2">
                      <Label>Contact Number</Label>
                      <Input 
                          className="bg-slate-950 border-slate-800" 
                          placeholder="+91..."
                          value={formData.citizen_phone}
                          onChange={(e) => setFormData({...formData, citizen_phone: e.target.value})}
                      />
                  </div>
                  <div className="space-y-2">
                      <Label>Area / Ward</Label>
                      <Input 
                          className="bg-slate-950 border-slate-800" 
                          placeholder="e.g. Ward 5, Gandhi Nagar"
                          value={formData.location}
                          onChange={(e) => setFormData({...formData, location: e.target.value})}
                      />
                  </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                      <Label>Issue Category</Label>
                      <Select onValueChange={(val) => {
                          let p = "MEDIUM";
                          if(["Electricity", "Safety", "Fire"].includes(val)) p = "CRITICAL";
                          if(["Water", "Sewage"].includes(val)) p = "HIGH";
                          setFormData({...formData, category: val, priority_level: p});
                      }}>
                          <SelectTrigger className="bg-slate-950 border-slate-800"><SelectValue placeholder="Select Category" /></SelectTrigger>
                          <SelectContent>
                              <SelectItem value="Electricity">Electricity</SelectItem>
                              <SelectItem value="Water">Water Supply</SelectItem>
                              <SelectItem value="Safety">Public Safety / Fire</SelectItem>
                              <SelectItem value="Roads">Roads & Infrastructure</SelectItem>
                              <SelectItem value="Sanitation">Sanitation</SelectItem>
                              <SelectItem value="Welfare">Welfare Scheme</SelectItem>
                              <SelectItem value="General">General</SelectItem>
                          </SelectContent>
                      </Select>
                  </div>
                  <div className="space-y-2">
                      <Label>Priority Level (Auto)</Label>
                      <div className={`p-2 border rounded text-sm font-bold ${
                        formData.priority_level === 'CRITICAL' ? 'bg-red-950 border-red-800 text-red-400' :
                        formData.priority_level === 'HIGH' ? 'bg-orange-950 border-orange-800 text-orange-400' :
                        'bg-slate-950 border-slate-800 text-slate-400'
                      }`}>
                          {formData.priority_level}
                      </div>
                  </div>
                  <div className="space-y-2 flex items-end">
                       <div className="w-full">
                          <Label className="mb-2 block">Voice Input</Label>
                          <Button 
                            onClick={() => setShowVoiceRecorder(true)}
                            variant="outline"
                            className="w-full bg-slate-950 border-slate-700 hover:bg-slate-800"
                          >
                            <Mic className="h-4 w-4 mr-2" /> Record Voice
                          </Button>
                       </div>
                  </div>
              </div>

              <div className="space-y-2">
                  <Label>Issue Description</Label>
                  <Textarea 
                      className="bg-slate-950 border-slate-800 h-20" 
                      placeholder="Detailed description of the grievance..."
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                  />
              </div>

              <div className="flex justify-end">
                  <Button onClick={handleRegister} className="bg-orange-500 hover:bg-orange-600 text-white font-bold px-8">
                      Register & Assign Ticket
                  </Button>
              </div>
          </CardContent>
      </Card>

      {/* 3. SEARCH & FILTERS */}
      <div className="flex gap-4 items-center bg-slate-900 p-4 rounded-lg border border-slate-800">
          <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-500" />
              <Input 
                  className="pl-10 bg-slate-950 border-slate-800" 
                  placeholder="Search by Name, Category, ID..."
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
              />
          </div>
          <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-500" />
              <Select onValueChange={setSortBy} defaultValue="priority">
                  <SelectTrigger className="w-[150px] bg-slate-950 border-slate-800"><SelectValue /></SelectTrigger>
                  <SelectContent>
                      <SelectItem value="priority">Sort by Priority</SelectItem>
                      <SelectItem value="date">Sort by Date</SelectItem>
                      <SelectItem value="status">Sort by Status</SelectItem>
                  </SelectContent>
              </Select>
          </div>
      </div>

      {/* 4. SPLIT VIEW: LIST + ANALYTICS */}
      <div className="flex flex-col lg:flex-row gap-6">
          
          {/* LEFT: All Grievances List */}
          <div className="flex-1 space-y-4">
              <h3 className="text-white font-bold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-500" /> All Grievances ({sortedList.length})
              </h3>
              <div className="grid gap-3 max-h-[600px] overflow-y-auto pr-2">
                  {sortedList.map((ticket) => (
                      <div key={ticket.id} className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center hover:border-slate-700 transition-colors">
                          <div>
                              <div className="flex items-center gap-3">
                                  <span className="text-white font-medium">{ticket.citizen_name || ticket.village || "Anonymous"}</span>
                                  <Badge variant="outline" className="text-[10px] text-slate-400">{ticket.category || ticket.issue_type}</Badge>
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
                                  <span>{ticket.location || ticket.village}</span>
                                  <span>ID: {ticket.id?.slice(0,8)}</span>
                                  <span>Status: <span className="text-white uppercase">{ticket.status}</span></span>
                              </div>
                          </div>
                          <Button variant="secondary" size="sm" className="shrink-0">
                              View
                          </Button>
                      </div>
                  ))}
              </div>
          </div>

          {/* RIGHT: Analytics Graph */}
          <div className="w-full lg:w-[400px]">
              <Card className="bg-slate-900 border-slate-800 h-fit sticky top-6">
                  <CardHeader>
                      <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                          <BarChart3 className="h-4 w-4" /> Issue Analysis (Top 4)
                      </CardTitle>
                  </CardHeader>
                  <CardContent className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={getCategoryData()} layout="vertical" margin={{ left: 20 }}>
                              <XAxis type="number" hide />
                              <YAxis 
                                  dataKey="name" 
                                  type="category" 
                                  width={100} 
                                  tick={{fill: '#94a3b8', fontSize: 11}} 
                                  interval={0}
                              />
                              <Tooltip 
                                  cursor={{fill: 'transparent'}}
                                  contentStyle={{backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#fff'}} 
                              />
                              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20}>
                                  {getCategoryData().map((entry, index) => (
                                      <Cell key={`cell-${index}`} fill={['#ef4444', '#f97316', '#eab308', '#22c55e'][index % 4]} />
                                  ))}
                              </Bar>
                          </BarChart>
                      </ResponsiveContainer>
                  </CardContent>
              </Card>
          </div>

      </div>

    </div>
  );
};

export default HelpPeople;
