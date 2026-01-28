import React, { useState, useEffect } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, ShieldCheck, ShieldAlert, Activity, ThumbsUp, ThumbsDown } from 'lucide-react';

const SentimentDashboard = () => {
  // State initialization with safe defaults
  const [chartData, setChartData] = useState([]);
  const [metrics, setMetrics] = useState({
    approval: 50,
    isNegative: false,
    spikeDetected: false,
    totalInteractions: 0,
    safePos: 0,
    safeNeg: 0
  });
  const [groundIntel, setGroundIntel] = useState({
    topIssue: "General",
    topLocation: "Constituency",
    criticalCount: 0,
    highCount: 0,
    stabilityScore: 100,
    topIssuePercent: 0
  });
  
  const [loading, setLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const fetchIntel = async () => {
      try {
        const [socialRes, grievanceRes] = await Promise.all([
            fetch('/api/social/dashboard'),
            fetch('/api/dashboard/grievances')
        ]);

        const socialData = socialRes.ok ? await socialRes.json() : [];
        const grievanceData = grievanceRes.ok ? await grievanceRes.json() : [];

        if (!isMounted) return;

        // --- 1. PROCESS SENTIMENT (Digital) ---
        // Defensive filtering: Ensure we only map over valid objects
        const validSocial = Array.isArray(socialData) ? socialData.filter(item => item && typeof item === 'object') : [];
        
        const processedChart = validSocial.slice().reverse().map(item => {
            const p = Number(item.positive_count) || 0;
            const n = Number(item.negative_count) || 0;
            return {
                name: item.report_date ? new Date(item.report_date).toLocaleDateString(undefined, { weekday: 'short' }) : 'Day',
                score: p - n, 
                positive: p,
                negative: n,
                isSpike: item.spike_detected === true
            };
        });

        // Calculate Latest Metrics immediately to avoid render-cycle gaps
        const latest = processedChart.length > 0 ? processedChart[processedChart.length - 1] : { positive: 0, negative: 0, isSpike: false };
        const safePos = latest.positive;
        const safeNeg = latest.negative;
        const total = safePos + safeNeg; // Simplified total for stability
        const approval = total > 0 ? Math.round((safePos / total) * 100) : 50;
        
        setChartData(processedChart);
        setMetrics({
            approval,
            isNegative: approval < 50,
            spikeDetected: latest.isSpike,
            totalInteractions: total,
            safePos,
            safeNeg
        });

        // --- 2. PROCESS GRIEVANCES (Ground) ---
        const validGrievances = Array.isArray(grievanceData) ? grievanceData.filter(g => g && typeof g === 'object') : [];
        
        const issues = {};
        const locations = {};
        let critical = 0;
        let high = 0;

        validGrievances.forEach(g => {
            const type = String(g.issue_type || "General");
            const loc = String(g.village || "Constituency");
            const prio = String(g.priority_level || "LOW");

            issues[type] = (issues[type] || 0) + 1;
            locations[loc] = (locations[loc] || 0) + 1;

            if (prio === 'CRITICAL') critical++;
            if (prio === 'HIGH') high++;
        });

        // Find Top Issue
        const sortedIssues = Object.entries(issues).sort((a,b) => b[1] - a[1]);
        const sortedLocs = Object.entries(locations).sort((a,b) => b[1] - a[1]);
        
        const topIssueName = sortedIssues.length > 0 ? sortedIssues[0][0] : "General";
        const topIssueVol = sortedIssues.length > 0 ? sortedIssues[0][1] : 0;
        const totalGrievances = validGrievances.length;
        const percentage = totalGrievances > 0 ? Math.round((topIssueVol / totalGrievances) * 100) : 0;

        // Calculate Stability (100 - penalties)
        const penalty = (critical * 15) + (high * 5);
        const stability = Math.max(0, 100 - penalty);

        setGroundIntel({
            topIssue: topIssueName,
            topLocation: sortedLocs.length > 0 ? sortedLocs[0][0] : "Constituency",
            criticalCount: critical,
            highCount: high,
            stabilityScore: stability,
            topIssuePercent: percentage
        });

      } catch (err) {
        console.error("Dashboard Safe Mode Activated:", err);
        if (isMounted) setIsDemoMode(true);
        // Fallback data prevents crashes
        setChartData([{ name: 'Today', score: 0, positive: 0, negative: 0, isSpike: false }]);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchIntel();
    return () => { isMounted = false; };
  }, []);

  // --- SAFE RENDERING HELPERS ---
  const getDigitalReasoning = () => {
      if (metrics.spikeDetected) return `Result: Critical Negative Spike. Cause: Sudden surge in negative reactions detected.`;
      if (metrics.isNegative) return `Result: Negative Trend. Cause: Negative feedback (${metrics.safeNeg}) exceeds positive (${metrics.safePos}).`;
      return `Result: Positive Trend. Cause: Strong engagement with ${metrics.safePos} positive interactions today.`;
  };

  const getGroundReasoning = () => {
      const urgent = groundIntel.criticalCount + groundIntel.highCount;
      if (urgent === 0) return "Result: Operations Stable. Cause: No critical tickets pending.";
      return `Result: ${urgent} Urgent Issues. Cause: High volume of '${groundIntel.topIssue}' reports (${groundIntel.topIssuePercent}% of total).`;
  };

  const isGroundCritical = groundIntel.stabilityScore < 50;

  if (loading) return <div className="h-48 bg-[#1F2937] rounded-xl animate-pulse border border-gray-800 flex items-center justify-center text-gray-500">Loading Briefing...</div>;

  return (
    <div className="bg-[#1F2937] rounded-xl shadow-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-[#111827] px-6 py-4 border-b border-gray-700 flex justify-between items-center">
        <h3 className="text-[#FF9933] font-bold text-lg flex items-center gap-2">
            <Activity size={20} /> Executive Briefing
        </h3>
        {isDemoMode && <span className="text-[10px] bg-gray-800 text-gray-400 px-2 py-1 rounded border border-gray-700">OFFLINE</span>}
      </div>

      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* COL 1: DIGITAL SENTIMENT */}
        <div className="border-r border-gray-800 pr-6">
            <div className="flex items-center gap-2 mb-4">
                <Activity size={16} className={metrics.isNegative ? "text-red-500" : "text-green-500"} />
                <span className="text-gray-400 text-xs font-bold uppercase tracking-widest">Digital Perception</span>
            </div>
            
            <div className="flex items-baseline gap-3 mb-2">
                <h1 className={`text-5xl font-extrabold ${metrics.spikeDetected ? 'text-red-500' : 'text-[#FF9933]'}`}>
                    {metrics.approval}%
                </h1>
                <span className="text-sm text-gray-400 uppercase font-medium">Approval</span>
            </div>

            <p className="text-sm text-gray-300 font-medium mb-4 leading-relaxed border-l-2 border-gray-600 pl-3">
               {getDigitalReasoning()}
            </p>

            <div className="flex gap-4 mb-2">
                <div className="flex items-center gap-1 text-green-400 text-xs">
                    <ThumbsUp size={12} /> {metrics.safePos} Pos
                </div>
                <div className="flex items-center gap-1 text-red-400 text-xs">
                    <ThumbsDown size={12} /> {metrics.safeNeg} Neg
                </div>
            </div>

            {/* Chart Area */}
            <div className="h-16 w-full mt-auto opacity-40">
                {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                            <Area type="monotone" dataKey="score" stroke="#FF9933" fill="#FF9933" />
                        </AreaChart>
                    </ResponsiveContainer>
                ) : <div className="text-xs text-gray-600">No trend data available</div>}
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
                    {groundIntel.stabilityScore}%
                </h1>
                <span className="text-sm text-gray-400 uppercase font-medium">Satisfaction</span>
            </div>

            <div className="bg-[#111827] p-3 rounded border-l-2 border-blue-500 mb-2">
                <p className="text-sm text-gray-300 leading-relaxed">
                   {getGroundReasoning()}
                </p>
            </div>
            
            {(groundIntel.criticalCount > 0 || groundIntel.highCount > 0) && (
                <div className="flex gap-4 mt-2">
                    <span className="text-xs text-red-400 font-bold flex items-center gap-1">
                        <AlertTriangle size={12} /> {groundIntel.criticalCount} Critical
                    </span>
                    <span className="text-xs text-orange-400 font-bold flex items-center gap-1">
                        <Activity size={12} /> {groundIntel.highCount} High Priority
                    </span>
                </div>
            )}
        </div>
      </div>
    </div>
  );
};

export default SentimentDashboard;
