import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import BroadcastWidget from '../components/BroadcastWidget';
import SentimentDashboard from '../components/SentimentDashboard';
import GrievanceFeed from '../components/GrievanceFeed';
import KPIGrid from '../components/KPIGrid';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
};

export default function Dashboard({ user }) {
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
      <motion.div variants={itemVariants}>
        <h1 className="text-3xl font-bold text-white mb-1">
          {getGreeting()}, {user?.full_name?.split(' ')[0] || 'Leader'}.
        </h1>
        <p className="text-gray-400">Here is your daily governance briefing.</p>
      </motion.div>

      {/* KPI Grid */}
      <motion.div variants={itemVariants}>
        <KPIGrid />
      </motion.div>

      {/* Broadcast Widget */}
      <motion.div variants={itemVariants}>
        <BroadcastWidget />
      </motion.div>

      {/* Executive Briefing (Sentiment) */}
      <motion.div variants={itemVariants}>
        <SentimentDashboard />
      </motion.div>

      {/* Critical Alerts (Grievances) */}
      <motion.div variants={itemVariants} className="pb-8">
        <GrievanceFeed />
      </motion.div>
    </motion.div>
  );
}
