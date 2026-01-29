import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Loader2, TrendingUp, Eye, AlertCircle, Instagram, Facebook, Heart, MessageCircle } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${BACKEND_URL}/api/analytics/campaigns`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) throw new Error("Failed to fetch intelligence data.");
      const result = await response.json();
      
      if (result.error) {
         setError(result.details || "Meta API Error");
      } else {
         setData(result);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8 animate-in fade-in duration-500">
      
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-orange-500" />
          Campaign Intelligence
        </h1>
        <p className="text-slate-400 mt-1">
          Real-time impact assessment across platforms.
        </p>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-900 text-red-200 p-4 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5" />
          <p>{error}. Check your Meta API Permissions.</p>
        </div>
      )}

      {!error && data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="bg-slate-900/50 border-slate-800 backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Total Reach</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-white flex items-center gap-2">
                  <Eye className="h-5 w-5 text-blue-500" />
                  {data.summary.total_reach.toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/50 border-slate-800 backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Total Engagement</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-white flex items-center gap-2">
                  <Heart className="h-5 w-5 text-pink-500" />
                  {data.summary.total_engagement.toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/50 border-slate-800 backdrop-blur">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Posts Tracked</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                   <div className="flex items-center gap-2 text-slate-300">
                      <Facebook className="h-4 w-4 text-blue-400" /> {data.summary.platform_breakdown.facebook || 0}
                   </div>
                   <div className="flex items-center gap-2 text-slate-300">
                      <Instagram className="h-4 w-4 text-pink-500" /> {data.summary.platform_breakdown.instagram || 0}
                   </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed List */}
          <div className="space-y-4">
            <h3 className="text-xl font-bold text-white">Recent Broadcasts</h3>
            <div className="space-y-3">
              {data.posts.length === 0 ? (
                <div className="text-center py-10 text-slate-500">No recent campaign data found.</div>
              ) : (
                data.posts.map((post) => (
                  <div key={post.id} className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    
                    {/* Post Content & Platform */}
                    <div className="flex items-start gap-3 flex-1">
                      <div className={`mt-1 p-2 rounded-full ${post.platform === 'facebook' ? 'bg-blue-900/20 text-blue-400' : 'bg-pink-900/20 text-pink-500'}`}>
                          {post.platform === 'facebook' ? <Facebook className="h-5 w-5" /> : <Instagram className="h-5 w-5" />}
                      </div>
                      <div className="space-y-1">
                        <p className="text-white font-medium text-sm md:text-base line-clamp-2">{post.content}</p>
                        <span className="text-xs text-slate-500">{new Date(post.date).toLocaleDateString()} • {new Date(post.date).toLocaleTimeString()}</span>
                      </div>
                    </div>
                    
                    {/* Metrics Columns */}
                    <div className="flex items-center gap-6 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 border-slate-800 pt-3 md:pt-0 mt-2 md:mt-0">
                      
                      {/* Reach */}
                      <div className="text-center min-w-[60px]">
                        <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                          <Eye className="h-3 w-3" />
                          <span className="text-[10px] uppercase">Reach</span>
                        </div>
                        <span className="block text-lg font-bold text-blue-400">{post.reach}</span>
                      </div>

                      <div className="w-px h-8 bg-slate-800 hidden md:block"></div>

                      {/* Likes */}
                      <div className="text-center min-w-[60px]">
                        <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                          <Heart className="h-3 w-3" />
                          <span className="text-[10px] uppercase">Likes</span>
                        </div>
                        <span className="block text-lg font-bold text-pink-400">{post.likes}</span>
                      </div>

                      {/* Comments */}
                      <div className="text-center min-w-[60px]">
                        <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                          <MessageCircle className="h-3 w-3" />
                          <span className="text-[10px] uppercase">Cmts</span>
                        </div>
                        <span className="block text-lg font-bold text-green-400">{post.comments}</span>
                      </div>

                      <a href={post.url} target="_blank" rel="noreferrer" className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400">
                        <TrendingUp className="h-4 w-4" />
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Analytics;
