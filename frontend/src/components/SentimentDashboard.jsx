import React, { useState, useEffect } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, ShieldCheck, ShieldAlert, Activity, ThumbsUp, ThumbsDown } from 'lucide-react';

const SentimentDashboard = () => {
  const [sentimentData, setSentimentData] = useState([]);
  const [topIssue, setTopIssue] = useState("None");
  const [grievanceStats, setGrievanceStats] = useState({ 
      total: 0, 
      criticalCount: 0, 
      highCount: 0, 
      topIssuePercentage: 0
  });
  const [loading, setLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [spikeDetected, setSpikeDetected] = useState(false);

  useEffect(() => {
    const fetchIntel = async () => {
      try {
        // WORLD-CLASS ARCHITECTURE: Parallel Fetching
        const [socialRes, grievanceRes] = await Promise.all([
            fetch('/api/social/dashboard'),
            fetch('/api/dashboard/grievances')
        ]);

        const socialData = socialRes.ok ? await socialRes.json() : [];
        const grievanceData = grievanceRes.ok ? await grievanceRes.json() : [];

        // 1. PROCESS SENTIMENT (Online Truth)
        // Filter nulls to prevent crashes
        const validSocialData = Array.isArray(socialData) ? socialData.filter(item => item) : [];
        const processedChart = validSocialData.slice().reverse().map(item => {
            const pos = Number(item.positive_count) || 0;
            const neg = Number(item.negative_count) || 0;
            return {
                name: item.report_date ? new Date(item.report_date).toLocaleDateString(undefined, { weekday: 'short' }) : 'Day',
                score: pos - neg, 
                positive: pos,
                negative: neg,
                isSpike: item.spike_detected === true
            };
        });
        setSentimentData(processedChart);
        if (processedChart.length > 0) setSpikeDetected(processedChart[processedChart.length - 1].isSpike);

        // 2. PROCESS GROUND REALITY METRICS (Offline Truth)
        if (Array.isArray(grievanceData) && grievanceData.length > 0) {
            const validGrievances = grievanceData.filter(g => g);
            const total = validGrievances.length;
            
            const issues = {};
            let critical = 0;
            let high = 0;

            validGrievances.forEach(g => {
                const type = g.issue_type || "General";
                const priority = g.priority_level || "LOW";

                // Frequency Count
                issues[type] = (issues[type] || 0) + 1;

                // Severity Count
                if (priority === 'CRITICAL') critical++;
                if (priority === 'HIGH') high++;
            });

            // Sort to find Top Issue
            const sortedIssues = Object.entries(issues).sort((a,b) => b[1] - a[1]);
            
            // Calculate Stats
            const topIssueName = sortedIssues.length > 0 ? sortedIssues[0][0] : "General";
            const topIssueVol = sortedIssues.length > 0 ? sortedIssues[0][1] : 0;
            const percentage = total > 0 ? Math.round((topIssueVol / total) * 100) : 0;

            setTopIssue(topIssueName);

            setGrievanceStats({
                total: total,
                criticalCount: critical,
                highCount: high,
                topIssuePercentage: percentage
            });
        }

      } catch (err) {
        console.warn("Intel Error, switching to demo mode", err);
        setIsDemoMode(true);
        // Fallback Demo Data
        setSentimentData([
            { name: 'Mon', score: 10, positive: 20, negative: 10, isSpike: false },
            { name: 'Tue', score: -5, positive: 15, negative: 20, isSpike: false },
            { name: 'Wed', score: 5, positive: 18, negative: 13, isSpike: false },
            { name: 'Thu', score: -15, positive: 10, negative: 25, isSpike: true },
            { name: 'Fri', score: -10, positive: 12, negative: 22, isSpike: false },
        ]);
        setTopIssue("Water Supply");
        setGrievanceStats({ total: 10, criticalCount: 3, highCount: 2, topIssuePercentage: 60 });
        setSpikeDetected(true);
      } finally {
        setLoading(false);
      }
    };
    fetchIntel();
  }, []);

  // --- DERIVED INTELLIGENCE ---
  // Safe extraction of latest data point
  const latest = sentimentData.length > 0 ? sentimentData[sentimentData.length - 1] : { positive: 0, negative: 0 };
  const prev = sentimentData.length > 1 ? sentimentData[sentimentData.length - 2] : { positive: 0, negative: 0 };

  const safePos = Number(latest.positive) || 0;
  const safeNeg = Number(latest.negative) || 0;
  const total = safePos + safeNeg + (Number(latest.neutral)||0);
  
  // Metric: Approval Rating (Default 50% if no data)
  const approval = total > 0 ? Math.round((safePos / total) * 100) : 50;
  
  // Logic for Alert State
  const isNegative = approval < 50;
  
  // Ground Logic: Stability Score (100% = Perfect)
  // Deduct 15% for Critical, 5% for High
  const penalty = (grievanceStats.criticalCount * 15) + (grievanceStats.highCount * 5);
  const stabilityScore = Math.max(0, 100 - penalty);
  const isGroundCritical = stabilityScore < 50;

  // SIMPLE REASONING: RESULT + CAUSE
  const getDigitalReasoning = () => {
      // Spike detected
      if (spikeDetected) {
          return `Result: Critical Negative Spike. Cause: Sudden surge in negative reactions detected in the last 24 hours.`;
      }
      
      // Negative Sentiment
      if (isNegative) {
          return `Result: Sentiment is Negative. Cause: Volume of 'Angry' or 'Sad' reactions is currently outpacing positive engagement.`;
      }
      
      // Positive Sentiment
      return `Result: Sentiment is Positive. Cause: Recent posts are generating consistent 'Like' and 'Heart' reactions from the community.`;
  };

  const getGroundReasoning = () => {
      if (stabilityScore === 100) return "Result: Operations Stable. Cause: No critical or high priority issues pending.";
      
      return `Result: Stability impacted. Cause: ${grievanceStats.topIssuePercentage}% of all pending issues relate to '${topIssue}'.`;
  };

  if (loading) return <div className="h-48 bg-[#1F2937] rounded-xl animate-pulse border border-gray-800"></div>;

  return (
    <div className="bg-[#1F2937] rounded-xl shadow-lg border border-gray-700 overflow-hidden">
      <div className="bg-[#111827] px-6 py-4 border-b border-gray-700 flex justify-between items-center">
        <h3 className="text-[#FF9933] font-bold text-lg flex items-center gap-2">
            <Activity size={20} /> Executive Briefing
        </h3>
        {isDemoMode && <span className="text-[10px] bg-gray-800 text-gray-400 px-2 py-1 rounded border border-gray-700">SIMULATION</span>}
      </div>

      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* COL 1: DIGITAL SENTIMENT */}
        <div className="border-r border-gray-800 pr-6">
            <div className="flex items-center gap-2 mb-4">
                <Activity size={16} className={isNegative ? "text-red-500" : "text-green-500"} />
                <span className="text-gray-400 text-xs font-bold uppercase tracking-widest">Digital Perception</span>
            </div>
            
            <div className="flex items-baseline gap-3 mb-2">
                <h1 className={`text-5xl font-extrabold ${spikeDetected ? 'text-red-500' : 'text-[#FF9933]'}`}>
                    {approval}%
                </h1>
                <span className="text-sm text-gray-400 uppercase font-medium">Approval</span>
            </div>

            {/* REASONING: PURELY DIGITAL */}
            <p className="text-sm text-gray-300 font-medium mb-4 leading-relaxed">
               {getDigitalReasoning()}
            </p>

            {/* MINI METRICS - New Requirement */}
            <div className="flex gap-4 mb-2">
                <div className="flex items-center gap-1 text-green-400 text-xs">
                    <ThumbsUp size={12} /> {safePos} Pos
                </div>
                <div className="flex items-center gap-1 text-red-400 text-xs">
                    <ThumbsDown size={12} /> {safeNeg} Neg
                </div>
            </div>

            {/* Context Chart */}
            <div className="h-12 w-full mt-auto opacity-40">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={sentimentData}>
                        <Area type="monotone" dataKey="score" stroke="#FF9933" fill="#FF9933" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>

        {/* COL 2: GROUND REALITY */}
        <div className="pl-2">
            <div className="flex items-center gap-2 mb-4">
                <ShieldCheck size={16} className={isGroundCritical ? "text-red-500" : "text-blue-400"} />
                <span className="text-gray-400 text-xs font-bold uppercase tracking-widest">Ground Stability</span>
            </div>
            
            <div className="flex items-baseline gap-3 mb-2">
                <h1 className={`text-5xl font-extrabold ${isGroundCritical ? 'text-red-500' : 'text-blue-400'}`}>
                    {stabilityScore}%
                </h1>
                <span className="text-sm text-gray-400 uppercase font-medium">Satisfaction</span>
            </div>

            {/* REASONING: SUMMARY BASED */}
            <div className="bg-[#111827] p-3 rounded border-l-2 border-blue-500 mb-2">
                <p className="text-sm text-gray-300 leading-relaxed">
                   {getGroundReasoning()}
                </p>
            </div>
            
            {/* Simple Stats */}
            {stabilityScore < 100 && (
                <div className="flex gap-4 mt-2">
                    <span className="text-xs text-red-400 font-bold flex items-center gap-1">
                        <AlertTriangle size={10} /> {grievanceStats.criticalCount} Critical
                    </span>
                    <span className="text-xs text-orange-400 font-bold flex items-center gap-1">
                        <Activity size={10} /> {grievanceStats.highCount} High Priority
                    </span>
                </div>
            )}
        </div>
      </div>
    </div>
  );
};

export default SentimentDashboard;
