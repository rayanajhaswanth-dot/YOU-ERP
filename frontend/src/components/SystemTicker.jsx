import React from 'react';
import { CheckCircle, TrendingUp, TrendingDown } from "lucide-react";

const SystemTicker = ({ resolvedYesterday = 0, sentimentChange = "+0%" }) => {
  const isPositive = sentimentChange.includes('+');

  return (
    <div className="bg-slate-900/95 backdrop-blur border-b border-slate-800 p-2 flex items-center justify-between sticky top-0 z-50 shadow-md">
      <div className="flex items-center gap-6 animate-in slide-in-from-top duration-500">
        
        {/* Metric 1: Resolutions */}
        <div className="flex items-center gap-2 px-4 border-r border-slate-800">
          <CheckCircle className="h-4 w-4 text-emerald-500" />
          <span className="text-xs font-semibold text-slate-300">
            Resolved Yesterday: <span className="text-white font-bold">{resolvedYesterday}</span>
          </span>
        </div>

        {/* Metric 2: Sentiment Shift */}
        <div className="flex items-center gap-2 px-4">
          {isPositive ? <TrendingUp className="h-4 w-4 text-blue-500" /> : <TrendingDown className="h-4 w-4 text-red-500" />}
          <span className="text-xs font-semibold text-slate-300">
            Sentiment: <span className={isPositive ? "text-blue-400 font-bold" : "text-red-400 font-bold"}>{sentimentChange}</span>
          </span>
        </div>

      </div>
      
      <div className="flex items-center gap-2 px-4">
        <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
        <span className="text-[10px] text-slate-500 uppercase tracking-widest hidden md:block">
          System Operational
        </span>
      </div>
    </div>
  );
};

export default SystemTicker;
