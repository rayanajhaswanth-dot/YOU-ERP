import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { Search, AlertTriangle, Plus, MapPin, BarChart3, Clock, Mic, ChevronDown, ChevronUp, CheckCircle, AlertCircle, List, Play, Camera, Star, X, Image, Phone, User } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { toast } from "sonner";
import VoiceRecorder from '../components/VoiceRecorder';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../components/ui/collapsible";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// 11 GOVERNANCE CATEGORIES
const CATEGORIES = [
    "Water & Irrigation", "Agriculture", "Forests & Environment", 
    "Health & Sanitation", "Education", "Infrastructure & Roads", 
    "Law & Order", "Welfare Schemes", "Finance & Taxation", 
    "Urban & Rural Development", "Miscellaneous"
];

const CATEGORY_COLORS = {
    "Water & Irrigation": "#3b82f6", 
    "Agriculture": "#22c55e",
    "Health & Sanitation": "#ef4444",
    "Infrastructure & Roads": "#f97316",
    "Law & Order": "#a855f7",
    "Education": "#eab308",
    "Welfare Schemes": "#ec4899",
    "Forests & Environment": "#10b981",
    "Finance & Taxation": "#06b6d4",
    "Urban & Rural Development": "#8b5cf6",
    "Miscellaneous": "#64748b"
};

// KPI Card Component
const KpiCard = ({ title, value, icon: Icon, color }) => (
    <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-5 flex justify-between items-center">
            <div>
                <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">{title}</p>
                <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
            </div>
            <div className={`p-3 rounded-full bg-slate-800`}>
                <Icon className={`h-6 w-6 ${color}`} />
            </div>
        </CardContent>
    </Card>
);

// Grievance Detail Modal with 10-Step Workflow
const GrievanceModal = ({ grievance, onClose, onUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [photoUrl, setPhotoUrl] = useState('');

  if (!grievance) return null;

  const token = localStorage.getItem('token');
  const status = grievance.status?.toUpperCase();

  const handleStartWork = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/grievances/${grievance.id}/start-work`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        toast.success("Work started on grievance");
        onUpdate();
      } else {
        toast.error("Failed to start work");
      }
    } catch(e) {
      toast.error("Error: " + e.message);
    }
    setLoading(false);
  };

  const handleUploadPhoto = async () => {
    if (!photoUrl) {
      toast.error("Please enter a photo URL");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/grievances/${grievance.id}/upload-resolution-photo`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ resolution_image_url: photoUrl })
      });
      if (res.ok) {
        toast.success("Photo uploaded successfully");
        onUpdate();
      } else {
        toast.error("Failed to upload photo");
      }
    } catch(e) {
      toast.error("Error: " + e.message);
    }
    setLoading(false);
  };

  const handleResolve = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/grievances/${grievance.id}/resolve`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ send_notification: true })
      });
      if (res.ok) {
        toast.success("Grievance marked as resolved! Citizen will be notified.");
        onUpdate();
        onClose();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to resolve");
      }
    } catch(e) {
      toast.error("Error: " + e.message);
    }
    setLoading(false);
  };

  const statusColor = {
    'PENDING': 'bg-yellow-600',
    'IN_PROGRESS': 'bg-blue-600',
    'RESOLVED': 'bg-green-600',
    'ASSIGNED': 'bg-purple-600'
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Badge className={statusColor[status] || 'bg-slate-600'}>{status}</Badge>
              <Badge className={
                grievance.priority_level === 'CRITICAL' ? 'bg-red-600' : 
                grievance.priority_level === 'HIGH' ? 'bg-orange-600' : 
                grievance.priority_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-blue-600'
              }>{grievance.priority_level || 'LOW'}</Badge>
            </div>
            <h2 className="text-xl font-bold text-white">Ticket #{grievance.id?.slice(0,8).toUpperCase()}</h2>
            <p className="text-slate-400 text-sm">{grievance.category || grievance.issue_type}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-5 w-5 text-slate-400" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Citizen Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-2 text-slate-300">
              <User className="h-4 w-4 text-slate-500" />
              <span>{grievance.citizen_name || grievance.village || "Anonymous"}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Phone className="h-4 w-4 text-slate-500" />
              <span>{grievance.citizen_phone || "N/A"}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300 col-span-2">
              <MapPin className="h-4 w-4 text-slate-500" />
              <span>{grievance.location || grievance.village}</span>
            </div>
          </div>

          {/* Description */}
          <div>
            <Label className="text-slate-400 text-xs uppercase">Issue Description</Label>
            <p className="text-white mt-1 bg-slate-800 p-3 rounded-lg">{grievance.description}</p>
          </div>

          {/* Media */}
          {grievance.media_url && (
            <div>
              <Label className="text-slate-400 text-xs uppercase">Attached Media</Label>
              <div className="mt-1 bg-slate-800 p-2 rounded-lg">
                <a href={grievance.media_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline flex items-center gap-2">
                  <Image className="h-4 w-4" /> View Attachment
                </a>
              </div>
            </div>
          )}

          {/* Resolution Photo */}
          {grievance.resolution_image_url && (
            <div>
              <Label className="text-slate-400 text-xs uppercase">Resolution Photo ✓</Label>
              <div className="mt-1 bg-green-900/30 border border-green-800 p-2 rounded-lg">
                <a href={grievance.resolution_image_url} target="_blank" rel="noreferrer" className="text-green-400 hover:underline flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" /> View Resolution Photo
                </a>
              </div>
            </div>
          )}

          {/* Feedback Rating */}
          {grievance.feedback_rating && (
            <div>
              <Label className="text-slate-400 text-xs uppercase">Citizen Feedback</Label>
              <div className="mt-1 flex items-center gap-1">
                {[1,2,3,4,5].map(star => (
                  <Star key={star} className={`h-5 w-5 ${star <= grievance.feedback_rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'}`} />
                ))}
                <span className="text-white ml-2">{grievance.feedback_rating}/5</span>
              </div>
            </div>
          )}

          {/* 10-STEP WORKFLOW ACTIONS */}
          <div className="border-t border-slate-800 pt-6">
            <Label className="text-slate-400 text-xs uppercase mb-4 block">Workflow Actions</Label>
            
            {/* Step 8a: Start Work */}
            {status === 'PENDING' && (
              <Button 
                onClick={handleStartWork} 
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white mb-3"
              >
                <Play className="h-4 w-4 mr-2" /> Start Work
              </Button>
            )}

            {/* Step 8b: Upload Photo (required before resolve) */}
            {(status === 'IN_PROGRESS' || status === 'ASSIGNED') && !grievance.resolution_image_url && (
              <div className="space-y-2 mb-3">
                <div className="flex gap-2">
                  <Input 
                    placeholder="Enter resolution photo URL..." 
                    value={photoUrl}
                    onChange={(e) => setPhotoUrl(e.target.value)}
                    className="bg-slate-800 border-slate-700 text-white flex-1"
                  />
                  <Button 
                    onClick={handleUploadPhoto}
                    disabled={loading || !photoUrl}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    <Camera className="h-4 w-4 mr-2" /> Upload
                  </Button>
                </div>
                <p className="text-xs text-slate-500">Photo verification required before marking as resolved</p>
              </div>
            )}

            {/* Step 8c: Mark Resolved */}
            {(status === 'IN_PROGRESS' || status === 'ASSIGNED') && grievance.resolution_image_url && (
              <Button 
                onClick={handleResolve}
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 text-white"
              >
                <CheckCircle className="h-4 w-4 mr-2" /> Mark Resolved & Notify Citizen
              </Button>
            )}

            {status === 'RESOLVED' && (
              <div className="bg-green-900/30 border border-green-800 rounded-lg p-4 text-center">
                <CheckCircle className="h-8 w-8 text-green-400 mx-auto mb-2" />
                <p className="text-green-400 font-semibold">Grievance Resolved</p>
                {grievance.feedback_rating && (
                  <p className="text-slate-400 text-sm mt-1">Citizen rated: {grievance.feedback_rating}/5 stars</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const HelpPeople = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterText, setFilterText] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);
  const [selectedGrievance, setSelectedGrievance] = useState(null);

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
        const deadlineHours = formData.priority_level === 'CRITICAL' ? 4 : (formData.priority_level === 'HIGH' ? 24 : 168);
        const deadline = new Date(Date.now() + deadlineHours * 3600000).toISOString();

        const payload = { 
          ...formData, 
          status: 'pending', 
          deadline_timestamp: deadline 
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

  // KPIs
  const total = grievances.length;
  const resolved = grievances.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length;
  const pending = grievances.filter(g => g.status !== 'resolved' && g.status !== 'RESOLVED').length;
  const longPending = grievances.filter(g => {
      if (g.status === 'resolved' || g.status === 'RESOLVED') return false;
      return Math.ceil(Math.abs(new Date() - new Date(g.created_at)) / (86400000)) > 7;
  }).length;

  const topCritical = grievances
    .filter(g => g.priority_level === 'CRITICAL' && g.status !== 'resolved' && g.status !== 'RESOLVED')
    .slice(0, 3);

  // Filtered List
  const filteredList = grievances.filter(g => 
    (g.citizen_name || g.village || "").toLowerCase().includes(filterText.toLowerCase()) ||
    (g.category || g.issue_type || "").toLowerCase().includes(filterText.toLowerCase())
  );

  // Sorted List
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

  const getGraphData = () => {
      const counts = {};
      grievances.forEach(g => {
          const cat = g.category || g.issue_type || "Miscellaneous";
          counts[cat] = (counts[cat] || 0) + 1;
      });
      return Object.keys(counts).map(k => ({ name: k, count: counts[k] })).sort((a,b) => b.count - a.count).slice(0, 5);
  };

  return (
    <div className="p-6 space-y-8 text-white">
      
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <AlertTriangle className="h-8 w-8 text-orange-500" />
          <div>
            <h1 className="text-3xl font-bold">Help People Console</h1>
            <p className="text-slate-400 text-sm">Citizen Grievance Redressal • 10-Step Workflow</p>
          </div>
      </div>

      {/* 1. KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KpiCard title="Total" value={total} icon={List} color="text-blue-400" />
          <KpiCard title="Resolved" value={resolved} icon={CheckCircle} color="text-green-400" />
          <KpiCard title="Pending" value={pending} icon={Clock} color="text-yellow-400" />
          <KpiCard title="Long Pending (>7 Days)" value={longPending} icon={AlertCircle} color="text-red-400" />
      </div>

      {/* 2. Top 3 Critical */}
      <div>
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2 mb-3">Priority 1: Unresolved Critical</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topCritical.length > 0 ? topCritical.map(issue => (
                  <Card 
                    key={issue.id} 
                    className="bg-red-950/20 border-red-900/50 border relative overflow-hidden cursor-pointer hover:border-red-700 transition-all"
                    onClick={() => setSelectedGrievance(issue)}
                  >
                      <div className="absolute top-0 right-0 p-2 opacity-20"><AlertTriangle className="h-16 w-16 text-red-500" /></div>
                      <CardHeader className="pb-2">
                          <div className="flex justify-between">
                            <Badge className="bg-red-600 text-white">CRITICAL</Badge>
                            <span className="text-xs text-red-300 font-mono">#{issue.id?.slice(0,6)}</span>
                          </div>
                          <CardTitle className="text-white text-md mt-2 line-clamp-1">{issue.category || issue.issue_type}</CardTitle>
                      </CardHeader>
                      <CardContent>
                          <p className="text-slate-300 text-sm line-clamp-2">{issue.description}</p>
                          <div className="flex items-center gap-2 text-xs text-slate-500 mt-2"><MapPin className="h-3 w-3" /> {issue.location || issue.village}</div>
                      </CardContent>
                  </Card>
              )) : <div className="col-span-3 p-4 text-center text-slate-500 border border-dashed border-slate-800 rounded">No critical issues.</div>}
          </div>
      </div>

      {/* 3. Add Entry (Collapsible) */}
      <Collapsible open={isAddOpen} onOpenChange={setIsAddOpen} className="border border-slate-700/50 rounded-xl bg-slate-900 shadow-md">
          <CollapsibleTrigger className="w-full">
              <div className="flex items-center justify-between p-5 cursor-pointer hover:bg-slate-800/50 transition-all">
                  <h3 className="text-white font-bold flex items-center gap-3"><Plus className="h-5 w-5 text-blue-500" /> Register New Grievance</h3>
                  {isAddOpen ? <ChevronUp className="text-slate-400" /> : <ChevronDown className="text-slate-400" />}
              </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
              <div className="p-6 border-t border-slate-800 space-y-4 bg-slate-950">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div><Label className="text-white">Name</Label><Input className="bg-slate-900 border-slate-700 text-white" value={formData.citizen_name} onChange={e => setFormData({...formData, citizen_name: e.target.value})} /></div>
                      <div><Label className="text-white">Contact</Label><Input className="bg-slate-900 border-slate-700 text-white" value={formData.citizen_phone} onChange={e => setFormData({...formData, citizen_phone: e.target.value})} /></div>
                      <div><Label className="text-white">Area</Label><Input className="bg-slate-900 border-slate-700 text-white" value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} /></div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                          <Label className="text-white">Category</Label>
                          <Select value={formData.category} onValueChange={(val) => {
                              const p = getCategoryPriority(val);
                              setFormData({...formData, category: val, priority_level: p});
                          }}>
                              <SelectTrigger className="bg-slate-900 border-slate-700 text-white"><SelectValue placeholder="Select" /></SelectTrigger>
                              <SelectContent className="bg-slate-900 border-slate-800 text-white max-h-[250px]">
                                  {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
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
                      <div className="relative">
                          <Label className="text-white">Description</Label>
                          <Textarea className="bg-slate-900 border-slate-700 text-white h-24 pr-12" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
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
                  <Button onClick={handleRegister} className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold">Register Ticket</Button>
              </div>
          </CollapsibleContent>
      </Collapsible>

      {/* 4. Search & Filter */}
      <div className="flex gap-4 items-center bg-slate-900/50 p-4 rounded-xl border border-slate-800">
          <Search className="h-4 w-4 text-slate-500" />
          <Input className="bg-transparent border-none text-white focus-visible:ring-0" placeholder="Search..." value={filterText} onChange={e => setFilterText(e.target.value)} />
          <Select onValueChange={setSortBy} defaultValue="priority">
            <SelectTrigger className="w-[130px] bg-slate-950 border-slate-700 text-white text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="priority">Priority</SelectItem>
              <SelectItem value="date">Date</SelectItem>
            </SelectContent>
          </Select>
      </div>

      {/* 5. Split View */}
      <div className="flex flex-col lg:flex-row gap-6 min-h-[500px]">
          {/* List */}
          <div className="flex-1 space-y-3 max-h-[600px] overflow-y-auto pr-2">
              {sortedList.map(t => (
                  <div 
                    key={t.id} 
                    className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center hover:bg-slate-800/50 cursor-pointer transition-all"
                    onClick={() => setSelectedGrievance(t)}
                  >
                      <div className="flex-1">
                          <div className="flex items-center gap-3 flex-wrap">
                              <span className="text-white font-semibold">{t.citizen_name || t.village?.split('(')[0] || "Anonymous"}</span>
                              <Badge variant="outline" className="text-slate-400 border-slate-700">{t.category || t.issue_type}</Badge>
                              <Badge className={
                                t.priority_level === 'CRITICAL' ? 'bg-red-600' : 
                                t.priority_level === 'HIGH' ? 'bg-orange-600' : 
                                t.priority_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-blue-600'
                              }>{t.priority_level || 'LOW'}</Badge>
                              {t.feedback_rating && (
                                <Badge className="bg-yellow-600 flex items-center gap-1">
                                  <Star className="h-3 w-3" /> {t.feedback_rating}/5
                                </Badge>
                              )}
                          </div>
                          <p className="text-sm text-slate-400 mt-1 line-clamp-1">{t.description}</p>
                          <div className="flex gap-4 mt-2 text-xs text-slate-500">
                            <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {t.location || t.village?.split('(')[0]}</span>
                            <span className={`uppercase font-bold ${
                              t.status === 'RESOLVED' || t.status === 'resolved' ? 'text-green-500' : 
                              t.status === 'IN_PROGRESS' ? 'text-blue-500' : 'text-yellow-500'
                            }`}>{t.status}</span>
                            {t.resolution_image_url && <span className="text-green-400 flex items-center gap-1"><Camera className="h-3 w-3" /> Verified</span>}
                          </div>
                      </div>
                      <Button variant="secondary" size="sm" className="bg-slate-800 ml-4">Manage</Button>
                  </div>
              ))}
          </div>
          
          {/* Graph */}
          <div className="w-full lg:w-[450px]">
              <Card className="bg-slate-900 border-slate-800 h-full">
                  <CardHeader className="border-b border-slate-800 pb-2"><CardTitle className="text-white text-sm flex gap-2"><BarChart3 className="h-4 w-4 text-purple-500"/> Sector Analysis</CardTitle></CardHeader>
                  <CardContent className="h-[400px] pt-4">
                      <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={getGraphData()} layout="vertical" margin={{left:10}}>
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                              <XAxis type="number" hide />
                              <YAxis dataKey="name" type="category" width={120} tick={{fill:'#e2e8f0', fontSize:11}} interval={0} axisLine={false} tickLine={false} />
                              <Tooltip cursor={{fill:'#1e293b', opacity:0.4}} contentStyle={{backgroundColor:'#020617', border:'1px solid #1e293b', color:'#fff'}} />
                              <Bar dataKey="count" radius={[0,4,4,0]} barSize={24}>
                                  {getGraphData().map((e,i) => <Cell key={i} fill={CATEGORY_COLORS[e.name] || '#64748b'} />)}
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

      {/* Grievance Detail Modal */}
      {selectedGrievance && (
        <GrievanceModal 
          grievance={selectedGrievance}
          onClose={() => setSelectedGrievance(null)}
          onUpdate={() => {
            fetchGrievances();
            // Refresh the selected grievance
            const token = localStorage.getItem('token');
            fetch(`${BACKEND_URL}/api/grievances/${selectedGrievance.id}`, {
              headers: { 'Authorization': `Bearer ${token}` }
            }).then(r => r.json()).then(data => setSelectedGrievance(data)).catch(() => {});
          }}
        />
      )}
    </div>
  );
};

export default HelpPeople;
