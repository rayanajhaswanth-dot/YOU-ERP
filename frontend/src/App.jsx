import React from 'react';
import { LayoutGrid, MessageSquareWarning, Megaphone, BarChart3, Settings, LogOut } from 'lucide-react';
import BroadcastWidget from './components/BroadcastWidget';
import SentimentDashboard from './components/SentimentDashboard';
import GrievanceFeed from './components/GrievanceFeed';
import KPIGrid from './components/KPIGrid';

const SidebarItem = ({ icon: Icon, label, active }) => (
  <div className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
    active ? 'bg-[#111827] text-[#FF9933] border-l-4 border-[#FF9933]' : 'text-gray-400 hover:bg-[#111827] hover:text-gray-200'
  }`}>
    <Icon size={20} />
    <span className="font-medium text-sm">{label}</span>
  </div>
);

const App = () => {
  return (
    <div className="flex h-screen bg-[#111827] text-gray-100 font-sans overflow-hidden">
      
      {/* SIDEBAR (Desktop) */}
      <div className="w-64 bg-[#1F2937] border-r border-gray-800 hidden md:flex flex-col flex-shrink-0">
        <div className="p-6">
          <h1 className="text-2xl font-extrabold tracking-wider text-white">
            YOU <span className="text-[#FF9933]">ERP</span>
          </h1>
          <p className="text-xs text-gray-500 mt-1">Governance OS v1.0</p>
        </div>

        <div className="flex-1 px-4 space-y-2 overflow-y-auto">
          <div className="text-xs font-bold text-gray-600 uppercase tracking-widest px-3 mb-2 mt-4">Command</div>
          <SidebarItem icon={LayoutGrid} label="Briefing Room" active />
          <SidebarItem icon={MessageSquareWarning} label="Grievances" />
          <SidebarItem icon={Megaphone} label="Broadcasts" />
          
          <div className="text-xs font-bold text-gray-600 uppercase tracking-widest px-3 mb-2 mt-8">Intel</div>
          <SidebarItem icon={BarChart3} label="Analytics" />
          <SidebarItem icon={Settings} label="Settings" />
        </div>

        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-[#111827] cursor-pointer text-gray-400 hover:text-red-400 transition-colors">
            <LogOut size={18} />
            <span className="text-sm font-medium">Secure Logout</span>
          </div>
        </div>
      </div>

      {/* MAIN FEED */}
      <div className="flex-1 overflow-y-auto relative">
        {/* Mobile Header */}
        <div className="md:hidden bg-[#1F2937] p-4 flex justify-between items-center sticky top-0 z-20 border-b border-gray-800">
           <h1 className="text-xl font-bold text-white">YOU <span className="text-[#FF9933]">ERP</span></h1>
           <LayoutGrid className="text-[#FF9933]" />
        </div>

        <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-8">
          
          {/* Welcome Header */}
          <div className="mb-6">
            <h2 className="text-3xl font-bold text-white">Good Afternoon, Leader.</h2>
            <p className="text-gray-400 mt-1">Here is your daily governance briefing.</p>
          </div>

          {/* 0. KPI LAYER (Metrics) */}
          <section>
            <KPIGrid />
          </section>

          {/* 1. ACTION LAYER (Broadcast) */}
          <section>
            <BroadcastWidget />
          </section>

          {/* 2. INTEL LAYER (Sentiment) */}
          <section>
            <SentimentDashboard />
          </section>

          {/* 3. REALITY LAYER (Grievances) */}
          <section className="pb-12">
            <GrievanceFeed />
          </section>

        </div>
      </div>
    </div>
  );
};

export default App;
