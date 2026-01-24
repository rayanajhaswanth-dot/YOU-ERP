import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { TrendingUp, Users, CheckCircle, FileText, Loader2 } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

export default function Dashboard({ user }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiSummary, setAiSummary] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/analytics/dashboard`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);

      const summaryResponse = await axios.post(
        `${BACKEND_URL}/api/ai/generate-constituency-summary`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAiSummary(summaryResponse.data.summary);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const mockActivityData = [
    { date: 'Mon', grievances: 12, resolved: 8 },
    { date: 'Tue', grievances: 19, resolved: 15 },
    { date: 'Wed', grievances: 15, resolved: 12 },
    { date: 'Thu', grievances: 22, resolved: 18 },
    { date: 'Fri', grievances: 18, resolved: 14 },
    { date: 'Sat', grievances: 25, resolved: 20 },
    { date: 'Sun', grievances: 16, resolved: 13 }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
      data-testid="dashboard"
    >
      <div>
        <h1 className="text-5xl font-bold text-slate-50 tracking-tight mb-2" style={{ fontFamily: 'Manrope' }}>
          The Briefing Room
        </h1>
        <p className="text-slate-400 text-lg">Your operational command center</p>
      </div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="executive-card p-6 hover:glow-orange" data-testid="stat-total-grievances">
          <div className="flex items-center justify-between mb-4">
            <Users className="h-8 w-8 text-orange-500" />
            <span className="text-xs uppercase tracking-wider text-slate-500">Total</span>
          </div>
          <p className="text-3xl font-bold text-slate-50">{stats?.total_grievances || 0}</p>
          <p className="text-sm text-slate-400 mt-1">Grievances</p>
        </div>

        <div className="executive-card p-6 hover:glow-orange" data-testid="stat-resolved">
          <div className="flex items-center justify-between mb-4">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
            <span className="text-xs uppercase tracking-wider text-slate-500">Resolved</span>
          </div>
          <p className="text-3xl font-bold text-slate-50">{stats?.resolved_grievances || 0}</p>
          <p className="text-sm text-slate-400 mt-1">Issues Closed</p>
        </div>

        <div className="executive-card p-6 hover:glow-orange" data-testid="stat-total-posts">
          <div className="flex items-center justify-between mb-4">
            <FileText className="h-8 w-8 text-sky-400" />
            <span className="text-xs uppercase tracking-wider text-slate-500">Posts</span>
          </div>
          <p className="text-3xl font-bold text-slate-50">{stats?.total_posts || 0}</p>
          <p className="text-sm text-slate-400 mt-1">Total Created</p>
        </div>

        <div className="executive-card p-6 hover:glow-orange" data-testid="stat-published">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="h-8 w-8 text-amber-400" />
            <span className="text-xs uppercase tracking-wider text-slate-500">Published</span>
          </div>
          <p className="text-3xl font-bold text-slate-50">{stats?.published_posts || 0}</p>
          <p className="text-sm text-slate-400 mt-1">Live Content</p>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="executive-card p-8" data-testid="activity-chart">
          <h3 className="text-2xl font-semibold text-slate-50 mb-6">Weekly Activity</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={mockActivityData}>
              <defs>
                <linearGradient id="colorGrievances" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '0.75rem',
                  color: '#f1f5f9'
                }}
              />
              <Area
                type="monotone"
                dataKey="grievances"
                stroke="#f97316"
                strokeWidth={2}
                fill="url(#colorGrievances)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="executive-card p-8" data-testid="ai-summary">
          <h3 className="text-2xl font-semibold text-slate-50 mb-4">Constituency Overview</h3>
          <div className="bg-slate-950 rounded-2xl p-6 border border-slate-800">
            <p className="text-sm uppercase tracking-wider text-orange-500 mb-3">AI-Generated Summary</p>
            <p className="text-slate-300 leading-relaxed">
              {aiSummary || 'Generating constituency analysis...'}
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="executive-card p-8" data-testid="campaign-suggestions">
        <h3 className="text-2xl font-semibold text-slate-50 mb-6">Campaign Suggestions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { title: 'Infrastructure Focus', desc: 'Organize road quality assessment drives in high-complaint areas', priority: 'High' },
            { title: 'Youth Engagement', desc: 'Launch skill development workshops based on employment grievances', priority: 'Medium' },
            { title: 'Healthcare Access', desc: 'Mobile medical camps in underserved villages', priority: 'High' }
          ].map((suggestion, idx) => (
            <div key={idx} className="bg-slate-950 rounded-2xl p-6 border border-slate-800 hover:border-orange-500/30 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                  suggestion.priority === 'High' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'
                }`}>
                  {suggestion.priority}
                </span>
              </div>
              <h4 className="font-semibold text-slate-200 mb-2">{suggestion.title}</h4>
              <p className="text-sm text-slate-400">{suggestion.desc}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}