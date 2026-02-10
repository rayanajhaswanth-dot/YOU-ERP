import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { Search, AlertTriangle, Plus, MapPin, BarChart3, Clock, Mic, ChevronDown, ChevronUp, CheckCircle, AlertCircle, List, Play, Camera, Star, X, Image, Phone, User, Upload, Calendar, Filter, FileText } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { toast } from "sonner";
import VoiceRecorder from '../components/VoiceRecorder';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../components/ui/collapsible";
import { api } from '../utils/safeFetch';

// 11 GOVERNANCE CATEGORIES (English Standard)
const CATEGORIES = [
    "Water & Irrigation", "Agriculture", "Forests & Environment", 
    "Health & Sanitation", "Education", "Infrastructure & Roads", 
    "Law & Order", "Welfare Schemes", "Finance & Taxation", 
    "Urban & Rural Development", "Electricity", "Miscellaneous"
];

// Geographical Hierarchy Options
const GEO_TYPES = [
    "All Areas", "Mandal", "Village", "Panchayat", "Town", "Ward", "Division", "City"
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
    "Electricity": "#fbbf24",
    "Miscellaneous": "#64748b",
    "General": "#64748b",
    "Emergency": "#dc2626"
};

// Format date and time
const formatDateTime = (isoString) => {
    if (!isoString) return { date: '-', time: '-' };
    const dt = new Date(isoString);
    return {
        date: dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
        time: dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
    };
};

// Normalize category to English (11 Official Categories)
const normalizeCategory = (category) => {
    if (!category) return "Miscellaneous";
    
    const normalized = category.trim();
    
    // Direct match with official categories
    if (CATEGORIES.includes(normalized)) return normalized;
    
    // Map common variations to official categories
    const categoryLower = normalized.toLowerCase();
    
    const mappings = {
        // General/Other → Miscellaneous
        "general": "Miscellaneous",
        "other": "Miscellaneous",
        "others": "Miscellaneous",
        "misc": "Miscellaneous",
        
        // Water
        "water": "Water & Irrigation",
        "irrigation": "Water & Irrigation",
        "drinking water": "Water & Irrigation",
        
        // Health
        "health": "Health & Sanitation",
        "hospital": "Health & Sanitation",
        "medical": "Health & Sanitation",
        "sanitation": "Health & Sanitation",
        
        // Roads
        "road": "Infrastructure & Roads",
        "roads": "Infrastructure & Roads",
        "infrastructure": "Infrastructure & Roads",
        "road repair": "Infrastructure & Roads",
        
        // Power
        "power": "Electricity",
        "current": "Electricity",
        "electric": "Electricity",
        
        // Law
        "police": "Law & Order",
        "crime": "Law & Order",
        "safety": "Law & Order",
        
        // Welfare
        "pension": "Welfare Schemes",
        "ration": "Welfare Schemes",
        "scheme": "Welfare Schemes",
        "welfare": "Welfare Schemes",
        
        // Education
        "school": "Education",
        "college": "Education",
        
        // Agriculture
        "farming": "Agriculture",
        "farmer": "Agriculture",
        "crop": "Agriculture",
        
        // Environment
        "forest": "Forests & Environment",
        "environment": "Forests & Environment",
        "pollution": "Forests & Environment",
        
        // Finance
        "tax": "Finance & Taxation",
        "finance": "Finance & Taxation",
        
        // Development
        "urban": "Urban & Rural Development",
        "rural": "Urban & Rural Development",
        "development": "Urban & Rural Development",
        "municipal": "Urban & Rural Development",
    };
    
    // Check for keyword matches
    for (const [key, official] of Object.entries(mappings)) {
        if (categoryLower.includes(key)) {
            return official;
        }
    }
    
    // Case-insensitive check against official categories
    for (const official of CATEGORIES) {
        if (official.toLowerCase() === categoryLower) {
            return official;
        }
    }
    
    return normalized;
};

// KPI Card Component
const KpiCard = ({ title, value, icon: Icon, color, subtitle }) => (
    <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-5 flex justify-between items-center">
            <div>
                <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">{title}</p>
                <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
                {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
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
  const [uploadMethod, setUploadMethod] = useState('file');
  const [photoUrl, setPhotoUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  if (!grievance) return null;

  const status = grievance.status?.toUpperCase();
  const { date, time } = formatDateTime(grievance.created_at);
  const displayCategory = normalizeCategory(grievance.category || grievance.issue_type);

  const handleStartWork = async () => {
    setLoading(true);
    try {
      const result = await api.put(`/api/grievances/${grievance.id}/start-work`, {});
      if (result.ok) {
        toast.success("Work started on grievance");
        onUpdate();
      } else {
        toast.error(result.error || "Failed to start work");
      }
    } catch(e) {
      toast.error("Error: " + e.message);
    }
    setLoading(false);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
        toast.error("Please select an image or PDF file");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error("File size must be less than 10MB");
        return;
      }
      setSelectedFile(file);
      toast.success(`Selected: ${file.name}`);
    }
  };

  const handleUploadPhoto = async () => {
    setLoading(true);
    try {
      if (uploadMethod === 'file' && selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        const result = await api.upload(`/api/grievances/${grievance.id}/upload-file`, formData);
        
        if (result.ok) {
          toast.success("Photo uploaded successfully!");
          setSelectedFile(null);
          onUpdate();
        } else {
          toast.error(result.error || "Failed to upload photo");
        }
      } else if (uploadMethod === 'url' && photoUrl) {
        const result = await api.put(`/api/grievances/${grievance.id}/upload-resolution-photo`, { resolution_image_url: photoUrl });
        
        if (result.ok) {
          toast.success("Photo URL saved!");
          setPhotoUrl('');
          onUpdate();
        } else {
          toast.error(result.error || "Failed to save photo URL");
        }
      } else {
        toast.error("Please select a file or enter a URL");
      }
    } catch(e) {
      toast.error("Error: " + e.message);
    }
    setLoading(false);
  };

  const handleResolve = async () => {
    setLoading(true);
    try {
      const result = await api.put(`/api/grievances/${grievance.id}/resolve`, { send_notification: true });
      if (result.ok) {
        toast.success("Grievance resolved! Citizen notified.");
        onUpdate();
        onClose();
      } else {
        toast.error(result.error || "Failed to resolve");
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
            <p className="text-slate-400 text-sm">{displayCategory}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-5 w-5 text-slate-400" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Timestamp Display - NEW */}
          <div className="flex items-center gap-4 text-sm bg-slate-800/50 p-3 rounded-lg">
            <div className="flex items-center gap-2 text-slate-300">
              <Calendar className="h-4 w-4 text-orange-500" />
              <span className="font-semibold">{date}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Clock className="h-4 w-4 text-orange-500" />
              <span className="font-semibold">{time}</span>
            </div>
          </div>

          {/* Standardized Format Display */}
          <div className="space-y-3 bg-slate-800/30 p-4 rounded-lg border border-slate-700">
            <p className="text-xs text-orange-500 uppercase font-bold mb-3">Grievance Details (Standardized Format)</p>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-500 text-xs">Name of the Person</Label>
                <p className="text-white font-medium">{grievance.citizen_name || "Anonymous"}</p>
              </div>
              <div>
                <Label className="text-slate-500 text-xs">Contact Number</Label>
                <p className="text-white font-medium">{grievance.citizen_phone || "N/A"}</p>
              </div>
            </div>
            
            <div>
              <Label className="text-slate-500 text-xs">Area (Mandal/Village/Town/Ward/Division)</Label>
              <p className="text-white font-medium">{grievance.village || grievance.location || "Not specified"}</p>
            </div>
            
            <div>
              <Label className="text-slate-500 text-xs">Issue Category</Label>
              <Badge 
                className="mt-1"
                style={{ backgroundColor: CATEGORY_COLORS[displayCategory] || '#64748b' }}
              >
                {displayCategory}
              </Badge>
            </div>
            
            <div>
              <Label className="text-slate-500 text-xs">Issue Description</Label>
              <p className="text-white mt-1 bg-slate-800 p-3 rounded-lg whitespace-pre-wrap">{grievance.description}</p>
            </div>
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

          {/* Workflow Actions */}
          <div className="border-t border-slate-800 pt-6">
            <Label className="text-slate-400 text-xs uppercase mb-4 block">Workflow Actions</Label>
            
            {status === 'PENDING' && (
              <Button onClick={handleStartWork} disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white mb-3">
                <Play className="h-4 w-4 mr-2" /> Start Work
              </Button>
            )}

            {(status === 'IN_PROGRESS' || status === 'ASSIGNED') && !grievance.resolution_image_url && (
              <div className="space-y-3 mb-3 bg-slate-800 p-4 rounded-lg">
                <Label className="text-white text-sm">Upload Resolution Photo</Label>
                
                <div className="flex gap-2">
                  <Button 
                    variant={uploadMethod === 'file' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setUploadMethod('file')}
                    className={uploadMethod === 'file' ? 'bg-orange-600' : 'border-slate-600'}
                  >
                    <Upload className="h-4 w-4 mr-1" /> From Device
                  </Button>
                  <Button 
                    variant={uploadMethod === 'url' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setUploadMethod('url')}
                    className={uploadMethod === 'url' ? 'bg-orange-600' : 'border-slate-600'}
                  >
                    <Image className="h-4 w-4 mr-1" /> From URL
                  </Button>
                </div>
                
                {uploadMethod === 'file' ? (
                  <div className="space-y-2">
                    <input type="file" ref={fileInputRef} onChange={handleFileSelect} accept="image/*,application/pdf" className="hidden" />
                    <div onClick={() => fileInputRef.current?.click()} className="border-2 border-dashed border-slate-600 rounded-lg p-6 text-center cursor-pointer hover:border-orange-500 transition-colors">
                      {selectedFile ? (
                        <div className="text-green-400">
                          <CheckCircle className="h-8 w-8 mx-auto mb-2" />
                          <p className="font-medium">{selectedFile.name}</p>
                          <p className="text-xs text-slate-400">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                        </div>
                      ) : (
                        <div className="text-slate-400">
                          <Camera className="h-8 w-8 mx-auto mb-2" />
                          <p>Click to select photo/PDF</p>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <Input placeholder="Enter photo URL..." value={photoUrl} onChange={(e) => setPhotoUrl(e.target.value)} className="bg-slate-900 border-slate-700 text-white" />
                )}
                
                <Button onClick={handleUploadPhoto} disabled={loading || (uploadMethod === 'file' ? !selectedFile : !photoUrl)} className="w-full bg-purple-600 hover:bg-purple-700">
                  <Upload className="h-4 w-4 mr-2" /> {loading ? 'Uploading...' : 'Upload Photo'}
                </Button>
              </div>
            )}

            {(status === 'IN_PROGRESS' || status === 'ASSIGNED') && grievance.resolution_image_url && (
              <Button onClick={handleResolve} disabled={loading} className="w-full bg-green-600 hover:bg-green-700 text-white">
                <CheckCircle className="h-4 w-4 mr-2" /> Mark Resolved & Notify Citizen
              </Button>
            )}

            {status === 'RESOLVED' && (
              <div className="bg-green-900/30 border border-green-800 rounded-lg p-4 text-center">
                <CheckCircle className="h-8 w-8 text-green-400 mx-auto mb-2" />
                <p className="text-green-400 font-semibold">Grievance Resolved</p>
                {grievance.feedback_rating && <p className="text-slate-400 text-sm mt-1">Citizen rated: {grievance.feedback_rating}/5 stars</p>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Help People Component
const HelpPeople = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterText, setFilterText] = useState("");
  const [filterCategory, setFilterCategory] = useState("All");
  const [filterGeoType, setFilterGeoType] = useState("All Areas");
  const [filterPriority, setFilterPriority] = useState("All");
  const [sortBy, setSortBy] = useState("date");
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);
  const [selectedGrievance, setSelectedGrievance] = useState(null);
  const [mediaFile, setMediaFile] = useState(null);
  const mediaInputRef = useRef(null);

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
      const result = await api.get('/api/grievances/');
      if (result.ok) {
        setGrievances(result.data);
      } else {
        console.error('Failed to fetch grievances:', result.error);
        toast.error('Failed to load grievances');
      }
    } catch(e) { 
      console.error(e); 
      toast.error('Error loading grievances');
    } 
    finally { setLoading(false); }
  };

  // Delete grievance handler
  const handleDeleteGrievance = async (grievanceId, e) => {
    e.stopPropagation(); // Prevent card click
    
    if (!window.confirm("Are you sure you want to delete this grievance? This action cannot be undone.")) {
      return;
    }
    
    try {
      const result = await api.delete(`/api/grievances/${grievanceId}`);
      
      if (result.ok) {
        toast.success("Grievance deleted successfully");
        fetchGrievances(); // Refresh list
      } else {
        toast.error(result.error || "Failed to delete grievance");
      }
    } catch (e) {
      toast.error("Error deleting grievance: " + e.message);
    }
  };

  const handleMediaSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
        toast.error("Please select an image or PDF file");
        return;
      }
      setMediaFile(file);
      toast.success(`Attached: ${file.name}`);
      
      // If it's a PDF or image, extract info using AI
      if (file.type === 'application/pdf' || file.type.startsWith('image/')) {
        toast.info("Processing document with AI...");
        try {
          const extractFormData = new FormData();
          extractFormData.append('file', file);
          
          // Use the appropriate endpoint based on file type
          const endpoint = file.type.startsWith('image/') 
            ? '/api/ai/analyze_image' 
            : '/api/ai/extract_from_media';
          
          const result = await api.upload(endpoint, extractFormData);
          
          if (result.ok && result.data?.success && result.data?.data) {
            const extracted = result.data.data;
            
            // Auto-fill form with extracted data
            setFormData(prev => ({
              ...prev,
              citizen_name: extracted.name || prev.citizen_name,
              citizen_phone: extracted.contact || prev.citizen_phone,
              location: extracted.area || prev.location,
              category: extracted.category || prev.category,
              description: extracted.description || prev.description,
              priority_level: extracted.urgency || getCategoryPriority(extracted.category || prev.category)
            }));
            
            toast.success("Document processed! Form auto-filled with extracted data.");
          } else {
            toast.info("Could not auto-extract info. Please fill the form manually.");
          }
        } catch (err) {
          console.error("AI extraction error:", err);
          toast.info("Could not auto-extract info. Please fill the form manually.");
        }
      }
    }
  };

  const handleRegister = async () => {
    try {
        const deadlineHours = formData.priority_level === 'CRITICAL' ? 4 : (formData.priority_level === 'HIGH' ? 24 : 168);
        const deadline = new Date(Date.now() + deadlineHours * 3600000).toISOString();

        const payload = { 
          ...formData, 
          status: 'PENDING', 
          deadline_timestamp: deadline,
          village: formData.location // Map location to village field
        };

        const result = await api.post('/api/grievances/', payload);

        if (result.ok) {
            const newGrievance = result.data;
            
            // Upload media if attached
            if (mediaFile && newGrievance.id) {
              const formDataMedia = new FormData();
              formDataMedia.append('file', mediaFile);
              
              await api.upload(`/api/grievances/${newGrievance.id}/upload-file`, formDataMedia);
            }
            
            toast.success("Grievance Registered Successfully");
            setFormData({ citizen_name: "", citizen_phone: "", location: "", category: "Miscellaneous", description: "", priority_level: "MEDIUM" });
            setMediaFile(null);
            fetchGrievances();
            setIsAddOpen(false);
        } else {
            toast.error(result.error || "Registration Failed");
        }
    } catch(e) { toast.error("Registration Failed: " + e.message); }
  };

  const getCategoryPriority = (category) => {
    if (["Law & Order", "Health & Sanitation", "Electricity"].includes(category)) return "CRITICAL";
    if (["Water & Irrigation", "Infrastructure & Roads", "Agriculture"].includes(category)) return "HIGH";
    if (["Welfare Schemes", "Education"].includes(category)) return "MEDIUM";
    return "LOW";
  };

  // KPIs
  const total = grievances.length;
  const resolved = grievances.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length;
  const pending = grievances.filter(g => g.status !== 'resolved' && g.status !== 'RESOLVED').length;
  const critical = grievances.filter(g => g.priority_level === 'CRITICAL' && g.status !== 'resolved' && g.status !== 'RESOLVED').length;

  const topCritical = grievances
    .filter(g => g.priority_level === 'CRITICAL' && g.status !== 'resolved' && g.status !== 'RESOLVED')
    .slice(0, 3);

  // Filtered List with enhanced filters
  const filteredList = grievances.filter(g => {
    // Text search
    const searchText = filterText.toLowerCase();
    const textMatch = !filterText || 
      (g.citizen_name || '').toLowerCase().includes(searchText) ||
      (g.village || '').toLowerCase().includes(searchText) ||
      (g.description || '').toLowerCase().includes(searchText);
    
    // Category filter
    const categoryMatch = filterCategory === "All" || normalizeCategory(g.category || g.issue_type) === filterCategory;
    
    // Priority filter
    const priorityMatch = filterPriority === "All" || g.priority_level === filterPriority;
    
    // Geo-type filter (based on area naming patterns)
    let geoMatch = true;
    if (filterGeoType !== "All Areas") {
      const area = (g.village || g.location || '').toLowerCase();
      const geoPatterns = {
        "Mandal": ["mandal", "mandalam", "మండలం", "मंडल"],
        "Village": ["village", "గ్రామం", "grama", "gram", "गांव", "gaon"],
        "Panchayat": ["panchayat", "పంచాయతీ", "पंचायत"],
        "Town": ["town", "పట్టణం", "नगर", "nagar"],
        "Ward": ["ward", "వార్డు", "वार्ड"],
        "Division": ["division", "విభాగం", "डिवीजन"],
        "City": ["city", "నగరం", "शहर", "shahar"]
      };
      const patterns = geoPatterns[filterGeoType] || [];
      geoMatch = patterns.some(p => area.includes(p));
    }
    
    return textMatch && categoryMatch && priorityMatch && geoMatch;
  });

  // Sorted List
  const sortedList = [...filteredList].sort((a, b) => {
    if (sortBy === "priority") {
      const priorityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      return (priorityOrder[a.priority_level] || 3) - (priorityOrder[b.priority_level] || 3);
    }
    return new Date(b.created_at) - new Date(a.created_at);
  });

  // Graph data - ALWAYS in English
  const getGraphData = () => {
      const counts = {};
      grievances.forEach(g => {
          const cat = normalizeCategory(g.category || g.issue_type);
          counts[cat] = (counts[cat] || 0) + 1;
      });
      return Object.keys(counts).map(k => ({ name: k, count: counts[k] })).sort((a,b) => b.count - a.count).slice(0, 6);
  };

  return (
    <div className="p-6 space-y-6 text-white" data-testid="help-people-page">
      
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <AlertTriangle className="h-8 w-8 text-orange-500" />
          <div>
            <h1 className="text-3xl font-bold">Help People Console</h1>
            <p className="text-slate-400 text-sm">Citizen Grievance Redressal • 10-Step Workflow</p>
          </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KpiCard title="Total" value={total} icon={List} color="text-blue-400" />
          <KpiCard title="Resolved" value={resolved} icon={CheckCircle} color="text-green-400" />
          <KpiCard title="Pending" value={pending} icon={Clock} color="text-yellow-400" />
          <KpiCard title="Critical" value={critical} icon={AlertCircle} color="text-red-400" />
      </div>

      {/* Top Critical */}
      <div>
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest border-b border-slate-800 pb-2 mb-3">Priority 1: Unresolved Critical</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topCritical.length > 0 ? topCritical.map(issue => {
                const { date, time } = formatDateTime(issue.created_at);
                return (
                  <Card key={issue.id} className="relative bg-red-950/20 border-red-900/50 border cursor-pointer hover:border-red-700 transition-all" onClick={() => setSelectedGrievance(issue)}>
                      {/* Delete Button */}
                      <button
                        onClick={(e) => handleDeleteGrievance(issue.id, e)}
                        className="absolute top-2 right-2 p-1 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded transition-colors z-10"
                        title="Delete Grievance"
                      >
                        <X className="h-4 w-4" />
                      </button>
                      
                      <CardHeader className="pb-2 pr-8">
                          <div className="flex justify-between">
                            <Badge className="bg-red-600 text-white">CRITICAL</Badge>
                            <span className="text-xs text-red-300 font-mono">#{issue.id?.slice(0,6)}</span>
                          </div>
                          <CardTitle className="text-white text-md mt-2 line-clamp-1">{normalizeCategory(issue.category || issue.issue_type)}</CardTitle>
                      </CardHeader>
                      <CardContent>
                          <p className="text-slate-300 text-sm line-clamp-2">{issue.description}</p>
                          <div className="flex items-center justify-between text-xs text-slate-500 mt-2">
                            <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {issue.village || issue.location}</span>
                            <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {date}</span>
                          </div>
                      </CardContent>
                  </Card>
                );
              }) : <div className="col-span-3 p-4 text-center text-slate-500 border border-dashed border-slate-800 rounded">No critical issues.</div>}
          </div>
      </div>

      {/* Add Grievance Form */}
      <Collapsible open={isAddOpen} onOpenChange={setIsAddOpen} className="border border-slate-700/50 rounded-xl bg-slate-900 shadow-md">
          <CollapsibleTrigger className="w-full">
              <div className="flex items-center justify-between p-5 cursor-pointer hover:bg-slate-800/50 transition-all">
                  <h3 className="text-white font-bold flex items-center gap-3"><Plus className="h-5 w-5 text-blue-500" /> Register New Grievance</h3>
                  {isAddOpen ? <ChevronUp className="text-slate-400" /> : <ChevronDown className="text-slate-400" />}
              </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
              <div className="relative p-6 border-t border-slate-800 space-y-4 bg-slate-950">
                  {/* Cancel/Close Button */}
                  <button
                    onClick={() => {
                      setIsAddOpen(false);
                      setFormData({
                        citizen_name: '', citizen_phone: '', location: '',
                        category: 'Miscellaneous', description: '', priority_level: 'LOW'
                      });
                      setMediaFile(null);
                    }}
                    className="absolute top-3 right-3 p-2 text-slate-400 hover:text-red-500 hover:bg-red-500/10 rounded-full transition-colors"
                    title="Cancel & Close"
                  >
                    <X className="h-5 w-5" />
                  </button>
                  
                  {/* Standardized Format Fields */}
                  <p className="text-xs text-orange-500 uppercase font-bold">Grievance Registration (Standardized Format)</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label className="text-white">Name of the Person *</Label>
                        <Input className="bg-slate-900 border-slate-700 text-white" placeholder="Full Name" value={formData.citizen_name} onChange={e => setFormData({...formData, citizen_name: e.target.value})} />
                      </div>
                      <div>
                        <Label className="text-white">Contact Number *</Label>
                        <Input className="bg-slate-900 border-slate-700 text-white" placeholder="Phone Number" value={formData.citizen_phone} onChange={e => setFormData({...formData, citizen_phone: e.target.value})} />
                      </div>
                  </div>
                  
                  <div>
                    <Label className="text-white">Area (Mandal/Village/Town/Ward/Division) *</Label>
                    <Input className="bg-slate-900 border-slate-700 text-white" placeholder="Location/Area Name" value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                          <Label className="text-white">Issue Category *</Label>
                          <Select value={formData.category} onValueChange={(val) => {
                              const p = getCategoryPriority(val);
                              setFormData({...formData, category: val, priority_level: p});
                          }}>
                              <SelectTrigger className="bg-slate-900 border-slate-700 text-white"><SelectValue /></SelectTrigger>
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
                      <div>
                        <Label className="text-white">Attach Photo/Document (Optional)</Label>
                        <input type="file" ref={mediaInputRef} onChange={handleMediaSelect} accept="image/*,application/pdf" className="hidden" />
                        <div onClick={() => mediaInputRef.current?.click()} className="mt-1 border-2 border-dashed border-slate-700 rounded-lg p-4 text-center cursor-pointer hover:border-orange-500 transition-colors">
                          {mediaFile ? (
                            <div className="text-green-400 flex items-center justify-center gap-2">
                              <FileText className="h-4 w-4" />
                              <span className="text-sm">{mediaFile.name}</span>
                            </div>
                          ) : (
                            <div className="text-slate-500 flex items-center justify-center gap-2">
                              <Upload className="h-4 w-4" />
                              <span className="text-sm">Click to attach</span>
                            </div>
                          )}
                        </div>
                      </div>
                  </div>
                  
                  <div className="relative">
                      <Label className="text-white">Issue Description *</Label>
                      <Textarea className="bg-slate-900 border-slate-700 text-white h-24 pr-12" placeholder="Describe the problem in detail..." value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
                      <Button type="button" size="sm" variant="ghost" className="absolute bottom-2 right-2 h-8 w-8 p-0 hover:bg-slate-800" onClick={() => setShowVoiceRecorder(true)}>
                        <Mic className="h-4 w-4 text-orange-500" />
                      </Button>
                  </div>
                  
                  <Button onClick={handleRegister} className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold">Register Grievance</Button>
              </div>
          </CollapsibleContent>
      </Collapsible>

      {/* Enhanced Filters */}
      <div className="flex flex-wrap gap-4 items-center bg-slate-900/50 p-4 rounded-xl border border-slate-800">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-500" />
            <span className="text-sm text-slate-400">Filters:</span>
          </div>
          
          <div className="flex-1 min-w-[200px]">
            <Input className="bg-slate-900 border-slate-700 text-white" placeholder="Search name, area, description..." value={filterText} onChange={e => setFilterText(e.target.value)} />
          </div>
          
          <Select onValueChange={setFilterCategory} defaultValue="All">
            <SelectTrigger className="w-[180px] bg-slate-900 border-slate-700 text-white text-sm"><SelectValue placeholder="Category" /></SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-800 text-white">
              <SelectItem value="All">All Categories</SelectItem>
              {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
          
          <Select onValueChange={setFilterGeoType} defaultValue="All Areas">
            <SelectTrigger className="w-[140px] bg-slate-900 border-slate-700 text-white text-sm"><SelectValue placeholder="Geo Type" /></SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-800 text-white">
              {GEO_TYPES.map(g => <SelectItem key={g} value={g}>{g}</SelectItem>)}
            </SelectContent>
          </Select>
          
          <Select onValueChange={setFilterPriority} defaultValue="All">
            <SelectTrigger className="w-[130px] bg-slate-900 border-slate-700 text-white text-sm"><SelectValue placeholder="Priority" /></SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-800 text-white">
              <SelectItem value="All">All Priority</SelectItem>
              <SelectItem value="CRITICAL">Critical</SelectItem>
              <SelectItem value="HIGH">High</SelectItem>
              <SelectItem value="MEDIUM">Medium</SelectItem>
              <SelectItem value="LOW">Low</SelectItem>
            </SelectContent>
          </Select>
          
          <Select onValueChange={setSortBy} defaultValue="date">
            <SelectTrigger className="w-[120px] bg-slate-900 border-slate-700 text-white text-sm"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-800 text-white">
              <SelectItem value="date">Newest</SelectItem>
              <SelectItem value="priority">Priority</SelectItem>
            </SelectContent>
          </Select>
      </div>

      {/* Split View */}
      <div className="flex flex-col lg:flex-row gap-6 min-h-[500px]">
          {/* List */}
          <div className="flex-1 space-y-3 max-h-[600px] overflow-y-auto pr-2">
              {sortedList.length === 0 ? (
                <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg">
                  No grievances match your filters
                </div>
              ) : sortedList.map(t => {
                const { date, time } = formatDateTime(t.created_at);
                const displayCat = normalizeCategory(t.category || t.issue_type);
                return (
                  <div key={t.id} className="relative p-4 bg-slate-900 border border-slate-800 rounded-lg cursor-pointer hover:bg-slate-800/50 transition-all" onClick={() => setSelectedGrievance(t)}>
                      {/* Delete Button */}
                      <button
                        onClick={(e) => handleDeleteGrievance(t.id, e)}
                        className="absolute top-2 right-2 p-1 text-slate-500 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors z-10"
                        title="Delete Grievance"
                      >
                        <X className="h-4 w-4" />
                      </button>
                      
                      <div className="flex items-start justify-between pr-6">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="text-white font-semibold">{t.citizen_name || "Anonymous"}</span>
                              <Badge variant="outline" className="text-slate-300 border-slate-600" style={{ borderColor: CATEGORY_COLORS[displayCat] }}>
                                {displayCat}
                              </Badge>
                              <Badge className={
                                t.priority_level === 'CRITICAL' ? 'bg-red-600' : 
                                t.priority_level === 'HIGH' ? 'bg-orange-600' : 
                                t.priority_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-blue-600'
                              }>{t.priority_level || 'LOW'}</Badge>
                          </div>
                          <p className="text-sm text-slate-400 line-clamp-1">{t.description}</p>
                          <div className="flex gap-4 mt-2 text-xs text-slate-500">
                            <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {t.village || t.location || '-'}</span>
                            <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {date}</span>
                            <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {time}</span>
                            <span className={`uppercase font-bold ${
                              t.status === 'RESOLVED' || t.status === 'resolved' ? 'text-green-500' : 
                              t.status === 'IN_PROGRESS' ? 'text-blue-500' : 'text-yellow-500'
                            }`}>{t.status}</span>
                          </div>
                        </div>
                        <Button variant="secondary" size="sm" className="bg-slate-800 ml-4">View</Button>
                      </div>
                  </div>
                );
              })}
          </div>
          
          {/* Graph - Categories in English */}
          <div className="w-full lg:w-[450px]">
              <Card className="bg-slate-900 border-slate-800 h-full">
                  <CardHeader className="border-b border-slate-800 pb-2">
                    <CardTitle className="text-white text-sm flex gap-2">
                      <BarChart3 className="h-4 w-4 text-purple-500"/> 
                      Category Analysis (English)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="h-[400px] pt-4">
                      <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={getGraphData()} layout="vertical" margin={{left:10}}>
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#1e293b" />
                              <XAxis type="number" hide />
                              <YAxis dataKey="name" type="category" width={140} tick={{fill:'#e2e8f0', fontSize:11}} interval={0} axisLine={false} tickLine={false} />
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
          onUpdate={async () => {
            fetchGrievances();
            const result = await api.get(`/api/grievances/${selectedGrievance.id}`);
            if (result.ok) {
              setSelectedGrievance(result.data);
            }
          }}
        />
      )}
    </div>
  );
};

export default HelpPeople;
