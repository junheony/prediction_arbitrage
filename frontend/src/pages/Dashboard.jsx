import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'
import BotControl from '../components/BotControl'
import OpportunitiesList from '../components/OpportunitiesList'
import StatsCards from '../components/StatsCards'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [botStatus, setBotStatus] = useState(null)
  const [opportunities, setOpportunities] = useState([])
  const [stats, setStats] = useState({
    opportunitiesFound: 0,
    totalProfit: '0.0',
    status: 'stopped'
  })
  const wsRef = useRef(null)

  useEffect(() => {
    fetchBotStatus()
    fetchOpportunities()
    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    const token = localStorage.getItem('token')
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws?token=${token}`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      handleWebSocketMessage(message)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      // Reconnect after 5 seconds
      setTimeout(() => {
        if (wsRef.current === ws) {
          connectWebSocket()
        }
      }, 5000)
    }

    wsRef.current = ws
  }

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'connected':
        console.log('Connected:', message.data.message)
        break
      case 'status':
        setBotStatus(message.data)
        setStats(prev => ({
          ...prev,
          status: message.data.status,
          opportunitiesFound: message.data.opportunities_found || prev.opportunitiesFound,
          totalProfit: message.data.total_profit || prev.totalProfit
        }))
        break
      case 'opportunity':
        const newOpp = message.data
        setOpportunities(prev => [newOpp, ...prev].slice(0, 50))
        setStats(prev => ({
          ...prev,
          opportunitiesFound: prev.opportunitiesFound + 1
        }))
        break
      case 'error':
        console.error('Bot error:', message.data.message)
        break
    }
  }

  const fetchBotStatus = async () => {
    try {
      const response = await axios.get('/api/bot/status')
      setBotStatus(response.data)
      setStats({
        opportunitiesFound: response.data.opportunities_found || 0,
        totalProfit: response.data.total_profit || '0.0',
        status: response.data.status
      })
    } catch (error) {
      console.error('Failed to fetch bot status:', error)
    }
  }

  const fetchOpportunities = async () => {
    try {
      const response = await axios.get('/api/bot/opportunities?limit=50')
      setOpportunities(response.data)
    } catch (error) {
      console.error('Failed to fetch opportunities:', error)
    }
  }

  const handleBotStart = async (config) => {
    try {
      await axios.post('/api/bot/start', { config })
      await fetchBotStatus()
    } catch (error) {
      console.error('Failed to start bot:', error)
      throw error
    }
  }

  const handleBotStop = async () => {
    try {
      await axios.post('/api/bot/stop')
      await fetchBotStatus()
    } catch (error) {
      console.error('Failed to stop bot:', error)
      throw error
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                Prediction Arbitrage Bot
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Welcome, {user?.username}
              </span>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-md transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <StatsCards stats={stats} />

        {/* Bot Control */}
        <div className="mt-8">
          <BotControl
            botStatus={botStatus}
            onStart={handleBotStart}
            onStop={handleBotStop}
          />
        </div>

        {/* Opportunities List */}
        <div className="mt-8">
          <OpportunitiesList
            opportunities={opportunities}
            onRefresh={fetchOpportunities}
          />
        </div>
      </div>
    </div>
  )
}
