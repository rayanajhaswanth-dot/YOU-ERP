import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const COLORS = ['#f97316', '#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6'];

export default function HappinessReport({ user }) {
  const [overview, setOverview] = useState(null);
  const [sentimentData, setSentimentData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      
      const overviewResponse = await axios.get(`${BACKEND_URL}/api/analytics/sentiment/overview`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOverview(overviewResponse.data);

      const sentimentResponse = await axios.get(`${BACKEND_URL}/api/analytics/sentiment?days=30`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSentimentData(sentimentResponse.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const formatIssueDistribution = () => {
    if (!overview?.issue_distribution) return [];
    return Object.entries(overview.issue_distribution).map(([name, value]) => ({
      name,
      value
    }));
  };

  const mockTrendData = [
    { date: 'Week 1', sentiment: 0.45 },
    { date: 'Week 2', sentiment: 0.52 },
    { date: 'Week 3', sentiment: 0.48 },
    { date: 'Week 4', sentiment: 0.65 }
  ];

  const getSentimentIcon = (score) => {
    if (score > 0.6) return <TrendingUp className="h-6 w-6 text-emerald-400" />;
    if (score < 0.4) return <TrendingDown className="h-6 w-6 text-rose-400" />;
    return <Minus className="h-6 w-6 text-amber-400" />;
  };

  const getSentimentLabel = (score) => {
    if (score > 0.6) return 'Positive';
    if (score < 0.4) return 'Negative';
    return 'Neutral';
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
      data-testid="happiness-report-page"
    >
      <div>
        <h1 className="text-5xl font-bold text-slate-50 tracking-tight mb-2" style={{ fontFamily: 'Manrope' }}>
          Happiness Report
        </h1>
        <p className="text-slate-400 text-lg">Sentiment analytics & social listening</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="executive-card p-6" data-testid="average-sentiment">
          <div className="flex items-center justify-between mb-4">
            {getSentimentIcon(overview?.average_sentiment || 0)}
            <span className="text-xs uppercase tracking-wider text-slate-500">Avg Sentiment</span>
          </div>
          <p className="text-3xl font-bold text-slate-50">{(overview?.average_sentiment || 0).toFixed(2)}</p>
          <p className="text-sm text-slate-400 mt-1">{getSentimentLabel(overview?.average_sentiment || 0)}</p>
        </div>

        <div className="executive-card p-6" data-testid="total-mentions">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs uppercase tracking-wider text-slate-500">Mentions</span>
          </div>
          <p className="text-3xl font-bold text-slate-50">{overview?.total_mentions || 0}</p>
          <p className="text-sm text-slate-400 mt-1">Total tracked</p>
        </div>

        <div className="executive-card p-6" data-testid="trend-indicator">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="h-6 w-6 text-emerald-400" />
            <span className="text-xs uppercase tracking-wider text-slate-500">Trend</span>
          </div>
          <p className="text-3xl font-bold text-emerald-400">+12%</p>
          <p className="text-sm text-slate-400 mt-1">vs last month</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="executive-card p-8" data-testid="sentiment-trend-chart">
          <h3 className="text-2xl font-semibold text-slate-50 mb-6">Sentiment Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={mockTrendData}>
              <defs>
                <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" />
              <YAxis stroke="#64748b" domain={[0, 1]} />
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
                dataKey="sentiment"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#colorSentiment)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="executive-card p-8" data-testid="issue-distribution-chart">
          <h3 className="text-2xl font-semibold text-slate-50 mb-6">Issue Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={formatIssueDistribution()}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {formatIssueDistribution().map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '0.75rem',
                  color: '#f1f5f9'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="executive-card p-8" data-testid="recent-mentions">
        <h3 className="text-2xl font-semibold text-slate-50 mb-6">Recent Mentions</h3>
        <div className="space-y-4">
          {sentimentData.length === 0 ? (
            <p className="text-slate-400 text-center py-8">No sentiment data available yet</p>
          ) : (
            sentimentData.slice(0, 10).map((item, idx) => (
              <div
                key={idx}
                className="bg-slate-950 rounded-2xl p-4 border border-slate-800"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs uppercase tracking-wider text-slate-500">
                    {item.platform} • {item.issue_category}
                  </span>
                  <span className={`text-sm font-semibold ${
                    item.sentiment_score > 0.6 ? 'text-emerald-400' :
                    item.sentiment_score < 0.4 ? 'text-rose-400' : 'text-amber-400'
                  }`}>
                    Score: {item.sentiment_score.toFixed(2)}
                  </span>
                </div>
                <p className="text-slate-300 text-sm">{item.content}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}