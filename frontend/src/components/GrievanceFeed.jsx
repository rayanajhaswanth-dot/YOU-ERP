import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Loader2, ArrowRight } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function GrievanceFeed() {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGrievances();
  }, []);

  const fetchGrievances = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/dashboard/grievances`);
      if (response.ok) {
        const data = await response.json();
        setGrievances(data);
      }
    } catch (error) {
      console.error('Error fetching grievances:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#1F2937] p-6 rounded-xl" data-testid="grievance-feed-loading">
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-[#FF9933]" />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="grievance-feed">
      <h3 className="text-xl font-bold mb-4 text-gray-200 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-red-500" />
        Operational Reality: Critical Alerts
      </h3>

      {grievances.length === 0 ? (
        <div 
          className="text-green-400 bg-green-900/20 p-4 rounded-lg flex items-center gap-3"
          data-testid="all-clear-message"
        >
          <CheckCircle className="h-5 w-5" />
          <span className="font-medium">All Systems Nominal</span>
        </div>
      ) : (
        <div className="space-y-3">
          {grievances.map((item) => (
            <div
              key={item.id}
              className={`bg-[#1F2937] p-4 rounded-lg border-l-4 flex justify-between items-start ${
                item.priority_level === 'CRITICAL' 
                  ? 'border-red-500' 
                  : 'border-orange-500'
              }`}
              data-testid={`grievance-card-${item.id}`}
            >
              <div className="flex-1 pr-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-white uppercase tracking-wide text-sm">
                    {item.issue_type || 'General'}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                    item.priority_level === 'CRITICAL'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-orange-500/20 text-orange-400'
                  }`}>
                    {item.priority_level}
                  </span>
                </div>
                <p className="text-gray-300 mt-1 line-clamp-2">
                  {item.description || 'No description provided'}
                </p>
                <p className="text-gray-500 text-xs mt-2">
                  {item.village || 'Unknown Location'} • {new Date(item.created_at).toLocaleDateString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric'
                  })}
                </p>
              </div>
              
              <button
                className="border border-[#FF9933] text-[#FF9933] px-4 py-1 rounded hover:bg-[#FF9933] hover:text-black transition text-sm font-medium h-fit self-center flex items-center gap-1 whitespace-nowrap"
                data-testid={`action-btn-${item.id}`}
              >
                Direct Action
                <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
