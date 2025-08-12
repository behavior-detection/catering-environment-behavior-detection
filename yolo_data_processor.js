// yolo_data_processor.js
const fs = require('fs');
const path = require('path');
const axios = require('axios');

class YoloDataProcessor {
    constructor(config = {}) {
        this.config = {
            batchOutputDir: config.batchOutputDir || './batch_out',
            imagesDir: config.imagesDir || './batch_out/images',
            jsonDir: config.jsonDir || './batch_out/json',
            serverUrl: config.serverUrl || 'http://localhost:3000',
            processInterval: config.processInterval || 10000,
            ...config
        };

        this.processedFiles = new Set();
        this.processedHashes = new Set();
        this.isProcessing = false;
        this.violationStats = {
            totalProcessed: 0,
            totalViolations: 0,
            violationsByType: {},
            violationsByCamera: {}
        };
    }

    start() {
        console.log('启动YOLO数据处理器...');
        console.log(`监控目录: ${this.config.jsonDir}`);

        this.ensureDirectories();

        setInterval(() => {
            this.processNewFiles();
        }, this.config.processInterval);

        this.processNewFiles();
    }

    ensureDirectories() {
        [this.config.batchOutputDir, this.config.imagesDir, this.config.jsonDir].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
                console.log(`创建目录: ${dir}`);
            }
        });
    }

    async processNewFiles() {
        if (this.isProcessing) return;
        this.isProcessing = true;

        try {
            const jsonFiles = fs.readdirSync(this.config.jsonDir)
                .filter(f => f.endsWith('.json') && !this.processedFiles.has(f));

            if (jsonFiles.length > 0) {
                console.log(`📁 发现 ${jsonFiles.length} 个新的JSON文件`);
            }

            for (const jsonFile of jsonFiles) {
                try {
                    await this.processJsonFile(jsonFile);
                    this.processedFiles.add(jsonFile);
                } catch (error) {
                    console.error(`❌ 处理文件失败 ${jsonFile}:`, error.message);
                }
            }

            if (jsonFiles.length > 0) {
                console.log(`📊 处理统计: 已处理 ${this.violationStats.totalProcessed} 个文件，检测到 ${this.violationStats.totalViolations} 次违规`);
            }

        } catch (error) {
            console.error('❌ 扫描目录失败:', error.message);
        } finally {
            this.isProcessing = false;
        }
    }

    async processJsonFile(jsonFileName) {
        const jsonPath = path.join(this.config.jsonDir, jsonFileName);

        console.log(`📝 处理文件: ${jsonFileName}`);

        // 读取并解析JSON
        let detectionData;
        try {
            const jsonContent = fs.readFileSync(jsonPath, 'utf8');
            detectionData = JSON.parse(jsonContent);
        } catch (error) {
            throw new Error(`解析JSON失败: ${error.message}`);
        }

        // 处理数据
        const processedData = this.processDetectionData(detectionData, jsonFileName);

        // 生成内容哈希去重
        const contentHash = this.generateContentHash(processedData);
        if (this.processedHashes.has(contentHash)) {
            console.log(`⚠️ 跳过重复数据: ${jsonFileName}`);
            return;
        }

        // 保存到数据库
        const recordId = await this.saveToDatabase(processedData);
        this.processedHashes.add(contentHash);

        // 更新统计
        this.updateStats(processedData);

        console.log(`✅ 成功处理: ${jsonFileName} (记录ID: ${recordId}) - 违规${processedData.total_violations}次`);
    }

    processDetectionData(rawData, fileName) {
        // 提取违规数据
        const violations = {};
        let totalViolations = 0;

        if (rawData.violations && typeof rawData.violations === 'object') {
            for (const [type, count] of Object.entries(rawData.violations)) {
                if (typeof count === 'number' && count > 0) {
                    violations[type] = count;
                    totalViolations += count;
                }
            }
        }

        // 如果没有violations但有total_violations，基于摄像头估算
        if (Object.keys(violations).length === 0 && rawData.total_violations > 0) {
            totalViolations = rawData.total_violations;
            const cameraId = rawData.camera_id || this.extractCameraIdFromFileName(fileName);
            Object.assign(violations, this.estimateViolations(totalViolations, cameraId));
        }

        // 解析时间戳
        const timestamp = this.parseTimestamp(rawData.timestamp);

        return {
            camera_id: rawData.camera_id || this.extractCameraIdFromFileName(fileName),
            detection_timestamp: timestamp,
            violations: violations,
            total_violations: totalViolations,
            source_file: fileName
        };
    }

    estimateViolations(totalViolations, cameraId) {
        const violations = {};

        if (totalViolations <= 0) return violations;

        // 根据摄像头智能分配
        if (cameraId === 'cam_28') {
            violations.mask = Math.ceil(totalViolations * 0.6);
            violations.hat = totalViolations - violations.mask;
        } else if (cameraId === 'cam_11') {
            violations.hat = Math.ceil(totalViolations * 0.7);
            violations.mask = totalViolations - violations.hat;
        } else {
            violations.mask = Math.ceil(totalViolations * 0.5);
            violations.hat = totalViolations - violations.mask;
        }

        // 移除0值
        Object.keys(violations).forEach(key => {
            if (violations[key] <= 0) delete violations[key];
        });

        return violations;
    }

    extractCameraIdFromFileName(fileName) {
        const match = fileName.match(/^(D\d+)/);
        if (match) {
            const mapping = { 'D11': 'cam_11', 'D28': 'cam_28', 'D34': 'cam_34' };
            return mapping[match[1]] || match[1];
        }
        return 'unknown';
    }

    parseTimestamp(timestampStr) {
        try {
            if (timestampStr && timestampStr.includes('年')) {
                const match = timestampStr.match(/(\d{4})年(\d{2})月(\d{2})日.*?(\d{2}):(\d{2}):(\d{2})/);
                if (match) {
                    const [, year, month, day, hour, minute, second] = match;
                    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`);
                }
            }
            return new Date(timestampStr || Date.now());
        } catch (error) {
            return new Date();
        }
    }

    generateContentHash(processedData) {
        const crypto = require('crypto');
        const content = `${processedData.camera_id}_${processedData.detection_timestamp.toISOString()}_${JSON.stringify(processedData.violations)}_${processedData.total_violations}`;
        return crypto.createHash('md5').update(content).digest('hex');
    }

    async saveToDatabase(processedData) {
        try {
            // 创建干净的违规数据对象
            const violationDataObject = {
                violations: processedData.violations,
                total_violations: processedData.total_violations,
                camera_id: processedData.camera_id,
                source: 'yolo_processor_fixed',
                processed_at: new Date().toISOString(),
                source_file: processedData.source_file
            };

            // JSON序列化
            const violationDataJson = this.createSafeJson(violationDataObject);

            const requestData = {
                camera_id: processedData.camera_id,
                detection_timestamp: processedData.detection_timestamp,
                violation_data: violationDataJson, // 发送JSON字符串
                total_violations: processedData.total_violations
            };

            console.log(`💾 保存数据: ${processedData.camera_id} - ${processedData.total_violations}次违规`);

            const response = await axios.post(`${this.config.serverUrl}/api/violations/save`, requestData, {
                headers: { 'Content-Type': 'application/json' },
                timeout: 8000
            });

            if (response.data.success) {
                return response.data.record_id;
            } else {
                throw new Error(response.data.message || '保存失败');
            }

        } catch (error) {
            console.error('❌ 数据库保存失败:', error.message);
            throw error;
        }
    }

    createSafeJson(obj) {
        try {
            // 确保对象结构干净
            const cleanObj = {
                violations: {},
                total_violations: 0,
                camera_id: 'unknown',
                source: 'yolo_processor_fixed',
                processed_at: new Date().toISOString()
            };

            // 安全复制violations
            if (obj.violations && typeof obj.violations === 'object') {
                for (const [key, value] of Object.entries(obj.violations)) {
                    if (typeof value === 'number' && value >= 0) {
                        cleanObj.violations[key] = value;
                    }
                }
            }

            // 安全复制其他字段
            if (typeof obj.total_violations === 'number') {
                cleanObj.total_violations = obj.total_violations;
            }
            if (typeof obj.camera_id === 'string') {
                cleanObj.camera_id = obj.camera_id;
            }
            if (typeof obj.source_file === 'string') {
                cleanObj.source_file = obj.source_file;
            }

            // 序列化
            const jsonString = JSON.stringify(cleanObj);

            // 验证
            if (jsonString.includes('[object Object]') || jsonString.includes('undefined')) {
                throw new Error('JSON包含无效内容');
            }

            // 测试解析
            const testParse = JSON.parse(jsonString);
            if (typeof testParse.violations !== 'object') {
                throw new Error('violations字段无效');
            }

            return jsonString;

        } catch (error) {
            console.error('❌ 创建安全JSON失败:', error);
            // 返回最基本的结构
            return JSON.stringify({
                violations: {},
                total_violations: 0,
                camera_id: 'unknown',
                source: 'fallback'
            });
        }
    }

    updateStats(processedData) {
        this.violationStats.totalProcessed++;
        this.violationStats.totalViolations += processedData.total_violations;

        // 按类型统计
        for (const [type, count] of Object.entries(processedData.violations)) {
            this.violationStats.violationsByType[type] =
                (this.violationStats.violationsByType[type] || 0) + count;
        }

        // 按摄像头统计
        this.violationStats.violationsByCamera[processedData.camera_id] =
            (this.violationStats.violationsByCamera[processedData.camera_id] || 0) + processedData.total_violations;
    }

    getStats() {
        return {
            ...this.violationStats,
            processedFiles: this.processedFiles.size,
            processedHashes: this.processedHashes.size,
            isProcessing: this.isProcessing,
            lastCheck: new Date().toISOString()
        };
    }

    resetProcessedFiles() {
        this.processedFiles.clear();
        this.processedHashes.clear();
        console.log('已重置处理器记录');
    }

    stop() {
        console.log('停止YOLO数据处理器...');
        this.isProcessing = false;
    }
}

module.exports = YoloDataProcessor;