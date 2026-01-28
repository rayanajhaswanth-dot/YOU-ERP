import React, { useEffect } from 'react';
import KPIGrid from '../components/KPIGrid';
import SentimentDashboard from '../components/SentimentDashboard';
import GrievanceFeed from '../components/GrievanceFeed';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Basic auth check
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
    }
  }, [navigate]);

  return (
    <div className="p-6 space-y-6">
      {/* Header Section */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">The Briefing Room</h1>
        <p className="text-slate-400">Real-time governance intelligence and operational status.</p>
      </div>

      {/* 1. KPI Scoreboard */}
      <div className="w-full">
        <KPIGrid />
      </div>

      {/* 2. Main Intelligence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Sentiment & Intel (Takes 2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          <SentimentDashboard />
        </div>

        {/* Right Column: Operational Reality (Takes 1/3 width) */}
        <div className="space-y-6">
           {/* CTO UPDATE: Cleaned up UI. GrievanceFeed is now the sole focus here. */}
          <GrievanceFeed />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
