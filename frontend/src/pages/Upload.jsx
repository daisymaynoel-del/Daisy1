import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload as UploadIcon, Film, Image, Wand2, CheckCircle, X } from 'lucide-react'
import { api } from '../api/client'
import clsx from 'clsx'

const PILLARS = ['transformation', 'education', 'process', 'lifestyle']
const PLATFORMS = ['instagram', 'tiktok']

export default function Upload() {
  const qc = useQueryClient()
  const fileInputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploadedAsset, setUploadedAsset] = useState(null)
  const [generateConfig, setGenerateConfig] = useState({
    platform: 'instagram',
    pillar: '',
    notes: '',
  })

  const uploadMutation = useMutation({
    mutationFn: async (file) => {
      const form = new FormData()
      form.append('file', file)
      form.append('tags', JSON.stringify([]))
      return api.uploadAsset(form)
    },
    onSuccess: (asset) => {
      setUploadedAsset(asset)
      qc.invalidateQueries({ queryKey: ['assets'] })
    },
  })

  const generateMutation = useMutation({
    mutationFn: () => api.generatePost({
      asset_id: uploadedAsset.id,
      platform: generateConfig.platform,
      content_pillar: generateConfig.pillar || undefined,
      custom_notes: generateConfig.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-approval'] })
      qc.invalidateQueries({ queryKey: ['posts'] })
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })

  const handleFile = (file) => {
    if (!file) return
    uploadMutation.mutate(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const aiAnalysis = uploadedAsset?.ai_analysis

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="font-semibold text-charcoal-900">Upload Content</h2>
        <p className="text-sm text-charcoal-400 mt-0.5">Upload a video or image — AI will analyse it and generate an optimised post ready for your approval</p>
      </div>

      {/* Upload Zone */}
      {!uploadedAsset && (
        <div
          className={clsx(
            'border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors',
            dragOver ? 'border-brand-400 bg-brand-50' : 'border-charcoal-200 hover:border-charcoal-300 bg-white'
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/mov,image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {uploadMutation.isPending ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-charcoal-600 font-medium">Uploading & analysing...</p>
            </div>
          ) : (
            <>
              <div className="flex justify-center gap-3 mb-4">
                <Film size={28} className="text-charcoal-300" />
                <Image size={28} className="text-charcoal-300" />
              </div>
              <p className="font-semibold text-charcoal-700 mb-1">Drop your video or image here</p>
              <p className="text-sm text-charcoal-400">MP4, MOV, JPEG, PNG, WEBP · Max {500}MB</p>
              <button className="btn-primary mt-4 text-sm">Choose File</button>
            </>
          )}
        </div>
      )}

      {/* Upload Error */}
      {uploadMutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
          Upload failed: {uploadMutation.error.message}
        </div>
      )}

      {/* Asset Uploaded — AI Analysis */}
      {uploadedAsset && (
        <div className="space-y-4">
          <div className="card bg-green-50 border-green-200">
            <div className="flex items-center gap-3">
              <CheckCircle size={18} className="text-green-600 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-green-800">Upload complete!</p>
                <p className="text-sm text-green-600 truncate">{uploadedAsset.original_filename}</p>
              </div>
              <button onClick={() => setUploadedAsset(null)} className="text-green-500 hover:text-green-700">
                <X size={16} />
              </button>
            </div>
          </div>

          {/* AI Analysis */}
          {aiAnalysis && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Wand2 size={15} className="text-brand-500" />
                <h3 className="font-semibold text-charcoal-900 text-sm">AI Analysis</h3>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-charcoal-400 text-xs font-medium">Brand Alignment</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-charcoal-100 rounded-full h-2">
                      <div
                        className="bg-brand-500 h-2 rounded-full"
                        style={{ width: `${aiAnalysis.brand_alignment_score || 70}%` }}
                      />
                    </div>
                    <span className="font-semibold text-charcoal-700">{aiAnalysis.brand_alignment_score || 70}%</span>
                  </div>
                </div>
                <div>
                  <p className="text-charcoal-400 text-xs font-medium">Suggested Pillar</p>
                  <p className="font-semibold text-charcoal-800 mt-1 capitalize">{aiAnalysis.suggested_pillar || 'transformation'}</p>
                </div>
              </div>
              {aiAnalysis.hook_ideas?.length > 0 && (
                <div className="mt-3">
                  <p className="text-charcoal-400 text-xs font-medium mb-1.5">Hook Ideas</p>
                  <div className="space-y-1">
                    {aiAnalysis.hook_ideas.map((h, i) => (
                      <p key={i} className="text-sm text-charcoal-700 bg-charcoal-50 rounded-lg px-3 py-1.5">"{h}"</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Generate Post Config */}
          <div className="card">
            <h3 className="font-semibold text-charcoal-900 mb-4">Generate Post</h3>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-charcoal-700 mb-1.5 block">Platform</label>
                <div className="flex gap-2">
                  {PLATFORMS.map(p => (
                    <button
                      key={p}
                      onClick={() => setGenerateConfig(c => ({ ...c, platform: p }))}
                      className={clsx(
                        'px-4 py-2 rounded-xl text-sm font-medium transition-colors',
                        generateConfig.platform === p ? 'bg-charcoal-900 text-white' : 'bg-charcoal-100 text-charcoal-600 hover:bg-charcoal-200'
                      )}
                    >
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-charcoal-700 mb-1.5 block">Content Pillar (optional — AI will choose)</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setGenerateConfig(c => ({ ...c, pillar: '' }))}
                    className={clsx('px-3 py-1.5 rounded-xl text-sm font-medium transition-colors', !generateConfig.pillar ? 'bg-charcoal-900 text-white' : 'bg-charcoal-100 text-charcoal-600 hover:bg-charcoal-200')}
                  >
                    Auto
                  </button>
                  {PILLARS.map(p => (
                    <button
                      key={p}
                      onClick={() => setGenerateConfig(c => ({ ...c, pillar: p }))}
                      className={clsx('px-3 py-1.5 rounded-xl text-sm font-medium transition-colors capitalize', generateConfig.pillar === p ? 'bg-brand-500 text-white' : 'bg-charcoal-100 text-charcoal-600 hover:bg-charcoal-200')}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-charcoal-700 mb-1.5 block">Notes for AI (optional)</label>
                <textarea
                  placeholder="e.g. 'This is a balayage transformation — make sure patch test notice is included'"
                  className="w-full text-sm border border-charcoal-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-400 resize-none"
                  rows={2}
                  value={generateConfig.notes}
                  onChange={(e) => setGenerateConfig(c => ({ ...c, notes: e.target.value }))}
                />
              </div>

              <button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Wand2 size={16} />
                {generateMutation.isPending ? 'Generating...' : 'Generate Post with AI'}
              </button>

              {generateMutation.isSuccess && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-sm text-green-700 text-center">
                  Post generated! Check the <a href="/approval" className="font-semibold underline">Approval Queue</a> to review it.
                </div>
              )}
              {generateMutation.isError && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
                  Generation failed: {generateMutation.error.message}
                </div>
              )}
            </div>
          </div>

          <button onClick={() => setUploadedAsset(null)} className="btn-ghost text-sm w-full">
            Upload another file
          </button>
        </div>
      )}
    </div>
  )
}
