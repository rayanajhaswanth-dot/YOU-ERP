import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { Loader2, Smile, TrendingUp, Users, Activity, AlertTriangle, CheckCircle, Share2, MessageCircle, ThumbsUp, Star, Clock, Target } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Cell, PieChart, Pie } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const HappinessReport = () => {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);
  const [digitalData, setDigitalData] = useState(null);
  const [groundData, setGroundData] = useState(null);
  const [scores, setScores] = useState({
    happinessIndex: 50,
    digitalPerception: 0,
    groundStability: 50
  });

  useEffect(() => {
    fetchReportData();
  }, []);

  const fetchReportData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // Fetch all data in parallel
      const [happinessRes, analyticsRes, grievancesRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/analytics/happiness_metrics`, { headers }),
        fetch(`${BACKEND_URL}/api/analytics/campaigns`, { headers }),
        fetch(`${BACKEND_URL}/api/grievances/`, { headers })
      ]);

      let happinessMetrics = null;
      let digital = { summary: { total_reach: 0, total_engagement: 0, platform_breakdown: {} }, posts: [] };
      let grievances = [];

      if (happinessRes.ok) happinessMetrics = await happinessRes.json();
      if (analyticsRes.ok) digital = await analyticsRes.json();
      if (grievancesRes.ok) grievances = await grievancesRes.json();

      setMetrics(happinessMetrics);
      setDigitalData(digital);
      setGroundData(grievances);

      // Calculate scores
      if (happinessMetrics) {
        setScores({
          happinessIndex: Math.round(happinessMetrics.overall_score || 50),
          digitalPerception: calculateDigitalScore(digital, happinessMetrics.digital),
          groundStability: Math.round(happinessMetrics.ground?.sla_percentage || 0)
        });
      } else {
        // Fallback calculation
        const totalGrievances = grievances.length;
        const resolvedGrievances = grievances.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length;
        let groundStabilityScore = totalGrievances > 0 ? Math.round((resolvedGrievances / totalGrievances) * 100) : 50;

        const engagementPoints = (digital.summary.total_engagement || 0) * 2;
        const reachPoints = (digital.summary.total_reach || 0) / 50;
        const rawDigitalScore = engagementPoints + reachPoints;
        const digitalPerceptionScore = rawDigitalScore > 0 ? Math.min(100, Math.max(5, Math.round(rawDigitalScore))) : 0;

        const happinessIndex = Math.round((groundStabilityScore + digitalPerceptionScore) / 2);

        setScores({
          happinessIndex,
          digitalPerception: digitalPerceptionScore,
          groundStability: groundStabilityScore
        });
      }

    } catch (error) {
      console.error("Failed to compile Happiness Report:", error);
    } finally {
      setLoading(false);
    }
  };

  const calculateDigitalScore = (digital, sentiment) => {
    // Weight: Engagement * 2 + Reach/50 + Sentiment bonus
    const engagementPoints = (digital.summary.total_engagement || 0) * 2;
    const reachPoints = (digital.summary.total_reach || 0) / 50;
    
    let sentimentBonus = 0;
    if (sentiment) {
      const total = (sentiment.positive || 0) + (sentiment.neutral || 0) + (sentiment.negative || 0);
      if (total > 0) {
        sentimentBonus = ((sentiment.positive || 0) / total) * 20; // Max 20 bonus points
      }
    }
    
    const rawScore = engagementPoints + reachPoints + sentimentBonus;
    return rawScore > 0 ? Math.min(100, Math.max(5, Math.round(rawScore))) : 0;
  };

  const getScoreColor = (score) => {
    if (score >= 75) return "text-green-500";
    if (score >= 50) return "text-yellow-500";
    if (score >= 30) return "text-orange-500";
    return "text-red-500";
  };

  const getSLAColor = (percentage) => {
    if (percentage >= 75) return "bg-green-500";
    if (percentage >= 50) return "bg-yellow-500";
    if (percentage >= 30) return "bg-orange-500";
    return "bg-red-500";
  };

  const getSafeLikeCount = (post) => {
    if (post.likes > 0) return post.likes;
    if (post.engagement > 0 && post.comments === 0) return post.engagement;
    return 0;
  };

  // Sentiment chart data
  const getSentimentChartData = () => {
    if (!metrics?.digital) return [];
    return [
      { name: 'Positive', value: metrics.digital.positive || 0, color: '#22c55e' },
      { name: 'Neutral', value: metrics.digital.neutral || 0, color: '#64748b' },
      { name: 'Negative', value: metrics.digital.negative || 0, color: '#ef4444' }
    ].filter(d => d.value > 0);
  };

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin text-orange-500 mx-auto" />
          <p className="text-slate-400 animate-pulse">Compiling Citizen Sentiment Matrix...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8 animate-in fade-in duration-700" data-testid="happiness-report">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Smile className="h-8 w-8 text-orange-500" />
            Happiness Report
          </h1>
          <p className="text-slate-400 mt-1 flex items-center gap-2">
            Live algorithmic assessment of constituency sentiment.
            <Badge variant="outline" className="text-[10px] border-orange-500/50 text-orange-500">
              Algorithm: Launch Mode v3.0
            </Badge>
          </p>
        </div>
        <div className="bg-slate-900/80 backdrop-blur border border-slate-800 p-4 rounded-xl flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Overall Index</p>
            <p className={`text-3xl font-black ${getScoreColor(scores.happinessIndex)}`}>
              {scores.happinessIndex}/100
            </p>
          </div>
          <div className="h-10 w-10 rounded-full border-4 border-slate-800 flex items-center justify-center bg-slate-900">
             <Activity className={`h-5 w-5 ${getScoreColor(scores.happinessIndex)}`} />
          </div>
        </div>
      </div>

      {/* NEW: Top KPI Row - Citizen Rating & SLA Gauge */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* KPI: Citizen Satisfaction (Rating) */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-5 flex justify-between items-center">
            <div>
              <p className="text-slate-400 text-xs font-bold uppercase">Citizen Rating</p>
              <div className="flex items-center gap-1 mt-1">
                <span className="text-3xl font-bold text-yellow-400">
                  {metrics?.ground?.citizen_rating?.toFixed(1) || "0.0"}
                </span>
                <Star className="h-5 w-5 text-yellow-400 fill-current" />
              </div>
              <p className="text-xs text-slate-500">
                {metrics?.ground?.rating_count || 0} feedbacks
              </p>
            </div>
            <Users className="h-8 w-8 text-blue-500 opacity-50" />
          </CardContent>
        </Card>

        {/* KPI: Ground Stability (SLA) */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-5">
            <div className="flex justify-between items-end mb-2">
              <div>
                <p className="text-slate-400 text-xs font-bold uppercase">Resolution Efficiency</p>
                <p className={`text-2xl font-bold ${
                  (metrics?.ground?.sla_percentage || 0) > 75 ? 'text-green-400' : 
                  (metrics?.ground?.sla_percentage || 0) > 30 ? 'text-orange-400' : 'text-red-400'
                }`}>
                  {metrics?.ground?.status_label || "No Data"}
                </p>
              </div>
              <span className="text-xl font-mono text-slate-500">
                {(metrics?.ground?.sla_percentage || 0).toFixed(0)}%
              </span>
            </div>
            {/* Progress Bar Visual for SLA */}
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={getSLAColor(metrics?.ground?.sla_percentage || 0)}
                style={{ width: `${metrics?.ground?.sla_percentage || 0}%` }}
              />
            </div>
            <p className="text-[10px] text-slate-600 mt-2">Target: &gt;75% within SLA</p>
          </CardContent>
        </Card>

        {/* KPI: Total Grievances */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-5 flex justify-between items-center">
            <div>
              <p className="text-slate-400 text-xs font-bold uppercase">Total Tickets</p>
              <p className="text-3xl font-bold text-white mt-1">
                {metrics?.ground?.total_grievances || groundData?.length || 0}
              </p>
              <p className="text-xs text-slate-500">
                {metrics?.ground?.resolved || 0} resolved
              </p>
            </div>
            <Target className="h-8 w-8 text-emerald-500 opacity-50" />
          </CardContent>
        </Card>

        {/* KPI: Digital Sentiment */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-5 flex justify-between items-center">
            <div>
              <p className="text-slate-400 text-xs font-bold uppercase">Digital Sentiment</p>
              <p className={`text-2xl font-bold mt-1 ${
                metrics?.digital?.overall_sentiment === 'Positive' ? 'text-green-400' :
                metrics?.digital?.overall_sentiment === 'Negative' ? 'text-red-400' : 'text-slate-400'
              }`}>
                {metrics?.digital?.overall_sentiment || "Neutral"}
              </p>
              <p className="text-xs text-slate-500">
                {(metrics?.digital?.positive || 0) + (metrics?.digital?.neutral || 0) + (metrics?.digital?.negative || 0)} analyzed
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-blue-500 opacity-50" />
          </CardContent>
        </Card>
      </div>

      {/* The Two Pillars: Digital vs Ground */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Pillar 1: Digital Perception */}
        <Card className="bg-slate-950 border-slate-800 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-3 opacity-10">
            <Share2 className="h-32 w-32 text-blue-500" />
          </div>
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Share2 className="h-5 w-5 text-blue-400" />
              Digital Perception
            </CardTitle>
            <CardDescription className="text-slate-400">Social Media Impact & Sentiment Analysis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 relative z-10">
            <div className="flex items-end justify-between">
              <div className="space-y-1">
                <span className={`text-4xl font-bold ${getScoreColor(scores.digitalPerception)}`}>
                  {scores.digitalPerception}
                </span>
                <span className="text-sm text-slate-500 block">/ 100 Score</span>
              </div>
              <div className="text-right space-y-1">
                 <Badge variant="outline" className="border-blue-900 text-blue-400 bg-blue-900/10">
                    {digitalData?.summary?.total_reach?.toLocaleString() || 0} Reach
                 </Badge>
              </div>
            </div>
            
            <Progress value={scores.digitalPerception} className="h-2 bg-slate-900" />

            {/* Sentiment Breakdown */}
            {metrics?.digital && (metrics.digital.positive + metrics.digital.neutral + metrics.digital.negative) > 0 && (
              <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800">
                <p className="text-xs text-slate-400 uppercase mb-3 font-semibold">Sentiment Breakdown</p>
                <div className="flex gap-4">
                  <div className="flex-1 text-center">
                    <p className="text-2xl font-bold text-green-400">{metrics.digital.positive}</p>
                    <p className="text-[10px] text-slate-500 uppercase">Positive</p>
                  </div>
                  <div className="flex-1 text-center">
                    <p className="text-2xl font-bold text-slate-400">{metrics.digital.neutral}</p>
                    <p className="text-[10px] text-slate-500 uppercase">Neutral</p>
                  </div>
                  <div className="flex-1 text-center">
                    <p className="text-2xl font-bold text-red-400">{metrics.digital.negative}</p>
                    <p className="text-[10px] text-slate-500 uppercase">Negative</p>
                  </div>
                </div>
                {metrics.digital.narrative && (
                  <p className="text-xs text-slate-400 mt-3 italic border-t border-slate-800 pt-3">
                    "{metrics.digital.narrative}"
                  </p>
                )}
              </div>
            )}

            <div className="grid grid-cols-3 gap-2 pt-2">
              <div className="bg-slate-900 p-3 rounded-lg text-center border border-slate-800">
                <ThumbsUp className="h-4 w-4 text-blue-400 mx-auto mb-2" />
                <span className="block text-xl font-bold text-white">
                  {digitalData?.posts?.reduce((acc, curr) => acc + getSafeLikeCount(curr), 0) || 0}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">Likes</span>
              </div>
              <div className="bg-slate-900 p-3 rounded-lg text-center border border-slate-800">
                <MessageCircle className="h-4 w-4 text-green-400 mx-auto mb-2" />
                <span className="block text-xl font-bold text-white">
                  {digitalData?.posts?.reduce((acc, curr) => acc + (curr.comments || 0), 0) || 0}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">Comments</span>
              </div>
              <div className="bg-slate-900 p-3 rounded-lg text-center border border-slate-800">
                <TrendingUp className="h-4 w-4 text-orange-400 mx-auto mb-2" />
                <span className="block text-xl font-bold text-white">
                  {digitalData?.summary?.total_engagement?.toLocaleString() || 0}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">Engage</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Pillar 2: Ground Stability */}
        <Card className="bg-slate-950 border-slate-800 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-3 opacity-10">
            <Users className="h-32 w-32 text-emerald-500" />
          </div>
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-400" />
              Ground Stability
            </CardTitle>
            <CardDescription className="text-slate-400">SLA-Based Grievance Resolution & Public Trust</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 relative z-10">
            <div className="flex items-end justify-between">
              <div className="space-y-1">
                <span className={`text-4xl font-bold ${getScoreColor(scores.groundStability)}`}>
                  {scores.groundStability}
                </span>
                <span className="text-sm text-slate-500 block">/ 100 SLA Score</span>
              </div>
              <div className="text-right space-y-1">
                 <Badge variant="outline" className="border-emerald-900 text-emerald-400 bg-emerald-900/10">
                    {groundData?.length || 0} Total Tickets
                 </Badge>
              </div>
            </div>

            <Progress value={scores.groundStability} className="h-2 bg-slate-900" />

            {/* SLA Details */}
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800">
              <p className="text-xs text-slate-400 uppercase mb-3 font-semibold">SLA Performance</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500">Resolved within SLA</p>
                  <p className="text-xl font-bold text-green-400">
                    {metrics?.ground?.resolved_within_sla || 0}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Total Resolved</p>
                  <p className="text-xl font-bold text-white">
                    {metrics?.ground?.resolved || groundData?.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length || 0}
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-800">
                <p className="text-[10px] text-slate-500 uppercase mb-1">SLA Targets</p>
                <div className="flex gap-2 text-[10px] text-slate-400">
                  <span className="bg-red-900/30 px-2 py-1 rounded">CRITICAL: 4h</span>
                  <span className="bg-orange-900/30 px-2 py-1 rounded">HIGH: 24h</span>
                  <span className="bg-yellow-900/30 px-2 py-1 rounded">MEDIUM: 72h</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="bg-slate-900/50 p-4 rounded-lg flex items-center gap-3 border border-slate-800">
                <div className="bg-green-900/20 p-2 rounded-full text-green-400">
                  <CheckCircle className="h-5 w-5" />
                </div>
                <div>
                  <span className="block text-xl font-bold text-white">
                    {groundData?.filter(g => g.status === 'resolved' || g.status === 'RESOLVED').length || 0}
                  </span>
                  <span className="text-xs text-slate-500 uppercase">Resolved</span>
                </div>
              </div>
              
              <div className="bg-slate-900/50 p-4 rounded-lg flex items-center gap-3 border border-slate-800">
                <div className="bg-red-900/20 p-2 rounded-full text-red-400">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <span className="block text-xl font-bold text-white">
                    {groundData?.filter(g => g.status !== 'resolved' && g.status !== 'RESOLVED').length || 0}
                  </span>
                  <span className="text-xs text-slate-500 uppercase">Pending</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Insights Chart */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">Engagement Velocity (Last 10 Posts)</CardTitle>
          <CardDescription className="text-slate-400">Visualizing how your digital content drives happiness metrics.</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={digitalData?.posts || []}>
              <defs>
                <linearGradient id="colorReach" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorEngage" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, {month:'short', day:'numeric'})} stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#fff' }} />
              <Area type="monotone" dataKey="reach" stroke="#3b82f6" fillOpacity={1} fill="url(#colorReach)" name="Reach" />
              <Area type="monotone" dataKey="engagement" stroke="#f97316" fillOpacity={1} fill="url(#colorEngage)" name="Engagement" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

    </div>
  );
};

export default HappinessReport;
