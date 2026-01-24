import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Send, Loader2, CheckCircle, Clock, Sparkles } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function SendNews({ user }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [content, setContent] = useState('');
  const [polishing, setPolishing] = useState(false);
  const [polishedVersions, setPolishedVersions] = useState(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/posts/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPosts(response.data);
    } catch (error) {
      console.error('Error fetching posts:', error);
      toast.error('Failed to load posts');
    } finally {
      setLoading(false);
    }
  };

  const handlePolish = async () => {
    if (!content.trim()) {
      toast.error('Please enter some content first');
      return;
    }

    setPolishing(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${BACKEND_URL}/api/ai/polish-post`,
        { prompt: content },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setPolishedVersions(response.data.polished_versions);
      toast.success('AI polished your post!');
    } catch (error) {
      console.error('Error polishing post:', error);
      toast.error('Failed to polish post');
    } finally {
      setPolishing(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (selectedPlatforms.length === 0) {
      toast.error('Please select at least one platform');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${BACKEND_URL}/api/posts/`,
        {
          content,
          platforms: selectedPlatforms
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success('Post created successfully');
      setShowForm(false);
      setContent('');
      setSelectedPlatforms([]);
      setPolishedVersions(null);
      fetchPosts();
    } catch (error) {
      console.error('Error creating post:', error);
      toast.error('Failed to create post');
    }
  };

  const approvePost = async (postId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${BACKEND_URL}/api/posts/${postId}/approve`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Post approved!');
      fetchPosts();
    } catch (error) {
      console.error('Error approving post:', error);
      toast.error('Failed to approve post');
    }
  };

  const platforms = [
    { id: 'whatsapp', name: 'WhatsApp', color: 'text-emerald-400' },
    { id: 'twitter', name: 'Twitter/X', color: 'text-sky-400' },
    { id: 'instagram', name: 'Instagram', color: 'text-pink-400' },
    { id: 'facebook', name: 'Facebook', color: 'text-blue-400' }
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft':
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
      case 'approved':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'published':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
      data-testid="send-news-page"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-5xl font-bold text-slate-50 tracking-tight mb-2" style={{ fontFamily: 'Manrope' }}>
            Send News
          </h1>
          <p className="text-slate-400 text-lg">Broadcast center for multi-platform posts</p>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          data-testid="create-post-button"
          className="bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full px-8 py-3 pill-button"
        >
          <Send className="h-4 w-4 mr-2" />
          Create Post
        </Button>
      </div>

      {showForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="executive-card p-8"
          data-testid="post-form"
        >
          <h3 className="text-2xl font-semibold text-slate-50 mb-6">Create Multi-Platform Post</h3>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Post Content</label>
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                data-testid="post-content-textarea"
                className="bg-slate-950 border-slate-800 focus:border-orange-500 rounded-xl text-slate-200 min-h-[150px]"
                placeholder="Write your message..."
                required
              />
            </div>

            <Button
              type="button"
              onClick={handlePolish}
              disabled={polishing}
              data-testid="polish-button"
              className="bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 rounded-full px-6 pill-button"
            >
              {polishing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  AI Polishing...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Polish with AI
                </>
              )}
            </Button>

            {polishedVersions && (
              <div className="bg-slate-950 rounded-2xl p-6 border border-purple-500/20">
                <p className="text-sm uppercase tracking-wider text-purple-400 mb-3">AI-Polished Versions</p>
                <div className="text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {polishedVersions}
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">Select Platforms</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {platforms.map((platform) => (
                  <button
                    key={platform.id}
                    type="button"
                    onClick={() => {
                      if (selectedPlatforms.includes(platform.id)) {
                        setSelectedPlatforms(selectedPlatforms.filter((p) => p !== platform.id));
                      } else {
                        setSelectedPlatforms([...selectedPlatforms, platform.id]);
                      }
                    }}
                    data-testid={`platform-${platform.id}`}
                    className={`p-4 rounded-2xl border-2 transition-all ${
                      selectedPlatforms.includes(platform.id)
                        ? 'border-orange-500 bg-orange-500/10'
                        : 'border-slate-800 bg-slate-950 hover:border-slate-700'
                    }`}
                  >
                    <span className={`font-medium ${platform.color}`}>{platform.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-4">
              <Button
                type="submit"
                data-testid="submit-post-button"
                className="bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full px-8 pill-button"
              >
                Create Post
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setContent('');
                  setSelectedPlatforms([]);
                  setPolishedVersions(null);
                }}
                className="bg-slate-800 hover:bg-slate-700 text-white rounded-full px-8 pill-button"
              >
                Cancel
              </Button>
            </div>
          </form>
        </motion.div>
      )}

      <div className="executive-card p-8" data-testid="posts-list">
        <h3 className="text-2xl font-semibold text-slate-50 mb-6">Recent Posts</h3>
        <div className="space-y-4">
          {posts.length === 0 ? (
            <p className="text-slate-400 text-center py-8">No posts created yet</p>
          ) : (
            posts.map((post) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                data-testid={`post-${post.id}`}
                className="bg-slate-950 rounded-2xl p-6 border border-slate-800 hover:border-orange-500/30 transition-colors"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <Badge className={getStatusColor(post.status)}>
                        {post.status}
                      </Badge>
                      {post.platforms && post.platforms.map((platform) => (
                        <Badge key={platform} variant="outline" className="text-slate-400 border-slate-700">
                          {platform}
                        </Badge>
                      ))}
                    </div>
                    <p className="text-slate-300">{post.content}</p>
                  </div>
                </div>
                {user?.role === 'politician' && post.status === 'draft' && (
                  <Button
                    onClick={() => approvePost(post.id)}
                    data-testid={`approve-post-${post.id}`}
                    size="sm"
                    className="bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 rounded-full pill-button"
                  >
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Approve
                  </Button>
                )}
              </motion.div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}