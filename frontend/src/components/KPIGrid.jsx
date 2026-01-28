import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle, Users, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

const KPICard = ({ label, value, subtext, icon: Icon, trend, color }) => (
  <div className="bg-[#1F2937] p-5 rounded-xl border border-gray-700 shadow-lg flex flex-col justify-between h-32 relative overflow-hidden">
    <div className="flex justify-between items-start z-10">
      <div>
        <p className="text-gray-400 text-xs font-bold uppercase tracking-wider">{label}</p>
        <h3 className={`text-3xl font-extrabold mt-1 ${color}`}>{value}</h3>
      </div>
      <div className={`p-2 rounded-lg bg-[#111827] ${color} bg-opacity-10`}>
        <Icon size={20} className={color} />
      </div>
    </div>
    
    <div className="flex items-center gap-1 mt-2 z-10">
      {trend === 'up' && <ArrowUpRight size={14} className="text-green-400" />}
      {trend === 'down' && <ArrowDownRight size={14} className="text-red-400" />}
      {trend === 'neutral' && <Minus size={14} className="text-gray-400" />}
      <span className="text-xs text-gray-400">{subtext}</span>
    </div>

    {/* Background Decoration */}
    <Icon size={80} className={`absolute -bottom-4 -right-4 opacity-5 ${color}`} />
  </div>
);

const KPIGrid = () => {
  const [stats, setStats] = useState({
    approval: 0,
    critical: 0,
    volume: 0,
    momentum: 0
  });
  const [loading, setLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [socialRes, grievanceRes] = await Promise.all([
            fetch('/api/social/dashboard'),
            fetch('/api/dashboard/grievances')
        ]);

        if (!socialRes.ok || !grievanceRes.ok) {
            throw new Error("Backend unavailable");
        }

        const socialData = await socialRes.json();
        const grievanceData = await grievanceRes.json();

        // 1. CALCULATE APPROVAL (Latest)
        const latestSocial = Array.isArray(socialData) && socialData.length > 0 ? socialData[0] : null;
        const prevSocial = Array.isArray(socialData) && socialData.length > 1 ? socialData[1] : null;

        const getApproval = (item) => {
            if (!item) return 0;
            const pos = Number(item.positive_count) || 0;
            const neg = Number(item.negative_count) || 0;
            const neu = Number(item.neutral_count) || 0;
            const total = pos + neg + neu;
            return total > 0 ? Math.round((pos / total) * 100) : 0;
        };

        const currentApproval = getApproval(latestSocial);
        
        // FIX: If no previous data exists (Day 1), assume stable trend (compare to current)
        const prevApproval = prevSocial ? getApproval(prevSocial) : currentApproval;
        
        // TREND calculation
        const trendValue = currentApproval - prevApproval;

        // TOTAL VOLUME
        const volume = latestSocial 
            ? (Number(latestSocial.positive_count) || 0) + (Number(latestSocial.negative_count) || 0) + (Number(latestSocial.neutral_count) || 0)
            : 0;

        // 2. CALCULATE CRITICAL ISSUES (Ground Reality)
        const validGrievances = Array.isArray(grievanceData) ? grievanceData.filter(g => g) : [];
        const criticalCount = validGrievances.filter(g => g.priority_level === 'CRITICAL' || g.priority_level === 'HIGH').length;

        setStats({
            approval: currentApproval,
            critical: criticalCount,
            volume: volume,
            momentum: trendValue
        });

      } catch (err) {
        console.warn("KPI Error (Switching to Demo Mode):", err);
        setIsDemoMode(true);
        // Fallback for demo/simulation
        setStats({ approval: 65, critical: 3, volume: 142, momentum: 5 });
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) return <div className="h-32 bg-[#1F2937] rounded-xl animate-pulse"></div>;

  return (
    <div className="relative">
        {isDemoMode && (
            <div className="absolute -top-6 right-0 text-[10px] text-gray-500 uppercase tracking-widest font-semibold bg-gray-800 px-2 py-0.5 rounded border border-gray-700">
                SIMULATION MODE
            </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* 1. APPROVAL RATING */}
        <KPICard 
            label="Approval Rating" 
            value={`${stats.approval}%`} 
            subtext="Public sentiment score"
            icon={TrendingUp} 
            color="text-[#FF9933]" 
            trend={stats.approval >= 50 ? "up" : "down"}
        />
        
        {/* 2. POLITICAL MOMENTUM */}
        <KPICard 
            label="Political Momentum" 
            value={`${stats.momentum > 0 ? '+' : ''}${stats.momentum}%`} 
            subtext="Change vs. yesterday"
            icon={TrendingUp} 
            color={stats.momentum > 0 ? "text-green-400" : stats.momentum < 0 ? "text-red-400" : "text-gray-400"} 
            trend={stats.momentum > 0 ? "up" : stats.momentum < 0 ? "down" : "neutral"}
        />

        {/* 3. ACTIVE CRITICALS */}
        <KPICard 
            label="Active Criticals" 
            value={stats.critical} 
            subtext="Urgent issues pending"
            icon={AlertTriangle} 
            color={stats.critical > 0 ? "text-red-500" : "text-green-500"} 
            trend={stats.critical > 0 ? "down" : "up"}
        />

        {/* 4. CITIZEN ENGAGEMENTS */}
        <KPICard 
            label="Daily Engagement" 
            value={stats.volume} 
            subtext="Interactions today"
            icon={Users} 
            color="text-blue-400" 
            trend="up"
        />
        </div>
    </div>
  );
};

export default KPIGrid;
