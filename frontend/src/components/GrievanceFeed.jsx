import React, { useState, useEffect } from 'react';
import { AlertTriangle, MapPin, CheckCircle, Share2 } from 'lucide-react';

const GrievanceFeed = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGrievances = async () => {
      try {
        const response = await fetch('/api/dashboard/grievances');
        if (response.ok) {
          const data = await response.json();
          // Safety check to ensure we always have an array
          setGrievances(Array.isArray(data) ? data : []);
        } else {
          setGrievances([]);
        }
      } catch (err) {
        console.error("Feed Error:", err);
        setGrievances([]);
      } finally {
        setLoading(false);
      }
    };

    fetchGrievances();
  }, []);

  const handleAssign = (item) => {
    // PRD Feature B: Deep Link Assignment
    // Generates a pre-filled WhatsApp message for the official
    const message = 
      `🚨 *URGENT TASK ASSIGNMENT*\n\n` +
      `*Issue:* ${item.issue_type || 'General Issue'}\n` +
      `*Location:* ${item.village || 'Constituency'}\n` +
      `*Priority:* ${item.priority_level || 'HIGH'}\n\n` +
      `*Description:* ${item.description}\n\n` +
      `Please resolve this immediately and share proof of completion.`;

    // Opens WhatsApp Web or App with the drafted text
    const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
    window.open(url, '_blank');
  };

  if (loading) return <div className="h-32 bg-[#1F2937] rounded-xl animate-pulse border border-gray-800"></div>;

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
          <AlertTriangle className="text-red-500" size={20} />
          Critical Alerts
        </h2>
        <span className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Real-Time</span>
      </div>

      <div className="space-y-3">
        {grievances.length === 0 ? (
          <div className="bg-[#1F2937] p-6 rounded-xl border border-green-900/30 flex items-center gap-3">
            <CheckCircle className="text-green-500" size={24} />
            <div>
              <h3 className="text-green-400 font-bold">All Systems Nominal</h3>
              <p className="text-sm text-gray-400">No critical issues pending attention.</p>
            </div>
          </div>
        ) : (
          grievances.map((item, index) => {
            const isCritical = item.priority_level === 'CRITICAL';
            return (
              <div 
                key={item.id || index}
                className={`bg-[#1F2937] p-4 rounded-lg border-l-4 flex justify-between items-center transition-all hover:bg-[#2d3748] ${
                  isCritical ? 'border-red-500' : 'border-orange-500'
                }`}
              >
                <div className="flex-1 pr-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      isCritical ? 'bg-red-500/20 text-red-400' : 'bg-orange-500/20 text-orange-400'
                    }`}>
                      {item.priority_level || 'HIGH'}
                    </span>
                    <span className="text-gray-400 text-xs flex items-center gap-1">
                      <MapPin size={10} /> {item.village || 'Unknown Location'}
                    </span>
                  </div>
                  <h4 className="text-white font-bold text-sm md:text-base">
                    {item.issue_type || 'General Issue'}
                  </h4>
                  <p className="text-gray-400 text-xs md:text-sm mt-1 line-clamp-1">
                    {item.description}
                  </p>
                </div>

                <button 
                  onClick={() => handleAssign(item)}
                  className="hidden md:flex items-center gap-1 text-[#FF9933] text-xs font-bold border border-[#FF9933]/30 px-3 py-1.5 rounded hover:bg-[#FF9933] hover:text-black transition-colors"
                >
                  Assign <Share2 size={12} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default GrievanceFeed;
