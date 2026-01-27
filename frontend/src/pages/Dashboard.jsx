import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import BroadcastWidget from '../components/BroadcastWidget';
import GrievanceFeed from '../components/GrievanceFeed';
import SentimentDashboard from '../components/SentimentDashboard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
};

export default function Dashboard({ user }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/dashboard/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
      data-testid="briefing-room"
    >
      {/* Header Section */}
      <motion.div variants={itemVariants} className="pb-4">
        <h1 
          className="text-3xl font-bold text-white mb-1"
          data-testid="greeting"
        >
          {getGreeting()}, {user?.full_name?.split(' ')[0] || 'Leader'}.
        </h1>
        <p className="text-gray-400">
          Here's your operational briefing for today.
        </p>
      </motion.div>

      {/* Quick Stats Bar */}
      {stats && (
        <motion.div 
          variants={itemVariants}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
          data-testid="quick-stats"
        >
          <div className="bg-[#1F2937] rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Pending</p>
            <p className="text-2xl font-bold text-white">{stats.pending_grievances}</p>
          </div>
          <div className="bg-[#1F2937] rounded-lg p-4 border border-red-900/30">
            <p className="text-xs text-red-400 uppercase tracking-wider">Critical</p>
            <p className="text-2xl font-bold text-red-400">{stats.critical_alerts}</p>
          </div>
          <div className="bg-[#1F2937] rounded-lg p-4 border border-green-900/30">
            <p className="text-xs text-green-400 uppercase tracking-wider">Resolved</p>
            <p className="text-2xl font-bold text-green-400">{stats.resolved_today}</p>
          </div>
          <div className="bg-[#1F2937] rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Total</p>
            <p className="text-2xl font-bold text-[#FF9933]">{stats.total}</p>
          </div>
        </motion.div>
      )}

      {/* Executive Feed - Vertical Layout */}
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Widget 1: Broadcast (Action) */}
        <motion.div variants={itemVariants}>
          <BroadcastWidget />
        </motion.div>

        {/* Widget 2: Grievance Feed (Reality/Crisis) */}
        <motion.div variants={itemVariants}>
          <GrievanceFeed />
        </motion.div>

        {/* Widget 3: Sentiment Dashboard (Perception/Intel) */}
        <motion.div variants={itemVariants}>
          <SentimentDashboard />
        </motion.div>
      </div>
    </motion.div>
  );
}
