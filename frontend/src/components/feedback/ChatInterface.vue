// ChatInterface.vue

<template>
    <div class="chat-interface">
    <div class="chat-header">
      <h3>AI 智能分析助手</h3>
      <div class="header-actions">
        <div class="status-indicator" :class="systemStatus.overall">
          <i :class="statusIcon"></i>
          <span>{{ statusText }}</span>
        </div>
        <button @click="clearConversation" class="clear-btn" :disabled="messages.length === 0">
          <i class="fas fa-trash"></i>
          清空对话
        </button>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer" :class="{ 'is-empty': messages.length === 0 }">
      <div v-if="messages.length === 0" class="welcome-message">
        <div class="welcome-content">
          <i class="fas fa-robot welcome-icon"></i>
          <h4>欢迎使用AI智能分析助手</h4>
          <p>我可以分析违规监控数据，生成系统使用指南，回答你的的问题</p>
          <div class="capabilities">
            <div class="capability-item">
              <i class="fas fa-chart-bar"></i>
              <span>数据分析与统计</span>
            </div>
            <div class="capability-item">
              <i class="fas fa-brain"></i>
              <span>智能问答系统</span>
            </div>
            <div class="capability-item">
              <i class="fas fa-shield-alt"></i>
              <span>安全风险评估</span>
            </div>
          </div>
        </div>
      </div>

      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message-wrapper', message.type === 'user' ? 'user-wrapper' : 'ai-wrapper']"
      >
        <div class="message-content">
          <div class="message-avatar">
            <i :class="message.type === 'user' ? 'fas fa-user' : 'fas fa-robot'"></i>
          </div>
          <div class="message-bubble">
            <div class="message-text" v-html="formatMessageText(message.content)"></div>
            <div class="message-meta">
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              <div v-if="message.metadata && message.metadata.routing_info" class="routing-info">
                <span v-if="message.metadata.processing_time" class="processing-time">
                  {{ message.metadata.processing_time }}s
                </span>
                <span v-if="message.metadata.routing_info.confidence" class="confidence-score" :title="`路由置信度: ${message.metadata.routing_info.confidence.toFixed(2)}`">
                  {{ (message.metadata.routing_info.confidence * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="message-wrapper ai-wrapper">
        <div class="message-content">
          <div class="message-avatar">
            <i class="fas fa-robot"></i>
          </div>
          <div class="message-bubble loading-bubble">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
              <span class="typing-text">{{ loadingText }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="example-queries-section">
      <div class="example-header">
        <span class="example-title">💡 常用查询示例</span>
        <div class="example-categories">
          <button
            v-for="category in exampleCategories"
            :key="category.key"
            @click="currentCategory = category.key"
            :class="['category-btn', { active: currentCategory === category.key }]"
          >
            {{ category.name }}
          </button>
        </div>
      </div>
      <div class="example-queries">
        <button
          v-for="example in getCurrentExamples()"
          :key="example.query"
          @click="sendMessage(example.query)"
          :class="['example-btn', example.complexity]"
        >
          <div class="example-content">
            <span class="example-text">{{ example.query }}</span>
            <span class="complexity-badge" :title="example.description">
              {{ example.badge }}
            </span>
          </div>
        </button>
      </div>
    </div>

    <div class="time-selector-section">
      <div class="time-selector-header">
        <span class="time-selector-title">📅 指定时间范围</span>
        <button v-if="isDateSelected" @click="clearTimeRange" class="clear-time-btn">
          清除选择
        </button>
      </div>
      <div class="time-selector-inputs">
        <el-date-picker
          v-model="startDate"
          type="date"
          placeholder="选择开始日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :clearable="false"
        />
        <el-time-picker
          v-model="startTime"
          placeholder="选择开始时间"
          format="HH:mm:ss"
          value-format="HH:mm:ss"
          :clearable="false"
        />
        <span class="time-separator">至</span>
        <el-date-picker
          v-model="endDate"
          type="date"
          placeholder="选择结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :clearable="false"
        />
        <el-time-picker
          v-model="endTime"
          placeholder="选择结束时间"
          format="HH:mm:ss"
          value-format="HH:mm:ss"
          :clearable="false"
        />
      </div>
    </div>

    <div class="chat-input">
      <div class="input-container">
        <textarea
          v-model="inputMessage"
          @keydown="handleKeyDown"
          :placeholder="inputPlaceholder" class="message-input"
          rows="1"
          ref="messageInput"
          :disabled="isInputDisabled" ></textarea>
        <button
          @click="sendUserMessage"
          :disabled="!inputMessage.trim() || isInputDisabled" class="send-button"
        >
          <i class="fas fa-paper-plane"></i>
        </button>
      </div>
    </div>

    <MessageToast
      v-if="message.show"
      :type="message.type"
      :text="message.text"
    />
    </div>
</template>

<script>
import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import MessageToast from '@/components/common/MessageToast.vue'
import { marked } from 'marked';

export default {
  name: 'ChatInterface',
  components: {
    MessageToast
  },
  data() {
    return {
      messages: [],
      inputMessage: '',
      isLoading: false,
      conversationId: null,
      currentCategory: 'basic',
      loadingText: 'AI助手正在分析中...',
      startDate: null,
      startTime: null,
      endDate: null,
      endTime: null,

      // 系统状态
        systemStatus: {
        overall: 'checking',
        janusProStatus: 'checking', // e.g., 'checking', 'LOADING', 'LOADED', 'FAILED'
        basicAvailable: true
      },

      statusInterval: null,

      // 分类示例查询
      exampleCategories: [
        { key: 'basic', name: '基础查询' },
        { key: 'complex', name: '深度分析' },
        { key: 'system', name: '系统功能' },
        { key: 'other', name: '其他问题' }
      ],

      exampleQueries: {
        basic: [
          {
            query: '违规情况如何',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI处理结构化查询',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '哪个摄像头违规最多？',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI处理排序查询',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '哪种违规类型的违规次数最多',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI处理时间筛选',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: 'cam_11摄像头口罩违规次数',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI处理筛选查询',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '有什么摄像头违规了',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '有什么违规类型违规次数大于0',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
        ],

        system: [
          {
            query: '这个系统有什么功能？',
            complexity: 'complex',
            badge: 'Pro',
            description: 'Deepseek处理系统介绍',
            expectedProcessor: 'janus_pro'
          },
          {
            query: '如何使用这个厨房违规情况实时监控系统？',
            complexity: 'complex',
            badge: 'Pro',
            description: 'Deepseek处理使用指南',
            expectedProcessor: 'janus_pro'
          },
          {
            query: '系统支持哪些违规类型检测？',
            complexity: 'complex',
            badge: 'Pro',
            description: 'Deepseek处理技术说明',
            expectedProcessor: 'janus_pro'
          },
          {
            query: '摄像头网络是如何配置的？',
            complexity: 'complex',
            badge: 'Pro',
            description: 'Deepseek处理架构介绍',
            expectedProcessor: 'janus_pro'
          }
        ],

        complex: [
         {
            query: '工作帽违规时间分布',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '违规情况详细分析',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '安全风险评估和改进建议',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '分析一下违规趋势',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: 'cam_11和cam_28摄像头违规区域违规对比分析',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
          {
            query: '为什么口罩违规这么多',
            complexity: 'structured',
            badge: '快速',
            description: '基础AI深度分析',
            expectedProcessor: 'enhanced_basic_ai'
          },
        ],

        other: [
          {
            query: '你是谁？',
            complexity: 'complex',
            badge: 'Pro',
            description: 'Deepseek身份介绍',
            expectedProcessor: 'janus_pro'
          },
          {
            query: '如何改善餐厅厨房安全？',
            complexity: 'complex',
            badge: 'Pro',
            description: 'Deepseek建议咨询',
            expectedProcessor: 'janus_pro'
          }
        ]
      },

      message: {
        show: false,
        type: 'info',
        text: ''
      }
    }
  },

  computed: {
    isDateSelected() {
      return this.startDate && this.endDate;
    },

    isInputDisabled() {
      // 如果正在等待AI回覆，或者大模型正在載入中，則禁用輸入
      return this.systemStatus.janusProStatus === 'LOADING';
    },

    inputPlaceholder() {
      if (this.systemStatus.janusProStatus === 'LOADING') {
        return 'AI引擎正在启动中，请耐心等待...';
      }
      return "输入您的问题，如：'今天违规情况如何'";
    },

    statusIcon() {
      if (this.systemStatus.janusProStatus === 'LOADING') {
        return 'fas fa-spinner fa-spin'; // 旋轉圖示
      }
      switch (this.systemStatus.overall) {
        case 'healthy': return 'fas fa-check-circle'
        case 'degraded': return 'fas fa-exclamation-triangle'
        case 'checking': return 'fas fa-spinner fa-spin'
        default: return 'fas fa-times-circle'
      }
    },

    statusText() {
      if (this.systemStatus.janusProStatus === 'LOADING') {
        return '引擎载入中，这需要一点时间……';
      }
      switch (this.systemStatus.overall) {
        case 'healthy': return '系统正常'
        case 'degraded': return '功能受限'
        case 'checking': return '检查中...'
        default: return '系统异常'
      }
    }
  },

  mounted() {
    this.initConversation()
    this.checkSystemStatus()

    this.statusInterval = setInterval(this.checkSystemStatus, 15000)
  },

  beforeUnmount() {
    if (this.statusInterval) {
      clearInterval(this.statusInterval)
    }
  },

  methods: {
    // 初始化对话
    initConversation() {
      this.conversationId = localStorage.getItem('chat_conversation_id') || this.generateConversationId()
      localStorage.setItem('chat_conversation_id', this.conversationId)
    },

    // 检查系统状态
    async checkSystemStatus() {
      try {
        const response = await axios.get('/api/monitor/ai-query/routing-status/');
        if (response.data.success) {
          const status = response.data.routing_status;
          // [修改] 更新詳細狀態
          this.systemStatus.janusProStatus = status.janus_pro_status;
          this.systemStatus.basicAvailable = status.basic_processor_available;

          // 根據詳細狀態決定總體狀態
          if (status.janus_pro_status === 'LOADED') {
            this.systemStatus.overall = 'healthy';
          } else if (status.janus_pro_status === 'LOADING') {
            this.systemStatus.overall = 'checking'; // 或自定義一個 'loading' 狀態
          } else if (status.basic_processor_available) {
            this.systemStatus.overall = 'degraded';
          } else {
            this.systemStatus.overall = 'error';
          }
        }
      } catch (error) {
        console.error('检查系统状态失败:', error)
        this.systemStatus.overall = 'error'
        this.systemStatus.degraded = false
      }
    },

    // 生成对话ID
    generateConversationId() {
      return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    },

    // 获取当前分类的示例
    getCurrentExamples() {
      return this.exampleQueries[this.currentCategory] || []
    },

    // 清除時間選擇的方法
    clearTimeRange() {
      this.startDate = null;
      this.startTime = null;
      this.endDate = null;
      this.endTime = null;
      this.showMessage('已清除指定时间范围', 'info');
    },

    // 获取处理器名称
    getProcessorName(processor) {
      const names = {
        'janus_pro': 'Deepseek',
        'enhanced_basic_ai': '基础AI+',
        'basic_ai': '基础AI',
        'fallback_basic': '降级处理',
        'structured_template': '模板处理',
        'error': '错误'
      }
      return names[processor] || processor
    },
    // 获取处理器样式类
    getProcessorClass(processor) {
      const classes = {
        'janus_pro': 'Deepseek',
        'enhanced_basic_ai': 'enhanced-basic',
        'basic_ai': 'basic-ai',
        'fallback_basic': 'fallback',
        'structured_template': 'structured',
        'error': 'error'
      }
      return classes[processor] || 'unknown'
    },

    // 发送消息主方法
    async sendMessage(content) {
      // 1. 防止在載入時重複傳送
      if (this.isLoading) return;

      const userMessageContent = content.trim();
      if (!userMessageContent) return;

      // 2. 將使用者訊息新增至聊天視窗
      this.messages.push({
        id: this.generateMessageId(),
        type: 'user',
        content: userMessageContent,
        timestamp: new Date().toISOString()
      });
      this.$nextTick(this.scrollToBottom);

      // 3. 設定載入狀態和提示文字
      this.isLoading = true;
      this.loadingText = this.getLoadingText(userMessageContent);

      // 用於後續更新的AI訊息佔位符
      let aiMsgPlaceholder = null;

      // 4. 準備傳送給後端的 payload
      const payload = {
        query: userMessageContent,
        context: {
          conversation_history: this.getRecentMessages(5)
        }
      };

      // 5. 檢查並組合使用者在UI上選擇的自訂時間範圍
      if (this.startDate && this.endDate) {
        // 如果使用者只選日期沒選時間，提供預設值
        const finalStartTime = this.startTime || '00:00:00';
        const finalEndTime = this.endTime || '23:59:59';

        // 組合日期和時間，並轉換為UTC時間的ISO格式字串，以便後端解析
        const startISO = new Date(`${this.startDate}T${finalStartTime}`).toISOString();
        const endISO = new Date(`${this.endDate}T${finalEndTime}`).toISOString();

        payload.custom_time_range = {
          start_time: startISO,
          end_time: endISO
        };
      }

      try {
        // 6. 使用 fetch API 傳送請求
        const token = localStorage.getItem('authToken')
        const response = await fetch('/api/monitor/ai-query/smart/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        // 處理請求失敗的情況
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.reply || `HTTP 错误! 状态: ${response.status}`);
        }

        const contentType = response.headers.get("content-type");

        // 7. 判斷並處理流式回應 (text/event-stream)
        if (contentType && contentType.includes("text/event-stream")) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let isStreamStarted = false;

          // 使用標籤(label)以便從巢狀迴圈中優雅地跳出
          streamLoop: while (true) {
            const {
              done,
              value
            } = await reader.read();

            // 當伺服器關閉連線時，done 會是 true
            if (done) break;

            // 解碼收到的數據塊，{stream: true}確保中文字元不會被截斷
            const chunk = decoder.decode(value, {
              stream: true
            });
            const eventLines = chunk.split('\n\n').filter(line => line.length > 0);

            for (const eventLine of eventLines) {
              if (eventLine.startsWith('data:')) {
                const dataStr = eventLine.substring(5).trim();
                try {
                  const data = JSON.parse(dataStr);

                  // 如果收到 token，則更新UI
                  if (data.token) {
                    if (!isStreamStarted) {
                      // 第一次收到 token，建立 AI 訊息物件
                      isStreamStarted = true;
                      this.isLoading = false; // 隱藏"正在輸入中"的提示
                      aiMsgPlaceholder = {
                        id: this.generateMessageId(),
                        type: 'ai',
                        content: data.token,
                        timestamp: new Date().toISOString(),
                        metadata: {}
                      };
                      this.messages.push(aiMsgPlaceholder);
                    } else {
                      // 後續收到 token，以響應式的方式更新訊息內容
                      const messageIndex = this.messages.findIndex(msg => msg.id === aiMsgPlaceholder.id);
                      if (messageIndex > -1) {
                        // 建立一個新物件來取代舊物件，確保Vue能偵測到變化
                        const updatedMessage = {
                          ...this.messages[messageIndex],
                          content: this.messages[messageIndex].content + data.token
                        };
                        this.messages.splice(messageIndex, 1, updatedMessage);
                      }
                    }
                    // 更新UI後，自動滾動到底部
                    this.$nextTick(this.scrollToBottom);
                  }

                  // 如果收到結束或錯誤信號，則跳出最外層的 while 迴圈
                  if (data.status === 'done' || data.error) {
                    break streamLoop;
                  }

                } catch (e) {
                  console.error("解析JSON数据流失败:", dataStr, e);
                }
              }
            }
          }
        } else {
          // 8. 處理非流式回應 (application/json)
          this.isLoading = false;
          const data = await response.json();
          aiMsgPlaceholder = {
            id: this.generateMessageId(),
            type: 'ai',
            content: data.reply || "无法获取有效回复。",
            timestamp: new Date().toISOString(),
            metadata: {
              processing_time: data.processing_time,
              routing_info: data.routing_info || {
                processor: data.processor_used
              }
            }
          };
          this.messages.push(aiMsgPlaceholder);
        }
      } catch (error) {
        // 9. 統一處理所有錯誤
        this.isLoading = false;
        const errorMsg = {
          id: this.generateMessageId(),
          type: 'ai',
          content: `抱歉，处理时发生错误：\n${error.message}`,
          timestamp: new Date().toISOString(),
          metadata: {
            routing_info: {
              processor: 'error'
            }
          }
        };
        this.messages.push(errorMsg);
        this.showMessage('消息处理失败: ' + error.message, 'error');
      } finally {
        // 10. 無論成功或失敗，最後都確保重置載入狀態並滾動到底部
        this.isLoading = false;
        this.$nextTick(this.scrollToBottom);
      }
    },

    showProcessorFeedback(routingInfo) {
      if (!routingInfo) return

      const processor = routingInfo.processor
      const confidence = routingInfo.confidence

      if (processor === 'janus_pro') {
        this.showMessage('已使用Deepseek深度分析', 'success')
      } else if (processor === 'enhanced_basic_ai') {
        this.showMessage('基础AI快速处理完成', 'info')
      } else if (processor.includes('fallback')) {
        this.showMessage('已降级处理您的查询', 'warning')
      }
      if (confidence && confidence < 0.7) {
        setTimeout(() => {
          this.showMessage('如需更准确的答案，可以尝试重新表述您的问题', 'info')
        }, 2000)
      }
    },


    // 根据问题内容生成对应的加载提示
    getLoadingText(query) {
      const queryLower = query.toLowerCase()

      // 预测可能的处理器
      if (queryLower.includes('系统') || queryLower.includes('功能') ||
          queryLower.includes('算') || queryLower.includes('等于')) {
        return 'Deepseek正在深度思考中...'
      } else if (queryLower.includes('分析') && (queryLower.includes('本月') || queryLower.includes('2025年'))) {
        return 'Deepseek正在进行复杂分析...'
      } else if (queryLower.includes('今天') || queryLower.includes('违规') || queryLower.includes('cam_')) {
        return '正在快速处理结构化查询...'
      } else {
        return '智能路由正在选择最佳处理方式...'
      }
    },


    getRecentMessages(limit = 5) {
      return this.messages.slice(-limit).map(msg => ({
        type: msg.type,
        content: msg.content,
        timestamp: msg.timestamp
      }))
    },

    async sendUserMessage() {
      if (!this.inputMessage.trim() || this.isLoading) {
        return
      }

      const message = this.inputMessage.trim()
      this.inputMessage = ''

      await this.sendMessage(message)
    },

    // 生成消息ID
    generateMessageId() {
      return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    },

    // 清空对话
    async clearConversation() {
      if (this.messages.length === 0) return

      try {
        await ElMessageBox.confirm('确认清空当前对话记录吗？', '提示', { type: 'warning' })
      } catch { return }

      this.messages = []
      this.conversationId = this.generateConversationId()
      localStorage.setItem('chat_conversation_id', this.conversationId)
      this.showMessage('对话记录已清空', 'success')
    },

    // 处理键盘事件
    handleKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.sendUserMessage()
      }
    },

    // 滚动到底部
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },

    // 格式化时间
    formatTime(timestamp) {
      const now = new Date()
      const msgTime = new Date(timestamp)
      const diff = now - msgTime

      if (diff < 60000) {
        return '刚刚'
      } else if (diff < 3600000) {
        return Math.floor(diff / 60000) + '分钟前'
      } else if (msgTime.toDateString() === now.toDateString()) {
        return msgTime.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      } else {
        return msgTime.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      }
    },

    // 格式化消息文本
    formatMessageText(text) {
      if (!text) return ''

      return marked.parse(text, { gfm: true, breaks: true });
    },

    // 显示消息
    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      setTimeout(() => {
        this.message.show = false
      }, type === 'error' ? 5000 : 3000)
    }
  }
}
</script>

<style scoped>
/* 基础样式保持不变，添加新的样式 */
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 12px;
  border: 1px solid transparent;
}

.status-indicator.healthy {
  background: #f0fff4;
  color: #38a169;
  border-color: #9ae6b4;
}

.status-indicator.degraded {
  background: #fffbeb;
  color: #d69e2e;
  border-color: #fbd38d;
}

.status-indicator.checking {
  background: #ebf8ff;
  color: #3182ce;
  border-color: #90cdf4;
}

.status-indicator.error {
  background: #fed7d7;
  color: #e53e3e;
  border-color: #fc8181;
}

.capabilities {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
}

.capability-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #4a5568;
  font-size: 12px;
}

.capability-item i {
  font-size: 24px;
  color: #3182ce;
}

.example-categories {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.category-btn {
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #4a5568;
  padding: 4px 12px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.category-btn.active,
.category-btn:hover {
  background: #3182ce;
  border-color: #3182ce;
  color: white;
}

.example-btn {
  display: flex;
  align-items: center;
  background: #edf2f7;
  border: 1px solid #e2e8f0;
  color: #1a202c;
  padding: 8px 12px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 12px;
  margin: 4px;
  transition: all 0.2s;
  min-width: 0;
}

.example-btn.simple {
  border-left: 3px solid #48bb78;
}

.example-btn.complex {
  border-left: 3px solid #ed64a6;
}

.example-btn:hover {
  background: #bee3f8;
  border-color: #63b3ed;
  transform: translateY(-1px);
}

.example-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}

.example-text {
  flex: 1;
  text-align: left;
}

.complexity-badge {
  background: #3182ce;
  color: white;
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

.example-btn.complex .complexity-badge {
  background: #ed64a6;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.routing-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.processing-time {
  font-size: 9px;
  color: #718096;
  background: #edf2f7;
  padding: 2px 4px;
  border-radius: 4px;
}

.chat-messages {
  flex: 1;
  padding: 15px 0;
  overflow-y: auto;
  background: #ffffff;
}

.welcome-message {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.chat-messages.is-empty {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.welcome-content {
  text-align: center;
  color: #718096;
}

.welcome-icon {
  font-size: 48px;
  color: #3182ce;
  margin-bottom: 15px;
}

.welcome-content h4 {
  margin: 0 0 10px 0;
  color: #1a202c;
  font-size: 18px;
}

.message-wrapper {
  margin-bottom: 15px;
  padding: 0 15px;
}

.message-content {
  display: flex;
  max-width: 80%;
  gap: 10px;
}

.user-wrapper .message-content {
  margin-left: auto;
  flex-direction: row-reverse;
}

.ai-wrapper .message-content {
  margin-right: auto;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.user-wrapper .message-avatar {
  background: #3182ce;
  color: white;
}

.ai-wrapper .message-avatar {
  background: #edf2f7;
  color: #4a5568;
}

.message-bubble {
  max-width: 100%;
  word-wrap: break-word;
  padding: 10px 15px;
  border-radius: 15px;
}

.user-wrapper .message-bubble {
  background: #3182ce;
  color: white;
  border-radius: 15px 15px 4px 15px;
}

.ai-wrapper .message-bubble {
  background: #f7fafc;
  color: #1a202c;
  border: 1px solid #e2e8f0;
  border-radius: 15px 15px 15px 4px;
}

.loading-bubble {
  background: #f7fafc !important;
  border: 1px solid #e2e8f0 !important;
}

.message-text {
  line-height: 1.5;
  font-size: 14px;
  margin-bottom: 4px;
}

.message-time {
  font-size: 10px;
  opacity: 0.7;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #718096;
}

.typing-indicator span:not(.typing-text) {
  width: 6px;
  height: 6px;
  background: #3182ce;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

.example-queries-section {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.example-header {
  padding: 10px 20px;
}

.example-title {
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
}

.example-queries {
  padding: 0 16px 12px;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.clear-btn {
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #718096;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.clear-btn:hover:not(:disabled) {
  background: #fed7d7;
  border-color: #fc8181;
  color: #e53e3e;
}

.clear-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-input {
  padding: 15px 20px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.input-container {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.message-input {
  flex: 1;
  min-height: 36px;
  padding: 8px 15px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.4;
  background: #f8fafc;
  transition: all 0.2s;
}

.message-input:focus {
  border-color: #3182ce;
  background: white;
  box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1);
}

.send-button {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #3182ce;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.send-button:hover:not(:disabled) {
  background: #2c5282;
}

.send-button:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 2px;
}

.status-detail {
  font-size: 10px;
  margin-top: 2px;
  opacity: 0.8;
}

.confidence-score {
  font-size: 9px;
  color: #718096;
  background: #e2e8f0;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: help;
}

.example-btn.structured {
  border-left: 3px solid #38a169;
}

.time-selector-section {
  background: #fdfdfd;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  padding: 10px 20px;
  flex-shrink: 0;
}

.time-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.time-selector-title {
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
}
.clear-time-btn {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #4a5568;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}
.clear-time-btn:hover {
  background: #e2e8f0;
}
.time-selector-inputs {
  display: flex;
  gap: 10px;
  align-items: center;
}
.time-selector-inputs .el-date-picker,
.time-selector-inputs .el-time-picker {
  width: 100% !important; /* 讓元件填滿空間 */
}
.time-separator {
  font-size: 12px;
  color: #718096;
}

.message-text ::v-deep table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #333;
  background-color: #fff;
}

.message-text ::v-deep th,
.message-text ::v-deep td {
  border: 1px solid #dfe2e5;
  padding: 8px 12px;
  text-align: center;
}

.message-text ::v-deep th {
  background-color: #f7f7f7;
  font-weight: 600;
}

.message-text ::v-deep tr:nth-child(even) {
  background-color: #fcfcfc;
}
</style>