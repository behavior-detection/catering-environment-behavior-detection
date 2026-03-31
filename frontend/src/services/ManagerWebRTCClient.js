/**
 * Manager端 WebRTC P2P 文件共享客户端
 * 作用：Manager可以分享本地文件给经过授权的Visitor
 */

class ManagerWebRTCClient {
    constructor(managerName, eid) {
        this.managerName = managerName;
        this.eid = eid;
        this.ws = null;
        this.peerConnections = {}; // 存储多个P2P连接
        this.dataChannels = {}; // 存储数据通道
        this.localFiles = new Map(); // 本地文件索引

        // WebRTC配置
        this.rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
    }

    /**
     * 连接到WebSocket信令服务器
     */
    connect() {
        const wsUrl = `ws://${window.location.host}/ws/file-share/`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket连接成功');
            this.authenticate();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket连接关闭');
            // 可以实现重连逻辑
        };
    }

    /**
     * 认证
     */
    authenticate() {
        this.send({
            type: 'auth',
            user_id: this.managerName,
            user_type: 'manager',
            eid: this.eid
        });
    }

    /**
     * 发送消息到信令服务器
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    /**
     * 处理信令消息
     */
    async handleMessage(data) {
        switch (data.type) {
            case 'auth_success':
                console.log('认证成功:', data);
                this.onAuthSuccess && this.onAuthSuccess(data);
                break;

            case 'file_access_request':
                // Visitor请求访问文件
                this.handleFileAccessRequest(data);
                break;

            case 'offer':
                // 收到WebRTC Offer
                await this.handleOffer(data);
                break;

            case 'ice-candidate':
                // 收到ICE候选
                await this.handleIceCandidate(data);
                break;

            case 'user_online':
                console.log('用户上线:', data.user_id);
                this.onUserOnline && this.onUserOnline(data);
                break;

            case 'user_offline':
                console.log('用户下线:', data.user_id);
                this.onUserOffline && this.onUserOffline(data);
                break;

            case 'error':
                console.error('服务器错误:', data.message);
                this.onError && this.onError(data.message);
                break;
        }
    }

    /**
     * 处理Visitor的文件访问请求
     */
    handleFileAccessRequest(data) {
        console.log('收到文件访问请求:', data);

        // 显示UI让Manager确认
        if (this.onFileAccessRequest) {
            this.onFileAccessRequest(data, (approved) => {
                this.respondToFileRequest(data.from_user, approved);
            });
        }
    }

    /**
     * 响应文件访问请求
     */
    respondToFileRequest(visitorId, approved) {
        this.send({
            type: 'approve_file_access',
            visitor_id: visitorId,
            approved: approved
        });

        if (approved) {
            // 批准后，等待Visitor发送Offer
            console.log(`已批准 ${visitorId} 的访问请求，等待建立连接`);
        }
    }

    /**
     * 处理WebRTC Offer
     */
    async handleOffer(data) {
        const visitorId = data.from_user;
        console.log(`收到来自 ${visitorId} 的Offer`);

        try {
            // 创建PeerConnection
            const pc = new RTCPeerConnection(this.rtcConfig);
            this.peerConnections[visitorId] = pc;

            // 监听ICE候选
            pc.onicecandidate = (event) => {
                if (event.candidate) {
                    this.send({
                        type: 'ice-candidate',
                        target_user: visitorId,
                        candidate: event.candidate
                    });
                }
            };

            // 监听DataChannel（Visitor创建）
            pc.ondatachannel = (event) => {
                const dataChannel = event.channel;
                this.dataChannels[visitorId] = dataChannel;
                this.setupDataChannel(dataChannel, visitorId);
                console.log('DataChannel已接收:', dataChannel.label);
            };

            // 设置远程描述
            await pc.setRemoteDescription(new RTCSessionDescription(data.offer));

            // 创建Answer
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);

            // 发送Answer
            this.send({
                type: 'answer',
                target_user: visitorId,
                answer: answer
            });

            console.log(`已发送Answer给 ${visitorId}`);

        } catch (error) {
            console.error('处理Offer失败:', error);
        }
    }

    /**
     * 处理ICE候选
     */
    async handleIceCandidate(data) {
        const userId = data.from_user;
        const pc = this.peerConnections[userId];

        if (pc && data.candidate) {
            try {
                await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
                console.log(`已添加ICE候选 from ${userId}`);
            } catch (error) {
                console.error('添加ICE候选失败:', error);
            }
        }
    }

    /**
     * 设置DataChannel
     */
    setupDataChannel(dataChannel, visitorId) {
        dataChannel.onopen = () => {
            console.log(`DataChannel打开，可以发送文件给 ${visitorId}`);
            this.onDataChannelOpen && this.onDataChannelOpen(visitorId);
        };

        dataChannel.onclose = () => {
            console.log(`DataChannel关闭 with ${visitorId}`);
        };

        dataChannel.onmessage = async (event) => {
            // 接收Visitor的文件请求
            const request = JSON.parse(event.data);

            if (request.type === 'request_file') {
                await this.sendFile(dataChannel, request.file_path);
            }
        };

        dataChannel.onerror = (error) => {
            console.error('DataChannel错误:', error);
        };
    }

    /**
     * 索引本地文件（Manager需要在页面加载时调用）
     */
    indexLocalFiles(files) {
        // files格式：[{path: 'warehouse1/file1.json', file: File对象}]
        files.forEach(item => {
            this.localFiles.set(item.path, item.file);
        });
        console.log(`已索引 ${files.length} 个本地文件`);
    }

    /**
     * 通过DataChannel发送文件
     */
    async sendFile(dataChannel, filePath) {
        const file = this.localFiles.get(filePath);

        if (!file) {
            console.error('文件不存在:', filePath);
            dataChannel.send(JSON.stringify({
                type: 'error',
                message: '文件不存在'
            }));
            return;
        }

        console.log(`开始发送文件: ${file.name}, 大小: ${file.size} bytes`);

        // 发送文件元数据
        dataChannel.send(JSON.stringify({
            type: 'file_metadata',
            name: file.name,
            size: file.size,
            path: filePath
        }));

        // 分块发送文件
        const chunkSize = 16384; // 16KB
        let offset = 0;

        const reader = new FileReader();

        reader.onload = (e) => {
            dataChannel.send(e.target.result);
            offset += chunkSize;

            // 报告进度
            const progress = Math.min((offset / file.size) * 100, 100);
            this.onSendProgress && this.onSendProgress(filePath, progress);

            if (offset < file.size) {
                readSlice(offset);
            } else {
                // 发送完成信号
                dataChannel.send(JSON.stringify({
                    type: 'file_complete',
                    path: filePath
                }));
                console.log('文件发送完成:', filePath);
            }
        };

        const readSlice = (o) => {
            const slice = file.slice(o, o + chunkSize);
            reader.readAsArrayBuffer(slice);
        };

        readSlice(0);
    }

    /**
     * 断开连接
     */
    disconnect() {
        // 关闭所有PeerConnections
        Object.values(this.peerConnections).forEach(pc => pc.close());
        this.peerConnections = {};
        this.dataChannels = {};

        // 关闭WebSocket
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 使用示例
/*
const managerClient = new ManagerWebRTCClient('manager_zhang', 'company123');

// 设置回调
managerClient.onAuthSuccess = (data) => {
    console.log('Manager认证成功');
};

managerClient.onFileAccessRequest = (data, callback) => {
    // 显示确认对话框
    const approved = confirm(`Visitor ${data.from_user} 请求访问文件，是否批准？`);
    callback(approved);
};

managerClient.onDataChannelOpen = (visitorId) => {
    console.log(`准备向 ${visitorId} 发送文件`);
};

managerClient.onSendProgress = (filePath, progress) => {
    console.log(`发送进度: ${filePath} - ${progress.toFixed(2)}%`);
};

// 连接
managerClient.connect();

// 索引本地文件（从input file选择）
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files).map(file => ({
        path: `warehouse1/${file.name}`,
        file: file
    }));
    managerClient.indexLocalFiles(files);
});
*/