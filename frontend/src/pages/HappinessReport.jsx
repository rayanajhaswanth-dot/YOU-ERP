import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { Loader2, Smile, TrendingUp, Users, Activity, AlertTriangle, CheckCircle, Share2, MessageCircle, ThumbsUp } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const HappinessReport = () => {
  const [loading, setLoading] = useState(true);
  const [digitalData, setDigitalData] = useState(null);
  const [groundData, setGroundData] = useState(null);
  const [scores, setScores] = useState({
    happinessIndex: 50, // Default to neutral start
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

      // Parallel Fetching: Analytics (Digital) & Grievances (Ground)
      const [analyticsRes, grievancesRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/analytics/campaigns`, { headers }),
        fetch(`${BACKEND_URL}/api/grievances/`, { headers }) 
      ]);

      let digital = { summary: { total_reach: 0, total_engagement: 0, platform_breakdown: {} }, posts: [] };
      let grievances = [];

      if (analyticsRes.ok) digital = await analyticsRes.json();
      if (grievancesRes.ok) grievances = await grievancesRes.json();

      setDigitalData(digital);
      setGroundData(grievances);

      // --- ALGORITHM V2: LAUNCH MODE (High Sensitivity) ---

      // 1. Ground Stability Calculation
      const totalGrievances = grievances.length;
      const resolvedGrievances = grievances.filter(g => g.status === 'resolved').length;
      
      let groundStabilityScore = 50; // Default Neutral
      if (totalGrievances > 0) {
        // Simple Percentage Resolution Rate
        groundStabilityScore = Math.round((resolvedGrievances / totalGrievances) * 100);
      }

      // 2. Digital Perception Calculation
      // Logic: (Engagement * 2) points + (Reach / 50) points. Max 100.
      // This ensures even 1 like gives 2 points visible on the board.
      const engagementPoints = (digital.summary.total_engagement || 0) * 2;
      const reachPoints = (digital.summary.total_reach || 0) / 50;
      
      const rawDigitalScore = engagementPoints + reachPoints;
      // Cap at 100, but ensure at least 5 points if there is ANY activity at all
      const digitalPerceptionScore = rawDigitalScore > 0 
        ? Math.min(100, Math.max(5, Math.round(rawDigitalScore))) 
        : 0;

      // 3. Overall Happiness Index
      const happinessIndex = Math.round((groundStabilityScore + digitalPerceptionScore) / 2);

      setScores({
        happinessIndex,
        digitalPerception: digitalPerceptionScore,
        groundStability: groundStabilityScore
      });

    } catch (error) {
      console.error("Failed to compile Happiness Report:", error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 75) return "text-green-500";
    if (score >= 50) return "text-yellow-500";
    return "text-red-500";
  };

  // Helper to safely get counts (Data Healing)
  // If likes are 0 but engagement is high, use engagement as a proxy for likes to show visual activity
  const getSafeLikeCount = (post) => {
    if (post.likes > 0) return post.likes;
    if (post.engagement > 0 && post.comments === 0) return post.engagement; // Likely all likes
    return 0;
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
    <div className="p-6 space-y-8 animate-in fade-in duration-700">
      
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
              Algorithm: Launch Mode v2.0
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
            <CardDescription className="text-slate-400">Social Media Impact & Reach Analysis</CardDescription>
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

            <div className="grid grid-cols-3 gap-2 pt-2">
              {/* LIKES: Uses safe fallback logic */}
              <div className="bg-slate-900 p-3 rounded-lg text-center border border-slate-800">
                <ThumbsUp className="h-4 w-4 text-blue-400 mx-auto mb-2" />
                <span className="block text-xl font-bold text-white">
                  {digitalData?.posts?.reduce((acc, curr) => acc + getSafeLikeCount(curr), 0) || 0}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">Likes</span>
              </div>
              {/* COMMENTS */}
              <div className="bg-slate-900 p-3 rounded-lg text-center border border-slate-800">
                <MessageCircle className="h-4 w-4 text-green-400 mx-auto mb-2" />
                <span className="block text-xl font-bold text-white">
                  {digitalData?.posts?.reduce((acc, curr) => acc + (curr.comments || 0), 0) || 0}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">Comments</span>
              </div>
              {/* ENGAGEMENT */}
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
            <CardDescription className="text-slate-400">Grievance Resolution & Public Trust</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 relative z-10">
            <div className="flex items-end justify-between">
              <div className="space-y-1">
                <span className={`text-4xl font-bold ${getScoreColor(scores.groundStability)}`}>
                  {scores.groundStability}
                </span>
                <span className="text-sm text-slate-500 block">/ 100 Score</span>
              </div>
              <div className="text-right space-y-1">
                 <Badge variant="outline" className="border-emerald-900 text-emerald-400 bg-emerald-900/10">
                    {groundData?.length || 0} Total Tickets
                 </Badge>
              </div>
            </div>

            <Progress value={scores.groundStability} className="h-2 bg-slate-900" />

            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="bg-slate-900/50 p-4 rounded-lg flex items-center gap-3 border border-slate-800">
                <div className="bg-green-900/20 p-2 rounded-full text-green-400">
                  <CheckCircle className="h-5 w-5" />
                </div>
                <div>
                  <span className="block text-xl font-bold text-white">
                    {groundData?.filter(g => g.status === 'resolved').length || 0}
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
                    {groundData?.filter(g => g.status !== 'resolved').length || 0}
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
