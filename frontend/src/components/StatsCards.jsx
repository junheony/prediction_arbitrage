export default function StatsCards({ stats }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800'
      case 'stopped':
        return 'bg-gray-100 text-gray-800'
      case 'error':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return '🟢'
      case 'stopped':
        return '🔴'
      case 'error':
        return '⚠️'
      default:
        return '⚪'
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Status Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Bot Status</p>
            <div className="mt-2 flex items-center space-x-2">
              <span className="text-2xl">{getStatusIcon(stats.status)}</span>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(stats.status)}`}>
                {stats.status.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Opportunities Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Opportunities Found</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {stats.opportunitiesFound}
            </p>
          </div>
          <div className="p-3 bg-blue-100 rounded-full">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
        </div>
      </div>

      {/* Profit Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Total Potential Profit</p>
            <p className="mt-2 text-3xl font-bold text-green-600">
              ${parseFloat(stats.totalProfit).toFixed(2)}
            </p>
          </div>
          <div className="p-3 bg-green-100 rounded-full">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  )
}
