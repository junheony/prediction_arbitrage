import { useState } from 'react'

export default function OpportunitiesList({ opportunities, onRefresh }) {
  const [filter, setFilter] = useState('all') // all, unexecuted, executed

  const filteredOpportunities = opportunities.filter(opp => {
    if (filter === 'unexecuted') return !opp.executed
    if (filter === 'executed') return opp.executed
    return true
  })

  const getProfitColor = (profit) => {
    const value = parseFloat(profit)
    if (value >= 3) return 'text-green-600 font-bold'
    if (value >= 1.5) return 'text-green-500'
    return 'text-green-400'
  }

  const getPlatformBadge = (platform) => {
    const colors = {
      polymarket: 'bg-purple-100 text-purple-800',
      kalshi: 'bg-blue-100 text-blue-800',
      opinion: 'bg-orange-100 text-orange-800'
    }
    return colors[platform.toLowerCase()] || 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Arbitrage Opportunities</h2>
        <div className="flex items-center space-x-4">
          {/* Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-primary focus:border-primary"
          >
            <option value="all">All ({opportunities.length})</option>
            <option value="unexecuted">Unexecuted ({opportunities.filter(o => !o.executed).length})</option>
            <option value="executed">Executed ({opportunities.filter(o => o.executed).length})</option>
          </select>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            className="px-4 py-2 bg-primary hover:bg-secondary text-white rounded-md transition-colors text-sm"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {filteredOpportunities.length === 0 ? (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="mt-2 text-sm text-gray-600">No opportunities found yet</p>
          <p className="text-xs text-gray-500 mt-1">Start the bot to begin monitoring markets</p>
        </div>
      ) : (
        <div className="space-y-4 max-h-[600px] overflow-y-auto">
          {filteredOpportunities.map((opp) => (
            <div
              key={opp.id}
              className={`p-4 rounded-lg border-2 transition-all ${
                opp.executed
                  ? 'bg-gray-50 border-gray-200 opacity-60'
                  : 'bg-white border-green-200 hover:border-green-300 hover:shadow-md'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${getPlatformBadge(opp.platform_a)}`}>
                      {opp.platform_a.toUpperCase()}
                    </span>
                    <span className="text-gray-400">↔️</span>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${getPlatformBadge(opp.platform_b)}`}>
                      {opp.platform_b.toUpperCase()}
                    </span>
                    {opp.executed && (
                      <span className="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">
                        ✓ EXECUTED
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    <p className="text-sm font-medium text-gray-900">
                      {opp.market_a}
                    </p>
                    <p className="text-sm text-gray-600">
                      vs. {opp.market_b}
                    </p>
                  </div>

                  <p className="mt-2 text-xs text-gray-500">
                    {opp.suggested_action}
                  </p>

                  <p className="mt-1 text-xs text-gray-400">
                    {new Date(opp.timestamp).toLocaleString()}
                  </p>
                </div>

                <div className="ml-4 text-right">
                  <div className={`text-2xl font-bold ${getProfitColor(opp.profit_percentage)}`}>
                    +{opp.profit_percentage}%
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Profit</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
