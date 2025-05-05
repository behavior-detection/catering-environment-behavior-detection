class WebSocketService {
  constructor() {
    this.connections = {}
    this.messageCallbacks = {}
    this.connectionStatusCallbacks = {}
    this.errorCallbacks = {}
    this.baseUrl = process.env.VUE_APP_WS_BASE_URL || 'ws://localhost:8000'
  }

  /**
   * Connect to a WebSocket endpoint
   * @param {string} name - Name to identify this connection
   * @param {string} path - WebSocket path (without baseUrl)
   * @param {boolean} reconnect - Whether to auto-reconnect on disconnection
   * @return {WebSocket} The WebSocket instance
   */
  connect(name, path, reconnect = true) {
    // Close existing connection if any
    this.close(name)

    const url = `${this.baseUrl}${path}`
    const ws = new WebSocket(url)

    // Store connection
    this.connections[name] = {
      socket: ws,
      url,
      reconnect,
      reconnectAttempts: 0,
      maxReconnectAttempts: 5,
      reconnectTimeout: null
    }

    // Set up event handlers
    ws.onopen = (event) => {
      console.log(`WebSocket connected: ${name}`)
      this.connections[name].reconnectAttempts = 0
      this._notifyConnectionStatus(name, true)
    }

    ws.onclose = (event) => {
      console.log(`WebSocket closed: ${name}`, event)
      this._notifyConnectionStatus(name, false)

      // Auto-reconnect if enabled
      if (reconnect && !event.wasClean && this.connections[name]) {
        this._scheduleReconnect(name)
      }
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error: ${name}`, error)
      this._notifyError(name, error)
    }

    ws.onmessage = (event) => {
      this._processMessage(name, event)
    }

    return ws
  }

  /**
   * Send data through WebSocket
   * @param {string} name - Connection name
   * @param {object|string} data - Data to send
   * @return {boolean} Success status
   */
  send(name, data) {
    const connection = this.connections[name]
    if (!connection || !connection.socket || connection.socket.readyState !== WebSocket.OPEN) {
      console.error(`Cannot send: WebSocket ${name} not connected`)
      return false
    }

    try {
      // Convert object to JSON if needed
      const message = typeof data === 'object' ? JSON.stringify(data) : data
      connection.socket.send(message)
      return true
    } catch (error) {
      console.error(`Error sending to WebSocket ${name}:`, error)
      return false
    }
  }

  /**
   * Register a callback for incoming messages
   * @param {string} name - Connection name
   * @param {function} callback - Callback function(data)
   */
  onMessage(name, callback) {
    if (!this.messageCallbacks[name]) {
      this.messageCallbacks[name] = []
    }
    this.messageCallbacks[name].push(callback)
  }

  /**
   * Register a callback for connection status changes
   * @param {string} name - Connection name
   * @param {function} callback - Callback function(isConnected)
   */
  onConnectionStatus(name, callback) {
    if (!this.connectionStatusCallbacks[name]) {
      this.connectionStatusCallbacks[name] = []
    }
    this.connectionStatusCallbacks[name].push(callback)
  }

  /**
   * Register a callback for connection errors
   * @param {string} name - Connection name
   * @param {function} callback - Callback function(error)
   */
  onError(name, callback) {
    if (!this.errorCallbacks[name]) {
      this.errorCallbacks[name] = []
    }
    this.errorCallbacks[name].push(callback)
  }

  /**
   * Close a WebSocket connection
   * @param {string} name - Connection name
   */
  close(name) {
    if (this.connections[name]) {
      const connection = this.connections[name]

      // Clear any pending reconnection
      if (connection.reconnectTimeout) {
        clearTimeout(connection.reconnectTimeout)
      }

      // Close socket if it exists and is not already closed
      if (connection.socket && connection.socket.readyState !== WebSocket.CLOSED) {
        connection.socket.close()
      }

      // Remove connection
      delete this.connections[name]
      console.log(`WebSocket ${name} closed and removed`)
    }
  }

  /**
   * Check if a connection is active
   * @param {string} name - Connection name
   * @return {boolean} Whether connection is active
   */
  isConnected(name) {
    return this.connections[name] &&
      this.connections[name].socket &&
      this.connections[name].socket.readyState === WebSocket.OPEN
  }

  /**
   * Close all connections
   */
  closeAll() {
    for (const name in this.connections) {
      this.close(name)
    }
  }

  /**
   * Process incoming WebSocket message
   * @private
   */
  _processMessage(name, event) {
    let data = event.data

    // Try to parse JSON
    try {
      data = JSON.parse(event.data)
    } catch (e) {
      // Keep as string if not valid JSON
    }

    // Notify callbacks
    if (this.messageCallbacks[name]) {
      this.messageCallbacks[name].forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in WebSocket message callback for ${name}:`, error)
        }
      })
    }
  }

  /**
   * Notify connection status callbacks
   * @private
   */
  _notifyConnectionStatus(name, isConnected) {
    if (this.connectionStatusCallbacks[name]) {
      this.connectionStatusCallbacks[name].forEach(callback => {
        try {
          callback(isConnected)
        } catch (error) {
          console.error(`Error in WebSocket connection status callback for ${name}:`, error)
        }
      })
    }
  }

  /**
   * Notify error callbacks
   * @private
   */
  _notifyError(name, error) {
    if (this.errorCallbacks[name]) {
      this.errorCallbacks[name].forEach(callback => {
        try {
          callback(error)
        } catch (err) {
          console.error(`Error in WebSocket error callback for ${name}:`, err)
        }
      })
    }
  }

  /**
   * Schedule a reconnection attempt
   * @private
   */
  _scheduleReconnect(name) {
    const connection = this.connections[name]
    if (!connection) return

    connection.reconnectAttempts++

    if (connection.reconnectAttempts <= connection.maxReconnectAttempts) {
      // Exponential backoff
      const delay = Math.min(1000 * Math.pow(2, connection.reconnectAttempts - 1), 30000)

      console.log(`Scheduling reconnect for ${name} in ${delay}ms (attempt ${connection.reconnectAttempts})`)

      connection.reconnectTimeout = setTimeout(() => {
        console.log(`Attempting to reconnect ${name}...`)
        this.connect(name, connection.url, connection.reconnect)
      }, delay)
    } else {
      console.error(`Max reconnect attempts reached for ${name}`)
    }
  }
}

// Create and export a singleton instance
const websocketService = new WebSocketService()
export default websocketService
