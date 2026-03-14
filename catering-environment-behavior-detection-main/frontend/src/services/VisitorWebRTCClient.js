/**
 * Visitor端 WebRTC P2P 文件共享客户端
 * 作用：Visitor使用access_token访问Manager的本地文件
 */

class VisitorWebRTCClient {
    constructor(visitorName, eid, accessToken) {
        this.visitorName = visitorName;
        this.eid = eid;
        this.accessToken = accessToken;
        this.ws = null;
        this.peerConnection = null;
        this.dataChannel = null;
        this.currentManager = null;
        this.receivedFileChunks = [];
        this.receivedFileMetadata = null;

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
        };
    }

    /**
     * 认证（使用access_token）
     */
    authenticate() {
        this.send({
            type: 'auth',
            user_id: this.visitorName,
            user_type: 'visitor',
            eid: this.eid,
            access_token: this.accessToken
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
     * 请求在线用户列表
     */
    requestOnlineUsers() {
        this.send({ type: 'request_online_users' });
    }

    /**
     * 处理信令消息
     */
    async handleMessage(data) {
        switch (data.type) {
            case 'auth_success':
                console.log('Visitor认证成功:', data);
                this.onAuthSuccess && this.onAuthSuccess(data);
                // 认证成功后，获取在线用户列表
                this.requestOnlineUsers();
                break;

            case 'online_users':
                // 收到在线用户列表
                this.handleOnlineUsers(data.users);
                break;

            case 'file_access_response':
                // Manager响应文件访问请求
                this.handleFileAccessResponse(data);
                break;

            case 'answer':
                // 收到WebRTC Answer
                await this.handleAnswer(data);
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
     * 处理在线用户列表
     */
    handleOnlineUsers(users) {
        // 筛选出Manager
        const managers = users.filter(u => u.user_type === 'manager');
        console.log('在线Manager列表:', managers);

        if (this.onOnlineManagersUpdate) {
            this.onOnlineManagersUpdate(managers);
        }
    }

    /**
     * 请求访问Manager的文件
     */
    requestFileAccess(managerName, warehouseId, filePath) {
        this.currentManager = managerName;

        this.send({
            type: 'request_file_access',
            target_manager: managerName,
            warehouse_id: warehouseId,
            file_path: filePath
        });

        console.log(`已请求访问 ${managerName} 的文件: ${filePath}`);
    }

    /**
     * 处理Manager的文件访问响应
     */
    async handleFileAccessResponse(data) {
        console.log('Manager响应:', data);

        if (data.approved) {
            console.log('访问已批准，开始建立P2P连接');
            this.onAccessApproved && this.onAccessApproved(data.manager_id);

            // 建立WebRTC连接
            await this.createPeerConnection(data.manager_id);
        } else {
            console.log('访问被拒绝');
            this.onAccessDenied && this.onAccessDenied(data.manager_id);
        }
    }

    /**
     * 创建PeerConnection并发送Offer
     */
    async createPeerConnection(managerName) {
        try {
            // 创建PeerConnection
            this.peerConnection = new RTCPeerConnection(this.rtcConfig);

            // 监听ICE候选
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    this.send({
                        type: 'ice-candidate',
                        target_user: managerName,
                        candidate: event.candidate
                    });
                }
            };

            // 监听连接状态
            this.peerConnection.onconnectionstatechange = () => {
                console.log('连接状态:', this.peerConnection.connectionState);

                if (this.peerConnection.connectionState === 'connected') {
                    this.onConnectionEstablished && this.onConnectionEstablished();
                }
            };

            // 创建DataChannel
            this.dataChannel = this.peerConnection.createDataChannel('fileTransfer', {
                ordered: true
            });

            this.setupDataChannel();

            // 创建Offer
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);

            // 发送Offer给Manager
            this.send({
                type: 'offer',
                target_user: managerName,
                offer: offer
            });

            console.log('已发送Offer给Manager');

        } catch (error) {
            console.error('创建PeerConnection失败:', error);
        }
    }

    /**
     * 处理WebRTC Answer
     */
    async handleAnswer(data) {
        console.log('收到Answer from Manager');

        try {
            await this.peerConnection.setRemoteDescription(
                new RTCSessionDescription(data.answer)
            );
            console.log('已设置远程描述');
        } catch (error) {
            console.error('设置远程描述失败:', error);
        }
    }

    /**
     * 处理ICE候选
     */
    async handleIceCandidate(data) {
        if (this.peerConnection && data.candidate) {
            try {
                await this.peerConnection.addIceCandidate(
                    new RTCIceCandidate(data.candidate)
                );
                console.log('已添加ICE候选');
            } catch (error) {
                console.error('添加ICE候选失败:', error);
            }
        }
    }

    /**
     * 设置DataChannel
     */
    setupDataChannel() {
        this.dataChannel.onopen = () => {
            console.log('DataChannel已打开，可以请求文件');
            this.onDataChannelOpen && this.onDataChannelOpen();
        };

        this.dataChannel.onclose = () => {
            console.log('DataChannel已关闭');
            this.onDataChannelClose && this.onDataChannelClose();
        };

        this.dataChannel.onmessage = (event) => {
            this.handleDataChannelMessage(event.data);
        };

        this.dataChannel.onerror = (error) => {
            console.error('DataChannel错误:', error);
        };
    }

    /**
     * 处理DataChannel消息
     */
    handleDataChannelMessage(data) {
        // 检查是否是JSON消息
        if (typeof data === 'string') {
            try {
                const message = JSON.parse(data);

                if (message.type === 'file_metadata') {
                    // 文件元数据
                    this.receivedFileMetadata = message;
                    this.receivedFileChunks = [];
                    console.log('开始接收文件:', message.name, '大小:', message.size);

                    this.onFileReceiveStart && this.onFileReceiveStart(message);

                } else if (message.type === 'file_complete') {
                    // 文件接收完成
                    this.assembleFile();

                } else if (message.type === 'error') {
                    console.error('文件传输错误:', message.message);
                    this.onFileReceiveError && this.onFileReceiveError(message.message);
                }
            } catch (e) {
                console.error('解析消息失败:', e);
            }
        } else {
            // 二进制数据块
            this.receivedFileChunks.push(data);

            // 计算进度
            if (this.receivedFileMetadata) {
                const receivedSize = this.receivedFileChunks.reduce(
                    (acc, chunk) => acc + chunk.byteLength, 0
                );
                const progress = (receivedSize / this.receivedFileMetadata.size) * 100;

                this.onFileReceiveProgress && this.onFileReceiveProgress(progress);
            }
        }
    }

    /**
     * 组装接收到的文件
     */
    assembleFile() {
        console.log('组装文件，总块数:', this.receivedFileChunks.length);

        // 合并所有数据块
        const blob = new Blob(this.receivedFileChunks);

        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = this.receivedFileMetadata.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        console.log('文件接收完成:', this.receivedFileMetadata.name);

        this.onFileReceiveComplete && this.onFileReceiveComplete(
            this.receivedFileMetadata,
            blob
        );

        // 清理
        this.receivedFileChunks = [];
        this.receivedFileMetadata = null;
    }

    /**
     * 请求文件
     */
    requestFile(filePath) {
        if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
            console.error('DataChannel未打开');
            return;
        }

        this.dataChannel.send(JSON.stringify({
            type: 'request_file',
            file_path: filePath
        }));

        console.log('已请求文件:', filePath);
    }

    /**
     * 断开连接
     */
    disconnect() {
        if (this.dataChannel) {
            this.dataChannel.close();
        }

        if (this.peerConnection) {
            this.peerConnection.close();
        }

        if (this.ws) {
            this.ws.close();
        }
    }
}

// 使用示例
/*
const visitorClient = new VisitorWebRTCClient(
    'visitor_li',
    'company123',
    'your_access_token_here'
);

// 设置回调
visitorClient.onAuthSuccess = () => {
    console.log('Visitor认证成功');
};

visitorClient.onOnlineManagersUpdate = (managers) => {
    console.log('在线Manager:', managers);
    // 显示在线Manager列表供用户选择
};

visitorClient.onAccessApproved = (managerId) => {
    console.log('访问已批准，Manager:', managerId);
};

visitorClient.onAccessDenied = (managerId) => {
    alert('访问被拒绝');
};

visitorClient.onConnectionEstablished = () => {
    console.log('P2P连接已建立');
};

visitorClient.onDataChannelOpen = () => {
    console.log('可以开始请求文件了');
    // 自动请求文件
    visitorClient.requestFile('warehouse1/data.json');
};

visitorClient.onFileReceiveStart = (metadata) => {
    console.log(`开始接收: ${metadata.name}, ${metadata.size} bytes`);
};

visitorClient.onFileReceiveProgress = (progress) => {
    console.log(`接收进度: ${progress.toFixed(2)}%`);
};

visitorClient.onFileReceiveComplete = (metadata, blob) => {
    console.log('文件接收完成!');
    alert(`文件 ${metadata.name} 已下载`);
};

// 连接
visitorClient.connect();

// 用户选择Manager后请求访问
// visitorClient.requestFileAccess('manager_zhang', 'warehouse1', 'data.json');
*/