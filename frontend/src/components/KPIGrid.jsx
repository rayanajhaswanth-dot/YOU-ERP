import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Activity, AlertCircle } from "lucide-react";

const KPIGrid = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      
      {/* KPI 1: Overall Sentiment */}
      <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-400">
            Overall Sentiment
          </CardTitle>
          <Activity className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-white">
            {stats.sentimentScore || "Neutral"}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Combined Digital & Ground Score
          </p>
        </CardContent>
      </Card>

      {/* KPI 2: Total Unresolved Issues */}
      <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-400">
            Total Unresolved Issues
          </CardTitle>
          <AlertCircle className="h-4 w-4 text-orange-500" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-white">
            {stats.unresolvedCount || 0}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Pending immediate action
          </p>
        </CardContent>
      </Card>

    </div>
  );
};

export default KPIGrid;
