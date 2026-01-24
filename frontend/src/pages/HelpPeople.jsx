import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Phone, MessageSquare, FileText, Loader2, AlertCircle, CheckCircle2, Clock, TrendingUp, AlertTriangle, Camera } from 'lucide-react';
import PhotoVerification from '../components/PhotoVerification';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function HelpPeople({ user }) {
  const [grievances, setGrievances] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [topPriority, setTopPriority] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showVerification, setShowVerification] = useState(false);
  const [selectedGrievance, setSelectedGrievance] = useState(null);
  const [formData, setFormData] = useState({
    village: '',
    description: '',
    issue_type: 'Other'
  });
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    fetchGrievances();
    fetchMetrics();
  }, []);

  const fetchGrievances = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/grievances/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGrievances(response.data);
      
      // Calculate top priority issues
      const sorted = [...response.data].sort((a, b) => {
        const priorityA = calculateDynamicPriority(a);
        const priorityB = calculateDynamicPriority(b);
        return priorityB - priorityA;
      });
      setTopPriority(sorted.slice(0, 3));
    } catch (error) {
      console.error('Error fetching grievances:', error);
      toast.error('Failed to load grievances');
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/grievances/metrics`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMetrics(response.data);
    } catch (error) {
      console.error('Error fetching metrics:', error);
    }
  };

  const calculateDynamicPriority = (grievance) => {
    // Dynamic priority calculation based on multiple factors
    let priority = grievance.ai_priority || 5;
    
    // Factor 1: Time elapsed (pending longer = higher priority)
    const createdDate = new Date(grievance.created_at);
    const now = new Date();
    const daysElapsed = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24));
    
    // Add 0.5 points per day for pending issues
    if (grievance.status === 'PENDING') {
      priority += (daysElapsed * 0.5);
    }
    
    // Factor 2: Category urgency multiplier
    const categoryMultipliers = {
      'Healthcare': 1.3,
      'Infrastructure': 1.2,
      'Emergency': 1.5,
      'Education': 1.0,
      'Employment': 1.0,
      'Social Welfare': 1.1,
      'Other': 1.0
    };
    priority *= (categoryMultipliers[grievance.issue_type] || 1.0);
    
    // Factor 3: Status penalty (in_progress gets slight boost)
    if (grievance.status === 'IN_PROGRESS') {
      priority += 1;
    }
    
    return Math.min(priority, 10); // Cap at 10
  };

  const getDaysElapsed = (createdAt) => {
    const created = new Date(createdAt);
    const now = new Date();
    return Math.floor((now - created) / (1000 * 60 * 60 * 24));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAnalyzing(true);

    try {
      const token = localStorage.getItem('token');
      
      const aiResponse = await axios.post(
        `${BACKEND_URL}/api/ai/analyze-grievance`,
        { text: formData.description, analysis_type: 'triage' },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      let ai_priority = 5;
      let issue_type = 'Other';
      try {
        const analysis = JSON.parse(aiResponse.data.analysis.replace(/```json\n|```/g, ''));
        ai_priority = analysis.priority || 5;
        issue_type = analysis.category || 'Other';
      } catch (e) {
        console.log('Could not parse AI response, using defaults');
      }

      await axios.post(
        `${BACKEND_URL}/api/grievances/`,
        { 
          village: formData.village,
          description: formData.description,
          issue_type: issue_type,
          ai_priority: ai_priority
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success('Grievance registered successfully');
      setShowForm(false);
      setFormData({ village: '', description: '', issue_type: 'Other' });
      fetchGrievances();
      fetchMetrics();
    } catch (error) {
      console.error('Error submitting grievance:', error);
      toast.error('Failed to register grievance');
    } finally {
      setAnalyzing(false);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(
        `${BACKEND_URL}/api/grievances/${id}`,
        { status },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Grievance marked as ${status}`);
      fetchGrievances();
      fetchMetrics();
    } catch (error) {
      console.error('Error updating status:', error);
      toast.error('Failed to update status');
    }
  };

  const getStatusColor = (status) => {
    const statusUpper = (status || '').toUpperCase();
    switch (statusUpper) {
      case 'PENDING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'IN_PROGRESS':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      case 'RESOLVED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const getPriorityColor = (priority) => {
    if (priority >= 8) return 'text-rose-400';
    if (priority >= 5) return 'text-amber-400';
    return 'text-sky-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
      data-testid="help-people-page"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-5xl font-bold text-slate-50 tracking-tight mb-2" style={{ fontFamily: 'Manrope' }}>
            Help People
          </h1>
          <p className="text-slate-400 text-lg">Grievance tracking & AI triage</p>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          data-testid="add-grievance-button"
          className="bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full px-8 py-3 pill-button"
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          Add Grievance
        </Button>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-6"
        >
          <div className="executive-card p-6 hover:glow-orange" data-testid="metric-total">
            <div className="flex items-center justify-between mb-4">
              <FileText className="h-8 w-8 text-orange-500" />
              <span className="text-xs uppercase tracking-wider text-slate-500">Total</span>
            </div>
            <p className="text-3xl font-bold text-slate-50">{metrics.total}</p>
            <p className="text-sm text-slate-400 mt-1">All Grievances</p>
          </div>

          <div className="executive-card p-6 hover:glow-orange" data-testid="metric-resolved">
            <div className="flex items-center justify-between mb-4">
              <CheckCircle2 className="h-8 w-8 text-emerald-400" />
              <span className="text-xs uppercase tracking-wider text-slate-500">Resolved</span>
            </div>
            <p className="text-3xl font-bold text-emerald-400">{metrics.resolved}</p>
            <p className="text-sm text-slate-400 mt-1">{metrics.resolution_rate}% Success Rate</p>
          </div>

          <div className="executive-card p-6 hover:glow-orange" data-testid="metric-pending">
            <div className="flex items-center justify-between mb-4">
              <Clock className="h-8 w-8 text-amber-400" />
              <span className="text-xs uppercase tracking-wider text-slate-500">Pending</span>
            </div>
            <p className="text-3xl font-bold text-amber-400">{metrics.unresolved}</p>
            <p className="text-sm text-slate-400 mt-1">Awaiting Action</p>
          </div>

          <div className="executive-card p-6 hover:glow-orange" data-testid="metric-overdue">
            <div className="flex items-center justify-between mb-4">
              <AlertTriangle className="h-8 w-8 text-rose-400" />
              <span className="text-xs uppercase tracking-wider text-slate-500">Long Pending</span>
            </div>
            <p className="text-3xl font-bold text-rose-400">{metrics.long_pending}</p>
            <p className="text-sm text-slate-400 mt-1">Over {metrics.long_pending_days} Days</p>
          </div>
        </motion.div>
      )}

      {/* Top Priority Issues */}
      {topPriority.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="executive-card p-8"
          data-testid="top-priority-section"
        >
          <div className="flex items-center gap-3 mb-6">
            <TrendingUp className="h-6 w-6 text-rose-400" />
            <h3 className="text-2xl font-semibold text-slate-50">Top Priority Issues</h3>
            <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20">Urgent Attention Required</Badge>
          </div>
          <div className="space-y-4">
            {topPriority.map((grievance, index) => {
              const dynamicPriority = calculateDynamicPriority(grievance);
              const daysElapsed = getDaysElapsed(grievance.created_at);
              return (
                <div
                  key={grievance.id}
                  data-testid={`top-priority-${index + 1}`}
                  className="bg-slate-950 rounded-2xl p-6 border-2 border-rose-500/30 hover:border-rose-500/50 transition-colors relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 w-2 h-full bg-gradient-to-b from-rose-500 to-orange-500"></div>
                  <div className="flex items-start justify-between ml-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl font-bold text-rose-400">#{index + 1}</span>
                        <h4 className="font-semibold text-slate-200 text-lg">{grievance.village || 'Unknown Location'}</h4>
                        <Badge className={getStatusColor(grievance.status)}>
                          {(grievance.status || 'pending').replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm mb-3">
                        <span className="flex items-center gap-1 text-slate-400">
                          <FileText className="h-3 w-3" />
                          {grievance.issue_type || 'Other'}
                        </span>
                        <span className="flex items-center gap-1 text-amber-400">
                          <Clock className="h-3 w-3" />
                          {daysElapsed} days ago
                        </span>
                        <span className={`text-sm font-bold ${getPriorityColor(dynamicPriority)}`}>
                          Dynamic Priority: {dynamicPriority.toFixed(1)}/10
                        </span>
                      </div>
                      <p className="text-slate-300 mb-4">{grievance.description || 'No description'}</p>
                      <div className="flex gap-2">
                        {grievance.status === 'PENDING' && (
                          <Button
                            onClick={() => updateStatus(grievance.id, 'IN_PROGRESS')}
                            size="sm"
                            className="bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 rounded-full pill-button"
                          >
                            Start Work Now
                          </Button>
                        )}
                        {grievance.status === 'IN_PROGRESS' && (
                          <Button
                            onClick={() => updateStatus(grievance.id, 'RESOLVED')}
                            size="sm"
                            className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 rounded-full pill-button"
                          >
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Mark Resolved
                          </Button>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs uppercase tracking-wider text-slate-500 mb-1">Base AI Score</div>
                      <div className="text-2xl font-bold text-orange-500">{grievance.ai_priority || 5}/10</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {showForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="executive-card p-8"
          data-testid="grievance-form"
        >
          <h3 className="text-2xl font-semibold text-slate-50 mb-6">Register New Grievance</h3>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Village/Area</label>
                <Input
                  value={formData.village}
                  onChange={(e) => setFormData({ ...formData, village: e.target.value })}
                  data-testid="village-input"
                  className="bg-slate-950 border-slate-800 focus:border-orange-500 rounded-xl h-12 text-slate-200"
                  placeholder="Village or area name"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Issue Type</label>
                <select
                  value={formData.issue_type}
                  onChange={(e) => setFormData({ ...formData, issue_type: e.target.value })}
                  data-testid="issue-type-select"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-orange-500 rounded-xl h-12 text-slate-200 px-4"
                >
                  <option value="Infrastructure">Infrastructure</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Education">Education</option>
                  <option value="Employment">Employment</option>
                  <option value="Social Welfare">Social Welfare</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Grievance Description</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                data-testid="description-textarea"
                className="bg-slate-950 border-slate-800 focus:border-orange-500 rounded-xl text-slate-200 min-h-[120px]"
                placeholder="Describe the issue..."
                required
              />
            </div>
            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={analyzing}
                data-testid="submit-grievance-button"
                className="bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full px-8 pill-button"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing with AI...
                  </>
                ) : (
                  'Submit'
                )}
              </Button>
              <Button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-slate-800 hover:bg-slate-700 text-white rounded-full px-8 pill-button"
              >
                Cancel
              </Button>
            </div>
          </form>
        </motion.div>
      )}

      <div className="executive-card p-8" data-testid="grievances-list">
        <h3 className="text-2xl font-semibold text-slate-50 mb-6">All Grievances</h3>
        <div className="space-y-4">
          {grievances.length === 0 ? (
            <p className="text-slate-400 text-center py-8">No grievances registered yet</p>
          ) : (
            grievances.map((grievance) => {
              const daysElapsed = getDaysElapsed(grievance.created_at);
              const dynamicPriority = calculateDynamicPriority(grievance);
              return (
                <motion.div
                  key={grievance.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  data-testid={`grievance-${grievance.id}`}
                  className="bg-slate-950 rounded-2xl p-6 border border-slate-800 hover:border-orange-500/30 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="font-semibold text-slate-200 text-lg">{grievance.village || 'Unknown Location'}</h4>
                        <Badge className={getStatusColor(grievance.status)}>
                          {(grievance.status || 'pending').replace('_', ' ')}
                        </Badge>
                        <span className={`text-sm font-semibold ${getPriorityColor(dynamicPriority)}`}>
                          Priority: {dynamicPriority.toFixed(1)}/10
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
                        <span className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {grievance.issue_type || 'Other'}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {daysElapsed} days ago
                        </span>
                        <span>ID: {grievance.id?.substring(0, 8).toUpperCase()}</span>
                      </div>
                      <p className="text-slate-300">{grievance.description || 'No description'}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4">
                    {grievance.status === 'PENDING' && (
                      <Button
                        onClick={() => updateStatus(grievance.id, 'IN_PROGRESS')}
                        data-testid={`start-work-${grievance.id}`}
                        size="sm"
                        className="bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 rounded-full pill-button"
                      >
                        Start Work
                      </Button>
                    )}
                    {grievance.status === 'IN_PROGRESS' && (
                      <>
                        <Button
                          onClick={() => {
                            setSelectedGrievance(grievance);
                            setShowVerification(true);
                          }}
                          data-testid={`verify-${grievance.id}`}
                          size="sm"
                          className="bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 rounded-full pill-button"
                        >
                          <Camera className="h-3 w-3 mr-1" />
                          Photo Verify
                        </Button>
                        <Button
                          onClick={() => updateStatus(grievance.id, 'RESOLVED')}
                          data-testid={`resolve-${grievance.id}`}
                          size="sm"
                          className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 rounded-full pill-button"
                        >
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Mark Resolved
                        </Button>
                      </>
                    )}
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      </div>
    </motion.div>
  );
}