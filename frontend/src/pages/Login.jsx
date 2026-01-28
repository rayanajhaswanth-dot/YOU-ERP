import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${BACKEND_URL}/api/auth/login`, {
        email,
        password
      });

      // CTO UPDATE: Store role and user_id in localStorage for RBAC
      localStorage.setItem('user_role', response.data.role);
      localStorage.setItem('user_id', response.data.user_id);

      onLogin(response.data.access_token, response.data.user);
      toast.success(`Welcome back! Logged in as ${response.data.role.toUpperCase()}`);
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{
      backgroundImage: 'url(https://images.unsplash.com/photo-1706545604042-399792bd8a04)',
      backgroundSize: 'cover',
      backgroundPosition: 'center'
    }}>
      <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm"></div>
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="executive-card p-10 glass-effect">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-orange-500 mb-2 tracking-tight" style={{ fontFamily: 'Manrope' }}>
              YOU
            </h1>
            <p className="text-slate-400 text-sm uppercase tracking-wider" style={{ fontFamily: 'JetBrains Mono' }}>
              Governance ERP
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Email
              </label>
              <Input
                type="email"
                data-testid="login-email-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-slate-950 border-slate-800 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 rounded-xl h-12 text-slate-200"
                placeholder="legislator@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
              <Input
                type="password"
                data-testid="login-password-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-slate-950 border-slate-800 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 rounded-xl h-12 text-slate-200"
                placeholder="••••••••"
                required
              />
            </div>

            <Button
              type="submit"
              data-testid="login-submit-button"
              disabled={loading}
              className="w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full h-12 shadow-lg shadow-orange-500/20 pill-button"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-500">
            <p>Demo credentials:</p>
            <p className="text-slate-400 mt-1">politician@demo.com / password123</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}