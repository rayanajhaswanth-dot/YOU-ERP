import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { FileText, TrendingUp, AlertTriangle } from "lucide-react";

const ConstituencySummary = ({ grievances = [], sentiment = {} }) => {
  // Dynamic Logic to generate the summary text
  const total = grievances.length;
  const critical = grievances.filter(g => g.priority === 'CRITICAL').length;
  const resolved = grievances.filter(g => g.status === 'resolved').length;
  
  // Find top category
  const categories = grievances.map(g => {
      const text = g.description ? g.description.toLowerCase() : "";
      if (text.includes('water')) return 'Water Supply';
      if (text.includes('road')) return 'Road Infrastructure';
      if (text.includes('elect')) return 'Power Supply';
      return 'General Civic';
  });
  
  const frequency = {};
  categories.forEach(c => frequency[c] = (frequency[c] || 0) + 1);
  const topCategory = Object.keys(frequency).length > 0 
    ? Object.keys(frequency).reduce((a, b) => frequency[a] > frequency[b] ? a : b, "General Issues")
    : "General Issues";

  return (
    <Card className="bg-slate-950 border-slate-800 shadow-lg">
      <CardHeader className="pb-3 border-b border-slate-900">
        <CardTitle className="text-white flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-blue-500" />
          Constituency Intelligence Briefing
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        
        {/* Ground Situation */}
        <div className="flex gap-3">
          <div className="mt-1 min-w-[20px]">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Ground Situation</h4>
            <p className="text-sm text-slate-300 leading-relaxed">
              Active grievances have reached <strong>{total}</strong>. The dominant narrative on the ground concerns <strong>{topCategory}</strong>. 
              <span className="text-red-400 font-medium"> {critical} critical incidents</span> are currently pending. 
              Operations team has successfully closed {resolved} tickets in this cycle.
            </p>
          </div>
        </div>

        {/* Digital Narrative */}
        <div className="flex gap-3 pt-2 border-t border-slate-900/50">
          <div className="mt-1 min-w-[20px]">
            <TrendingUp className="h-5 w-5 text-blue-500" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Digital Narrative</h4>
            <p className="text-sm text-slate-300 leading-relaxed">
              Online sentiment is trending <strong>{sentiment.label || 'Neutral'}</strong>. 
              Citizens are engaging with the recent updates on infrastructure. 
              Recommendation: Push updates regarding {topCategory} resolution to boost digital perception scores.
            </p>
          </div>
        </div>

      </CardContent>
    </Card>
  );
};

export default ConstituencySummary;
