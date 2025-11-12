import { useState } from 'react'

export default function BotControl({ botStatus, onStart, onStop }) {
  const [loading, setLoading] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [config, setConfig] = useState({
    min_profit_threshold: 0.01,
    max_position_size: 100.0,
    platforms: ['polymarket', 'kalshi', 'opinion'],
    auto_execute: false,
    notification_enabled: true
  })

  const isRunning = botStatus?.status === 'running'

  const handleStart = async () => {
    setLoading(true)
    try {
      await onStart(config)
    } catch (error) {
      alert('Failed to start bot: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    setLoading(true)
    try {
      await onStop()
    } catch (error) {
      alert('Failed to stop bot: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handlePlatformToggle = (platform) => {
    setConfig(prev => ({
      ...prev,
      platforms: prev.platforms.includes(platform)
        ? prev.platforms.filter(p => p !== platform)
        : [...prev.platforms, platform]
    }))
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Bot Control</h2>
        <button
          onClick={() => setShowConfig(!showConfig)}
          className="text-sm text-primary hover:text-secondary transition-colors"
        >
          {showConfig ? 'Hide Config' : 'Show Config'}
        </button>
      </div>

      {/* Configuration Panel */}
      {showConfig && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg space-y-4">
          <h3 className="font-semibold text-gray-700">Configuration</h3>

          {/* Platforms */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Platforms
            </label>
            <div className="space-y-2">
              {['polymarket', 'kalshi', 'opinion'].map(platform => (
                <label key={platform} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.platforms.includes(platform)}
                    onChange={() => handlePlatformToggle(platform)}
                    className="rounded border-gray-300 text-primary focus:ring-primary"
                  />
                  <span className="ml-2 text-sm text-gray-700 capitalize">{platform}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Min Profit Threshold */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Min Profit Threshold: {(config.min_profit_threshold * 100).toFixed(1)}%
            </label>
            <input
              type="range"
              min="0.001"
              max="0.1"
              step="0.001"
              value={config.min_profit_threshold}
              onChange={(e) => setConfig(prev => ({ ...prev, min_profit_threshold: parseFloat(e.target.value) }))}
              className="w-full"
            />
          </div>

          {/* Max Position Size */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Position Size: ${config.max_position_size}
            </label>
            <input
              type="range"
              min="10"
              max="1000"
              step="10"
              value={config.max_position_size}
              onChange={(e) => setConfig(prev => ({ ...prev, max_position_size: parseFloat(e.target.value) }))}
              className="w-full"
            />
          </div>

          {/* Auto Execute */}
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={config.auto_execute}
              onChange={(e) => setConfig(prev => ({ ...prev, auto_execute: e.target.checked }))}
              className="rounded border-gray-300 text-primary focus:ring-primary"
            />
            <span className="ml-2 text-sm text-gray-700">Auto-execute trades (⚠️ Use with caution)</span>
          </label>

          {/* Notifications */}
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={config.notification_enabled}
              onChange={(e) => setConfig(prev => ({ ...prev, notification_enabled: e.target.checked }))}
              className="rounded border-gray-300 text-primary focus:ring-primary"
            />
            <span className="ml-2 text-sm text-gray-700">Enable notifications</span>
          </label>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex space-x-4">
        {!isRunning ? (
          <button
            onClick={handleStart}
            disabled={loading || config.platforms.length === 0}
            className="flex-1 px-6 py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Starting...' : '▶️ Start Bot'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            disabled={loading}
            className="flex-1 px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Stopping...' : '⏹️ Stop Bot'}
          </button>
        )}
      </div>

      {/* Status Message */}
      {botStatus?.started_at && isRunning && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            Bot started at: {new Date(botStatus.started_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  )
}
