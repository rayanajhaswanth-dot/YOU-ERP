import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { Home, Users, Send, Heart, LogOut } from 'lucide-react';
import { Button } from './ui/button';
import SystemTicker from './SystemTicker';

export default function Layout({ user, onLogout }) {
  const navItems = [
    { path: '/', icon: Home, label: 'Briefing Room' },
    { path: '/help-people', icon: Users, label: 'Help People' },
    { path: '/send-news', icon: Send, label: 'Send News' },
    { path: '/happiness-report', icon: Heart, label: 'Happiness Report' }
  ];

  return (
    <div className="min-h-screen bg-slate-900" data-testid="main-layout">
      <div className="flex">
        <aside className="w-72 min-h-screen bg-slate-950 border-r border-slate-800 p-6 fixed left-0 top-0">
          <div className="mb-10">
            <h1 className="text-3xl font-bold text-orange-500 tracking-tight" style={{ fontFamily: 'Manrope' }}>
              YOU
            </h1>
            <p className="text-slate-500 text-xs uppercase tracking-wider mt-1" style={{ fontFamily: 'JetBrains Mono' }}>
              Governance ERP
            </p>
          </div>

          <nav className="space-y-2" data-testid="navigation-menu">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-full transition-colors ${
                    isActive
                      ? 'bg-orange-500 text-white'
                      : 'text-slate-400 hover:text-orange-400 hover:bg-orange-500/10'
                  }`
                }
              >
                <item.icon className="h-5 w-5" />
                <span className="font-medium">{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="absolute bottom-6 left-6 right-6">
            <div className="executive-card p-4 mb-4">
              <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">Logged in as</p>
              <p className="font-semibold text-slate-200">{user?.full_name}</p>
              <p className="text-xs text-slate-400 mt-1 capitalize">{user?.role}</p>
            </div>
            <Button
              onClick={onLogout}
              data-testid="logout-button"
              className="w-full bg-slate-800 hover:bg-slate-700 text-white rounded-full pill-button"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </aside>

        <main className="ml-72 flex-1 pb-12">
          <div className="p-8">
            <Outlet />
          </div>
        </main>
      </div>

      <SystemTicker />
    </div>
  );
}