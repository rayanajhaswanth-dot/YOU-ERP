import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { AlertTriangle, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Executive Saffron Design System Colors
const COLORS = {
  background: '#111827',
  cardSurface: '#1F2937',
  text: '#F3F4F6',
  textMuted: '#9CA3AF',
  positive: '#FF9933',  // Saffron
  negative: '#EF4444',  // Red
  neutral: '#6B7280',
};

export default function SentimentDashboard() {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [spikeAlert, setSpikeAlert] = useState(false);
  const [latestStats, setLatestStats] = useState({ positive: 0, negative: 0, neutral: 0 });
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${BACKEND_URL}/api/social/dashboard`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      // Reverse data (API returns newest first, chart needs oldest first)
      const reversed = [...data].reverse();
      setChartData(reversed);
      
      // Check for spike in ANY item
      const hasSpike = data.some(item => item.spike_detected === true);
      setSpikeAlert(hasSpike);
      
      // Get latest stats (first item from original data is most recent)
      if (data.length > 0) {
        const totals = data.reduce((acc, item) => ({
          positive: acc.positive + (item.positive_count || 0),
          negative: acc.negative + (item.negative_count || 0),
          neutral: acc.neutral + (item.neutral_count || 0),
        }), { positive: 0, negative: 0, neutral: 0 });
        
        setLatestStats(totals);
        
        // Also check if any negative count is unusually high (spike detection fallback)
        const avgNegative = totals.negative / Math.max(data.length, 1);
        const latestNegative = data[0]?.negative_count || 0;
        if (latestNegative > avgNegative * 2 && latestNegative >= 3) {
          setSpikeAlert(true);
        }
      }
      
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError('Failed to load sentiment data');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div 
        className="p-6 rounded-xl shadow-lg flex items-center justify-center h-64"
        style={{ backgroundColor: COLORS.background }}
        data-testid="sentiment-dashboard-loading"
      >
        <Loader2 className="h-8 w-8 animate-spin" style={{ color: COLORS.positive }} />
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="p-6 rounded-xl shadow-lg"
        style={{ backgroundColor: COLORS.background, color: COLORS.text }}
        data-testid="sentiment-dashboard-error"
      >
        <p className="text-center text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div 
      className="p-6 rounded-xl shadow-lg space-y-6"
      style={{ backgroundColor: COLORS.background, color: COLORS.text }}
      data-testid="sentiment-dashboard"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Happiness Report</h2>
        {spikeAlert && (
          <span 
            className="px-3 py-1 rounded-full text-xs font-bold animate-pulse flex items-center gap-1"
            style={{ backgroundColor: COLORS.negative, color: 'white' }}
            data-testid="spike-alert-badge"
          >
            <AlertTriangle className="h-3 w-3" />
            SPIKE DETECTED
          </span>
        )}
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Public Trust Card */}
        <div 
          className="p-5 rounded-lg"
          style={{ backgroundColor: COLORS.cardSurface }}
          data-testid="public-trust-card"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
              Public Trust
            </span>
            <TrendingUp className="h-5 w-5" style={{ color: COLORS.positive }} />
          </div>
          <p className="text-4xl font-bold" style={{ color: COLORS.positive }}>
            {latestStats.positive}
          </p>
          <p className="text-sm mt-1" style={{ color: COLORS.textMuted }}>
            Positive mentions
          </p>
        </div>

        {/* Critical Issues Card */}
        <div 
          className="p-5 rounded-lg relative"
          style={{ backgroundColor: COLORS.cardSurface }}
          data-testid="critical-issues-card"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
              Critical Issues
            </span>
            <TrendingDown className="h-5 w-5" style={{ color: COLORS.negative }} />
          </div>
          <p className="text-4xl font-bold" style={{ color: COLORS.negative }}>
            {latestStats.negative}
          </p>
          <p className="text-sm mt-1" style={{ color: COLORS.textMuted }}>
            Negative mentions
          </p>
          {spikeAlert && (
            <span 
              className="absolute top-2 right-2 px-2 py-0.5 rounded text-xs font-bold animate-pulse"
              style={{ backgroundColor: COLORS.negative, color: 'white' }}
            >
              ⚠️ SPIKE
            </span>
          )}
        </div>

        {/* Neutral Card */}
        <div 
          className="p-5 rounded-lg"
          style={{ backgroundColor: COLORS.cardSurface }}
          data-testid="neutral-card"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
              Neutral
            </span>
          </div>
          <p className="text-4xl font-bold" style={{ color: COLORS.neutral }}>
            {latestStats.neutral}
          </p>
          <p className="text-sm mt-1" style={{ color: COLORS.textMuted }}>
            Neutral mentions
          </p>
        </div>
      </div>

      {/* Chart */}
      <div 
        className="p-4 rounded-lg"
        style={{ backgroundColor: COLORS.cardSurface }}
        data-testid="sentiment-chart"
      >
        <h3 className="text-lg font-semibold mb-4" style={{ color: COLORS.text }}>
          Sentiment Trend (Last 7 Days)
        </h3>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="report_date" 
                tickFormatter={formatDate}
                stroke={COLORS.textMuted}
                tick={{ fill: COLORS.textMuted, fontSize: 12 }}
              />
              <YAxis 
                stroke={COLORS.textMuted}
                tick={{ fill: COLORS.textMuted, fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: COLORS.cardSurface, 
                  border: 'none',
                  borderRadius: '8px',
                  color: COLORS.text
                }}
                labelFormatter={formatDate}
              />
              <Line 
                type="monotone"
                dataKey="positive_count" 
                stroke={COLORS.positive} 
                strokeWidth={3}
                dot={{ fill: COLORS.positive, strokeWidth: 2 }}
                name="Positive"
              />
              <Line 
                type="monotone"
                dataKey="negative_count" 
                stroke={COLORS.negative} 
                strokeWidth={3}
                dot={{ fill: COLORS.negative, strokeWidth: 2 }}
                name="Negative"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-64 flex items-center justify-center" style={{ color: COLORS.textMuted }}>
            No data available yet. Start analyzing sentiment to see trends.
          </div>
        )}
      </div>

      {/* Platform Breakdown */}
      {chartData.length > 0 && (
        <div 
          className="p-4 rounded-lg"
          style={{ backgroundColor: COLORS.cardSurface }}
          data-testid="platform-breakdown"
        >
          <h3 className="text-lg font-semibold mb-3" style={{ color: COLORS.text }}>
            By Platform
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[...new Set(chartData.map(d => d.platform))].map(platform => {
              const platformData = chartData.filter(d => d.platform === platform);
              const total = platformData.reduce((sum, d) => 
                sum + (d.positive_count || 0) + (d.negative_count || 0) + (d.neutral_count || 0), 0);
              return (
                <div 
                  key={platform}
                  className="p-3 rounded-md text-center"
                  style={{ backgroundColor: COLORS.background }}
                >
                  <p className="text-sm font-medium" style={{ color: COLORS.text }}>{platform}</p>
                  <p className="text-xl font-bold" style={{ color: COLORS.positive }}>{total}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
