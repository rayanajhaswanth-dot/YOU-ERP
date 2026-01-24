import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const systemEvents = [
  { type: 'resolved', message: 'Grievance #G-1247 resolved - Water supply issue in Sector 12' },
  { type: 'meeting', message: 'Scheduled: Village meeting at Rampur - 3:00 PM' },
  { type: 'post', message: 'Post approved for Twitter: Infrastructure update' },
  { type: 'alert', message: 'High priority grievance received - Road accident assistance needed' },
  { type: 'sentiment', message: 'Sentiment trend: +12% positive mentions this week' }
];

export default function SystemTicker() {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % systemEvents.length);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getEventColor = (type) => {
    switch (type) {
      case 'resolved':
        return 'text-emerald-400';
      case 'alert':
        return 'text-rose-400';
      case 'post':
        return 'text-sky-400';
      case 'sentiment':
        return 'text-amber-400';
      default:
        return 'text-orange-400';
    }
  };

  return (
    <div data-testid="system-ticker" className="fixed bottom-0 left-0 right-0 h-10 bg-slate-950 border-t border-slate-800 flex items-center z-50 overflow-hidden">
      <motion.div
        key={currentIndex}
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -100 }}
        className="flex items-center gap-4 px-6 w-full"
      >
        <span className="text-xs font-mono text-slate-600">SYSTEM LOG</span>
        <div className="h-1 w-1 rounded-full bg-orange-500 animate-pulse"></div>
        <span className={`text-sm font-mono ${getEventColor(systemEvents[currentIndex].type)} flex-1`}>
          {systemEvents[currentIndex].message}
        </span>
      </motion.div>
    </div>
  );
}