import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Phone, MessageSquare, FileText, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function HelpPeople({ user }) {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    village: '',
    description: '',
    issue_type: 'Other'
  });
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    fetchGrievances();
  }, []);

  const fetchGrievances = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/grievances/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGrievances(response.data);
    } catch (error) {
      console.error('Error fetching grievances:', error);
      toast.error('Failed to load grievances');
    } finally {
      setLoading(false);
    }
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
                <label className="block text-sm font-medium text-slate-300 mb-2">Constituent Name</label>
                <Input
                  value={formData.constituent_name}
                  onChange={(e) => setFormData({ ...formData, constituent_name: e.target.value })}
                  data-testid="constituent-name-input"
                  className="bg-slate-950 border-slate-800 focus:border-orange-500 rounded-xl h-12 text-slate-200"
                  placeholder="Full name"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Phone Number</label>
                <Input
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  data-testid="phone-input"
                  className="bg-slate-950 border-slate-800 focus:border-orange-500 rounded-xl h-12 text-slate-200"
                  placeholder="+91 XXXXX XXXXX"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Grievance Message</label>
              <Textarea
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                data-testid="message-textarea"
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
        <h3 className="text-2xl font-semibold text-slate-50 mb-6">Active Grievances</h3>
        <div className="space-y-4">
          {grievances.length === 0 ? (
            <p className="text-slate-400 text-center py-8">No grievances registered yet</p>
          ) : (
            grievances.map((grievance) => (
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
                      <h4 className="font-semibold text-slate-200 text-lg">{grievance.constituent_name}</h4>
                      <Badge className={getStatusColor(grievance.status)}>
                        {grievance.status.replace('_', ' ')}
                      </Badge>
                      <span className={`text-sm font-semibold ${getPriorityColor(grievance.priority)}`}>
                        Priority: {grievance.priority}/10
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" />
                        {grievance.phone}
                      </span>
                      <span>Source: {grievance.source}</span>
                    </div>
                    <p className="text-slate-300">{grievance.message}</p>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  {grievance.status === 'pending' && (
                    <Button
                      onClick={() => updateStatus(grievance.id, 'in_progress')}
                      data-testid={`start-work-${grievance.id}`}
                      size="sm"
                      className="bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 rounded-full pill-button"
                    >
                      Start Work
                    </Button>
                  )}
                  {grievance.status === 'in_progress' && (
                    <Button
                      onClick={() => updateStatus(grievance.id, 'resolved')}
                      data-testid={`resolve-${grievance.id}`}
                      size="sm"
                      className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 rounded-full pill-button"
                    >
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Mark Resolved
                    </Button>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}