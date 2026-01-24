import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Upload, Camera, Loader2, CheckCircle, AlertTriangle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PhotoVerification({ grievance, onVerificationComplete, onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [notes, setNotes] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Image size must be less than 10MB');
        return;
      }
      
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }

      setSelectedFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      toast.error('Please select a photo');
      return;
    }

    setUploading(true);
    setResult(null);

    try {
      const token = localStorage.getItem('token');
      
      // Convert to base64
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64String = reader.result.split(',')[1];
        
        try {
          const response = await axios.post(
            `${BACKEND_URL}/api/verification/verify-resolution`,
            {
              grievance_id: grievance.id,
              image_base64: base64String,
              notes: notes
            },
            { headers: { Authorization: `Bearer ${token}` } }
          );

          setResult(response.data);
          
          if (response.data.verification.is_verified) {
            toast.success(response.data.message);
          } else {
            toast.warning(response.data.message);
          }
          
          // Wait a bit then callback
          setTimeout(() => {
            onVerificationComplete(response.data);
          }, 3000);
          
        } catch (error) {
          console.error('Verification error:', error);
          toast.error('Failed to verify resolution');
        } finally {
          setUploading(false);
        }
      };
      
      reader.readAsDataURL(selectedFile);
      
    } catch (error) {
      console.error('File reading error:', error);
      toast.error('Failed to process image');
      setUploading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className=\"fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-6\"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className=\"executive-card p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto\"
          onClick={(e) => e.stopPropagation()}
        >
          <div className=\"flex items-center justify-between mb-6\">
            <div>
              <h3 className=\"text-2xl font-semibold text-slate-50\">Photo Verification</h3>
              <p className=\"text-slate-400 text-sm mt-1\">Upload resolution photo for AI verification</p>
            </div>
            <button onClick={onClose} className=\"text-slate-400 hover:text-slate-200\">
              <X className=\"h-6 w-6\" />
            </button>
          </div>

          {/* Grievance Info */}
          <div className=\"bg-slate-950 rounded-xl p-4 mb-6 border border-slate-800\">
            <p className=\"text-xs uppercase tracking-wider text-slate-500 mb-2\">Original Issue</p>
            <p className=\"text-slate-300\">{grievance.description}</p>
            <div className=\"flex items-center gap-2 mt-3\">
              <Badge className=\"bg-orange-500/10 text-orange-400\">
                {grievance.issue_type || 'Other'}
              </Badge>
              <Badge className=\"bg-slate-700/50 text-slate-300\">
                Priority: {grievance.ai_priority || 5}/10
              </Badge>
            </div>
          </div>

          {!result ? (
            <>
              {/* File Upload */}
              <div className=\"mb-6\">
                <label className=\"block text-sm font-medium text-slate-300 mb-3\">
                  Resolution Photo (After)
                </label>
                
                {preview ? (
                  <div className=\"relative\">
                    <img 
                      src={preview} 
                      alt=\"Preview\" 
                      className=\"w-full rounded-xl border-2 border-slate-800 max-h-96 object-contain\"
                    />
                    <button
                      onClick={() => {
                        setSelectedFile(null);
                        setPreview(null);
                      }}
                      className=\"absolute top-2 right-2 bg-rose-500 text-white p-2 rounded-full hover:bg-rose-600\"
                    >
                      <X className=\"h-4 w-4\" />
                    </button>
                  </div>
                ) : (
                  <label className=\"border-2 border-dashed border-slate-700 rounded-xl p-12 flex flex-col items-center justify-center cursor-pointer hover:border-orange-500 transition-colors\">
                    <Camera className=\"h-12 w-12 text-slate-500 mb-4\" />
                    <p className=\"text-slate-400 mb-2\">Click to upload resolution photo</p>
                    <p className=\"text-xs text-slate-500\">JPEG, PNG up to 10MB</p>
                    <input
                      type=\"file\"
                      accept=\"image/*\"
                      onChange={handleFileSelect}
                      className=\"hidden\"
                    />
                  </label>
                )}
              </div>

              {/* Notes */}
              <div className=\"mb-6\">
                <label className=\"block text-sm font-medium text-slate-300 mb-2\">
                  Resolution Notes (Optional)
                </label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className=\"bg-slate-950 border-slate-800 focus:border-orange-500 rounded-xl text-slate-200 min-h-[80px]\"
                  placeholder=\"Describe what was done to resolve the issue...\"
                />
              </div>

              {/* Actions */}
              <div className=\"flex gap-4\">
                <Button
                  onClick={handleSubmit}
                  disabled={!selectedFile || uploading}
                  className=\"flex-1 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full pill-button\"
                >
                  {uploading ? (
                    <>
                      <Loader2 className=\"mr-2 h-4 w-4 animate-spin\" />
                      AI Verifying...
                    </>
                  ) : (
                    <>
                      <Upload className=\"mr-2 h-4 w-4\" />
                      Verify Resolution
                    </>
                  )}
                </Button>
                <Button
                  onClick={onClose}
                  className=\"bg-slate-800 hover:bg-slate-700 text-white rounded-full px-8 pill-button\"
                >
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            /* Verification Result */
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className=\"space-y-6\"
            >
              <div className={`p-6 rounded-2xl border-2 ${ 
                result.verification.is_verified 
                  ? 'bg-emerald-500/10 border-emerald-500/30' 
                  : 'bg-rose-500/10 border-rose-500/30'
              }`}>
                <div className=\"flex items-center gap-3 mb-4\">
                  {result.verification.is_verified ? (
                    <CheckCircle className=\"h-8 w-8 text-emerald-400\" />
                  ) : (
                    <AlertTriangle className=\"h-8 w-8 text-rose-400\" />
                  )}
                  <div>
                    <h4 className=\"text-xl font-semibold text-slate-50\">
                      {result.verification.is_verified ? 'Resolution Verified! ✓' : 'Verification Failed'}
                    </h4>
                    <p className=\"text-sm text-slate-400\">
                      Confidence: {(result.verification.confidence_score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
                
                <div className=\"space-y-3\">
                  <div>
                    <p className=\"text-xs uppercase tracking-wider text-slate-500 mb-1\">AI Analysis</p>
                    <p className=\"text-slate-300\">{result.verification.analysis}</p>
                  </div>
                  
                  {result.verification.changes_observed && (
                    <div>
                      <p className=\"text-xs uppercase tracking-wider text-slate-500 mb-1\">Changes Observed</p>
                      <p className=\"text-slate-300\">{result.verification.changes_observed}</p>
                    </div>
                  )}
                  
                  <div>
                    <p className=\"text-xs uppercase tracking-wider text-slate-500 mb-1\">Recommendation</p>
                    <p className=\"text-slate-300 capitalize\">{result.verification.recommendation.replace('_', ' ')}</p>
                  </div>
                  
                  <div>
                    <p className=\"text-xs uppercase tracking-wider text-slate-500 mb-1\">Status Update</p>
                    <Badge className={
                      result.status === 'RESOLVED' 
                        ? 'bg-emerald-500/10 text-emerald-400' 
                        : 'bg-amber-500/10 text-amber-400'
                    }>
                      {result.status}
                    </Badge>
                    {result.requires_review && (
                      <Badge className=\"ml-2 bg-amber-500/10 text-amber-400\">
                        Requires Review
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <Button
                onClick={() => {
                  onVerificationComplete(result);
                  onClose();
                }}
                className=\"w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-full pill-button\"
              >
                Done
              </Button>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}