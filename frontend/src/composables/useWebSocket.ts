import { ref, onUnmounted } from 'vue'

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const messageHandlers = ref<((event: MessageEvent) => void)[]>([])

  // 连接WebSocket
  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/video/`
    
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket连接已建立')
      isConnected.value = true
    }

    ws.value.onclose = () => {
      console.log('WebSocket连接已关闭')
      isConnected.value = false
      // 尝试重新连接
      setTimeout(connect, 3000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket错误:', error)
    }

    ws.value.onmessage = (event) => {
      messageHandlers.value.forEach(handler => handler(event))
    }
  }

  // 发送消息
  const send = (data: string | object) => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      console.error('WebSocket未连接')
      return
    }

    const message = typeof data === 'string' ? data : JSON.stringify(data)
    ws.value.send(message)
  }

  // 添加消息处理器
  const onMessage = (handler: (event: MessageEvent) => void) => {
    messageHandlers.value.push(handler)
  }

  // 移除消息处理器
  const offMessage = (handler: (event: MessageEvent) => void) => {
    const index = messageHandlers.value.indexOf(handler)
    if (index !== -1) {
      messageHandlers.value.splice(index, 1)
    }
  }

  // 组件卸载时清理
  onUnmounted(() => {
    if (ws.value) {
      ws.value.close()
    }
    messageHandlers.value = []
  })

  // 初始化连接
  connect()

  return {
    isConnected,
    send,
    onMessage,
    offMessage
  }
} 