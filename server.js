const express = require('express');
const mysql = require('mysql2');
const bodyParser = require('body-parser');
const cors = require('cors');
const app = express();
const path = require('path');
const multer = require('multer');
const { exec, spawn } = require('child_process');
const fs = require('fs');
const PORT = 3000;
const nodemailer = require('nodemailer');
const redis = require('redis');
const axios = require('axios');
const FormData = require('form-data');
const bcrypt = require('bcrypt');
const http = require('http');
const { Server } = require('socket.io');

// 引入YOLO数据处理器
const YoloDataProcessor = require('./yolo_data_processor');

// 配置文件上传
const upload = multer({
    dest: 'uploads/',
    limits: { fileSize: 5 * 1024 * 1024 }
});

// 配置分析文件上传
const analysisUpload = multer({
    dest: 'uploads/analysis/',
    limits: { fileSize: 10 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        const allowedTypes = ['application/json', 'image/jpeg', 'image/png', 'image/jpg'];
        if (allowedTypes.includes(file.mimetype) || file.originalname.endsWith('.json')) {
            cb(null, true);
        } else {
            cb(new Error('只允许上传JSON和图片文件'), false);
        }
    }
});

// 设置静态文件目录
app.use(express.static(path.join(__dirname)));
app.use(cors());
app.use(bodyParser.json());

// 创建HTTP服务器和Socket.IO实例
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

app.get('/', (req, res) => {
    res.redirect('../fontend/login_main_page/identity_division.html');
});

// Python Flask应用配置
const PYTHON_APP_PORT = 5000;
const PYTHON_APP_URL = `http://localhost:${PYTHON_APP_PORT}`;
let pythonProcess = null;

// Java OCR服务配置
const JAVA_OCR_PORT = 8080;
const JAVA_OCR_URL = `http://localhost:${JAVA_OCR_PORT}`;
let javaOcrProcess = null;

// 分析服务配置
const ANALYSIS_SERVICE_PORT = 5002;
const ANALYSIS_SERVICE_URL = `http://localhost:${ANALYSIS_SERVICE_PORT}`;
let analysisProcess = null;

const yoloProcessor = new YoloDataProcessor({
    batchOutputDir: './batch_out',
    imagesDir: './batch_out/images',
    jsonDir: './batch_out/json',
    serverUrl: 'http://localhost:3000',
    processInterval: 5000
});

// ==================== 数据库连接 ==================== //

// 主数据库连接
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '123456',
    database: 'user_management_db'
});

// 分析报告数据库连接
const analysis_reports = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '123456',
    database: 'analysis_reports',
    acquireTimeout: 5000,
    timeout: 5000,
    reconnect: true,
    multipleStatements: false
});

// 连接到主数据库
db.connect((err) => {
    if (err) {
        console.error('主数据库连接失败:', err.stack);
        return;
    }
    console.log('Connected to user_management_db database...');
});

// 连接到分析报告数据库
analysis_reports.connect((err) => {
    if (err) {
        console.error('分析报告数据库连接失败:', err);
        createAnalysisDatabase();
    } else {
        console.log('Connected to analysis_reports database...');
        createAnalysisTables();
    }
});

// ==================== 服务启动函数 ==================== //

// 启动Java OCR应用
function startJavaOcrApp() {
    if (javaOcrProcess) {
        console.log('Java OCR应用已在运行中...');
        return;
    }

    console.log('启动Java OCR应用...');
    javaOcrProcess = spawn('java', ['-jar', 'ocr-application.jar'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: __dirname
    });

    javaOcrProcess.stdout.on('data', (data) => {
        console.log(`Java OCR输出: ${data}`);
    });

    javaOcrProcess.stderr.on('data', (data) => {
        console.error(`Java OCR错误: ${data}`);
    });

    javaOcrProcess.on('close', (code) => {
        console.log(`Java OCR应用已关闭，退出代码: ${code}`);
        javaOcrProcess = null;
    });

    javaOcrProcess.on('error', (error) => {
        console.error(`启动Java OCR应用失败: ${error}`);
        javaOcrProcess = null;
    });

    setTimeout(() => {
        checkJavaOcrHealth();
    }, 10000);
}

// 检查Java OCR应用健康状态
async function checkJavaOcrHealth() {
    try {
        const response = await axios.get(`${JAVA_OCR_URL}/actuator/health`);
        console.log('Java OCR应用启动成功，已连接');
        return true;
    } catch (error) {
        console.log('Java OCR应用尚未就绪，等待中...');
        return false;
    }
}

// 启动Python Flask应用
function startPythonApp() {
    if (pythonProcess) {
        console.log('Python应用已在运行中...');
        return;
    }

    console.log('启动Python人脸识别应用...');
    pythonProcess = spawn('python', ['app.py'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: __dirname,
        env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8',  // 强制Python使用UTF-8编码
            PYTHONUNBUFFERED: '1'       // 禁用Python输出缓冲
        }
    });

    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString('utf8');
        console.log(`Python应用输出: ${output}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        const output = data.toString('utf8');
        console.error(`Python应用输出: ${output}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python应用已关闭，退出代码: ${code}`);
        pythonProcess = null;
    });

    pythonProcess.on('error', (error) => {
        console.error(`Python应用: ${error}`);
        pythonProcess = null;
    });

    setTimeout(() => {
        checkPythonAppHealth();
    }, 3000);
}

// 检查Python应用健康状态
async function checkPythonAppHealth() {
    try {
        const response = await axios.get(`${PYTHON_APP_URL}/api/registered_users`);
        console.log('Python应用启动成功，已连接');
        return true;
    } catch (error) {
        console.log('Python应用尚未就绪，等待中...');
        return false;
    }
}

//// 启动分析服务
//function startAnalysisService() {
//    if (analysisProcess) {
//        console.log('分析服务已在运行中...');
//        return;
//    }
//
//    console.log('启动分析服务...');
//    analysisProcess = spawn('python', ['analysis_service.py'], {
//        stdio: ['pipe', 'pipe', 'pipe'],
//        cwd: __dirname,
//        env: {
//            ...process.env,
//            PYTHONIOENCODING: 'utf-8',  // 强制Python使用UTF-8编码
//            PYTHONUNBUFFERED: '1'       // 禁用Python输出缓冲
//        }
//    });
//
//    analysisProcess.stdout.on('data', (data) => {
//        // 确保正确解码UTF-8
//        const output = data.toString('utf8');
//        console.log(`分析服务输出: ${output}`);
//    });
//
//    analysisProcess.stderr.on('data', (data) => {
//        // 确保正确解码UTF-8
//        const output = data.toString('utf8');
//        console.error(`分析服务输出: ${output}`);
//    });
//
//    analysisProcess.on('close', (code) => {
//        console.log(`分析服务已关闭，退出代码: ${code}`);
//        analysisProcess = null;
//    });
//
//    analysisProcess.on('error', (error) => {
//        console.error(`分析服务: ${error}`);
//        analysisProcess = null;
//    });
//
//    setTimeout(() => {
//        checkAnalysisServiceHealth();
//    }, 5000);
//}
//
//// 启动分析服务
//function startJanusService() {
//    if (janusProcess) {
//        console.log('Janus智能分析服务已在运行中...');
//        return;
//    }
//
//    console.log('启动Janus智能分析服务...');
//    janusProcess = spawn('python', ['janus_analysis_service.py'], {
//        stdio: ['pipe', 'pipe', 'pipe'],
//        cwd: __dirname,
//        env: {
//            ...process.env,
//            PYTHONIOENCODING: 'utf-8',
//            PYTHONUNBUFFERED: '1'
//        }
//    });
//
//    janusProcess.stdout.on('data', (data) => {
//        const output = data.toString('utf8');
//        console.log(`Janus服务输出: ${output}`);
//    });
//
//    janusProcess.stderr.on('data', (data) => {
//        const output = data.toString('utf8');
//        console.error(`Janus服务输出: ${output}`);
//    });
//
//    janusProcess.on('close', (code) => {
//        console.log(`Janus服务已关闭，退出代码: ${code}`);
//        janusProcess = null;
//    });
//
//    janusProcess.on('error', (error) => {
//        console.error(`Janus服务: ${error}`);
//        janusProcess = null;
//    });
//
//    setTimeout(() => {
//        checkJanusServiceHealth();
//    }, 5000);
//}

// 检查分析服务健康状态
async function checkAnalysisServiceHealth() {
    try {
        const response = await axios.get(`${ANALYSIS_SERVICE_URL}/api/health`);
        console.log('分析服务启动成功，已连接');
        return true;
    } catch (error) {
        console.log('分析服务尚未就绪，等待中...');
        return false;
    }
}

// 检查分析服务健康状态
async function checkJanusServiceHealth() {
    try {
        const response = await axios.get(`${JANUS_SERVICE_URL}/api/health`);
        console.log('Janus智能分析服务启动成功，已连接');
        return true;
    } catch (error) {
        console.log('Janus智能分析服务尚未就绪，等待中...');
        return false;
    }
}

// ==================== 数据库表创建函数 ==================== //

function createAnalysisDatabase() {
    const createDbConnection = mysql.createConnection({
        host: 'localhost',
        user: 'root',
        password: '123456'
    });

    createDbConnection.connect((err) => {
        if (err) {
            console.error('无法连接到MySQL:', err);
            return;
        }

        const createDbQuery = "CREATE DATABASE IF NOT EXISTS analysis_reports";
        createDbConnection.query(createDbQuery, (err, result) => {
            if (err) {
                console.error('创建数据库失败:', err);
            } else {
                console.log('分析报告数据库创建成功');
                analysis_reports.connect((err) => {
                    if (!err) {
                        console.log('Connected to analysis_reports database...');
                        createAnalysisTables();
                    }
                });
            }
            createDbConnection.end();
        });
    });
}

function createAnalysisTables() {
    const createViolationRecordsTable = `
        CREATE TABLE IF NOT EXISTS violations_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            camera_id VARCHAR(50) NOT NULL,
            detection_timestamp DATETIME NOT NULL,
            violation_data JSON NOT NULL,
            image_path VARCHAR(500),
            total_violations INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_camera_time (camera_id, detection_timestamp),
            INDEX idx_created_at (created_at)
        )
    `;

    const createAnalysisReportsTable = `
        CREATE TABLE IF NOT EXISTS ai_analysis_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            analysis_id VARCHAR(100) UNIQUE NOT NULL,
            violation_record_id INT,
            analysis_type ENUM('janus_model', 'rule_engine', 'multimodal_simulation', 'comprehensive', 'quick', 'risk_focused', 'compliance', 'error') DEFAULT 'rule_engine',
            risk_level ENUM('无风险', '低风险', '中风险', '高风险', '未知') DEFAULT '低风险',
            analysis_result JSON NOT NULL,
            summary TEXT,
            recommendations JSON,
            compliance_score INT DEFAULT 0,
            confidence_score DECIMAL(3,2) DEFAULT 0.80,
            processing_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (violation_record_id) REFERENCES violations_records(id) ON DELETE CASCADE,
            INDEX idx_analysis_id (analysis_id),
            INDEX idx_risk_level (risk_level),
            INDEX idx_created_at (created_at)
        )
    `;

    analysis_reports.query(createViolationRecordsTable, (err, result) => {
        if (err) {
            console.error('创建violations_records表失败:', err);
        } else {
            console.log('violations_records表创建成功');
        }
    });

    analysis_reports.query(createAnalysisReportsTable, (err, result) => {
        if (err) {
            console.error('创建ai_analysis_reports表失败:', err);
        } else {
            console.log('ai_analysis_reports表创建成功');
        }
    });
}

function createViolationTable() {
    const createViolationRecordsTable = `
        CREATE TABLE IF NOT EXISTS violations_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            camera_id VARCHAR(50) NOT NULL,
            detection_timestamp DATETIME NOT NULL,
            violation_data JSON NOT NULL,
            image_path VARCHAR(500),
            total_violations INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_camera_time (camera_id, detection_timestamp),
            INDEX idx_created_at (created_at)
        )
    `;

    analysis_reports.query(createViolationRecordsTable, (err, result) => {
        if (err) {
            console.error('创建violations_records表失败:', err);
        } else {
            console.log('violations_records表创建成功');
        }
    });
}

// ==================== Socket.IO连接处理 ==================== //

io.on('connection', (socket) => {
    console.log('客户端连接:', socket.id);

    socket.join('analysis');

    socket.on('request_realtime_stats', async () => {
        try {
            const response = await axios.get(`${ANALYSIS_SERVICE_URL}/api/analysis/statistics?range=1h`);
            socket.emit('realtime_stats', response.data);
        } catch (error) {
            socket.emit('realtime_stats', { error: '获取实时数据失败' });
        }
    });

    socket.on('request_realtime_alerts', async () => {
        try {
            const response = await axios.get(`${ANALYSIS_SERVICE_URL}/api/analysis/alerts`);
            socket.emit('realtime_alerts', response.data);
        } catch (error) {
            socket.emit('realtime_alerts', { error: '获取预警数据失败' });
        }
    });

    socket.on('disconnect', () => {
        console.log('客户端断开连接:', socket.id);
    });
});

// ==================== 人脸识别相关API路由 ==================== //

app.get('/api/face/registered_users', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_APP_URL}/api/registered_users`);
        res.json(response.data);
    } catch (error) {
        console.error('获取注册用户失败:', error.message);
        res.status(500).json({
            success: false,
            error: '人脸识别服务不可用，请稍后重试'
        });
    }
});

app.post('/api/face/verify', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_APP_URL}/api/verify_face`, req.body, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 30000
        });
        res.json(response.data);
    } catch (error) {
        console.error('人脸验证失败:', error.message);
        res.status(500).json({
            success: false,
            error: '人脸验证服务异常，请稍后重试'
        });
    }
});

app.post('/api/face/reload_database', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_APP_URL}/api/reload_database`);
        res.json(response.data);
    } catch (error) {
        console.error('重新加载数据库失败:', error.message);
        res.status(500).json({
            success: false,
            error: '重新加载数据库失败，请稍后重试'
        });
    }
});

app.get('/api/face/health', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_APP_URL}/api/registered_users`, {
            timeout: 5000
        });
        res.json({
            success: true,
            message: '人脸识别服务正常',
            python_service: 'running'
        });
    } catch (error) {
        res.status(503).json({
            success: false,
            message: '人脸识别服务不可用',
            python_service: 'down',
            error: error.message
        });
    }
});

app.post('/api/face/restart', (req, res) => {
    try {
        if (pythonProcess) {
            pythonProcess.kill();
            pythonProcess = null;
        }

        setTimeout(() => {
            startPythonApp();
        }, 2000);

        res.json({
            success: true,
            message: '人脸识别服务重启中，请稍等...'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: '重启服务失败: ' + error.message
        });
    }
});

// ==================== YOLO违规记录API ==================== //

app.post('/api/violations/save', (req, res) => {
    try {
        const { camera_id, detection_timestamp, violation_data, image_path, total_violations } = req.body;

        if (!camera_id || !detection_timestamp) {
            return res.status(400).json({
                success: false,
                message: '缺少必要参数'
            });
        }

        console.log('📝 接收batch_out数据保存请求:', {
            camera_id,
            total_violations,
            data_type: typeof violation_data
        });

        // 处理violation_data
        let violationDataText;

        if (typeof violation_data === 'string') {
            // 拒绝明显损坏的数据
            if (violation_data.includes('[object Object]') || violation_data === '' || violation_data === 'null') {
                console.error('❌ 拒绝保存损坏的数据');
                return res.status(400).json({
                    success: false,
                    message: '数据格式错误'
                });
            }

            try {
                // 验证JSON格式
                const testParse = JSON.parse(violation_data);
                if (!testParse.violations || typeof testParse.violations !== 'object') {
                    throw new Error('violations字段缺失或格式错误');
                }
                violationDataText = violation_data;
            } catch (parseError) {
                console.error('❌ JSON格式验证失败:', parseError);
                return res.status(400).json({
                    success: false,
                    message: '无效的JSON格式'
                });
            }
        } else if (typeof violation_data === 'object' && violation_data !== null) {
            try {
                // 验证对象结构
                if (!violation_data.violations || typeof violation_data.violations !== 'object') {
                    throw new Error('violations字段缺失或格式错误');
                }

                violationDataText = JSON.stringify(violation_data);
                if (violationDataText.includes('[object Object]')) {
                    throw new Error('序列化包含无效内容');
                }
            } catch (serializeError) {
                console.error('❌ 对象验证失败:', serializeError);
                return res.status(400).json({
                    success: false,
                    message: '对象格式错误'
                });
            }
        } else {
            console.error('❌ 不支持的数据类型');
            return res.status(400).json({
                success: false,
                message: '不支持的数据类型'
            });
        }

        // 最终验证
        try {
            const finalTest = JSON.parse(violationDataText);
            if (!finalTest.violations || typeof finalTest.violations !== 'object') {
                throw new Error('violations字段无效');
            }

            // 确保violations中的值都是有效数字
            for (const [key, value] of Object.entries(finalTest.violations)) {
                if (typeof value !== 'number' || value < 0) {
                    throw new Error(`违规类型 ${key} 的值无效: ${value}`);
                }
            }
        } catch (finalError) {
            console.error('❌ 最终验证失败:', finalError);
            return res.status(400).json({
                success: false,
                message: '数据验证失败: ' + finalError.message
            });
        }

        // 基本去重检查（仅避免完全重复的数据）
        const detectionTime = new Date(detection_timestamp);
        const quickCheckQuery = `
            SELECT id FROM violations_records
            WHERE camera_id = ?
            AND ABS(TIMESTAMPDIFF(SECOND, detection_timestamp, ?)) <= 2
            AND total_violations = ?
            LIMIT 1
        `;

        analysis_reports.query(quickCheckQuery, [
            camera_id,
            detectionTime,
            total_violations || 0
        ], (checkErr, checkResults) => {

            if (checkResults && checkResults.length > 0) {
                console.log(`🔄 跳过重复的记录: ${camera_id}`);
                return res.json({
                    success: true,
                    message: '记录已存在',
                    record_id: checkResults[0].id,
                    duplicate: true
                });
            }

            // 插入数据记录
            const insertQuery = `
                INSERT INTO violations_records
                (camera_id, detection_timestamp, violation_data, total_violations, created_at)
                VALUES (?, ?, ?, ?, NOW())
            `;

            analysis_reports.query({
                sql: insertQuery,
                timeout: 5000
            }, [
                camera_id,
                detectionTime,
                violationDataText,
                total_violations || 0
            ], (err, result) => {

                if (err) {
                    console.error('❌ 插入记录失败:', err.message);
                    return res.status(500).json({
                        success: false,
                        message: '数据库错误: ' + err.message
                    });
                }

                console.log(`✅ 数据保存成功: ID=${result.insertId}, 摄像头=${camera_id}, 违规=${total_violations}次`);

                res.json({
                    success: true,
                    message: '违规记录已保存',
                    record_id: result.insertId
                });
            });
        });

    } catch (error) {
        console.error('❌ 保存违规记录异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器错误: ' + error.message
        });
    }
});

app.get('/api/violations/list', (req, res) => {
    try {
        const page = parseInt(req.query.page) || 1;
        const limit = parseInt(req.query.limit) || 20;
        const offset = (page - 1) * limit;
        const camera_id = req.query.camera_id;

        let whereClause = '';
        let queryParams = [];

        if (camera_id) {
            whereClause = ' WHERE camera_id = ?';
            queryParams.push(camera_id);
        }

        const query = `
            SELECT
                id,
                camera_id,
                detection_timestamp,
                violation_data,
                image_path,
                total_violations,
                created_at
            FROM violations_records
            ${whereClause}
            ORDER BY detection_timestamp DESC
            LIMIT ? OFFSET ?
        `;

        queryParams.push(limit, offset);

        analysis_reports.query(query, queryParams, (err, results) => {
            if (err) {
                console.error('获取违规记录失败:', err);
                return res.status(500).json({
                    success: false,
                    message: '查询失败'
                });
            }

            const processedResults = results.map(record => {
                try {
                    record.violation_data = JSON.parse(record.violation_data);
                } catch (e) {
                    console.error('解析违规数据失败:', e);
                    record.violation_data = {};
                }
                return record;
            });

            const countQuery = `SELECT COUNT(*) as total FROM violations_records${whereClause}`;
            const countParams = camera_id ? [camera_id] : [];

            analysis_reports.query(countQuery, countParams, (countErr, countResult) => {
                if (countErr) {
                    console.error('获取记录总数失败:', countErr);
                    return res.status(500).json({
                        success: false,
                        message: '查询总数失败'
                    });
                }

                const total = countResult[0].total;

                res.json({
                    success: true,
                    data: {
                        records: processedResults,
                        pagination: {
                            current_page: page,
                            per_page: limit,
                            total: total,
                            total_pages: Math.ceil(total / limit)
                        }
                    }
                });
            });
        });

    } catch (error) {
        console.error('获取违规记录异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误'
        });
    }
});

app.get('/api/violations/stats', (req, res) => {
    try {
        const timeRange = req.query.range || '24h';
        let dateCondition = '';

        switch(timeRange) {
            case '1h':
                dateCondition = 'AND detection_timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)';
                break;
            case '24h':
                dateCondition = 'AND detection_timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)';
                break;
            case '7d':
                dateCondition = 'AND detection_timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)';
                break;
            case '30d':
                dateCondition = 'AND detection_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)';
                break;
        }

        const statsQuery = `
            SELECT
                COUNT(*) as total_records,
                SUM(total_violations) as total_violations,
                AVG(total_violations) as avg_violations_per_record,
                COUNT(DISTINCT camera_id) as active_cameras,
                camera_id,
                COUNT(*) as camera_records,
                SUM(total_violations) as camera_violations
            FROM violations_records
            WHERE 1=1 ${dateCondition}
            GROUP BY camera_id
            ORDER BY camera_violations DESC
        `;

        analysis_reports.query(statsQuery, (err, results) => {
            if (err) {
                console.error('获取违规统计失败:', err);
                return res.status(500).json({
                    success: false,
                    message: '统计查询失败'
                });
            }

            const totalStats = results.reduce((acc, row) => {
                acc.total_records += row.total_records;
                acc.total_violations += row.total_violations;
                acc.active_cameras = Math.max(acc.active_cameras, results.length);
                return acc;
            }, { total_records: 0, total_violations: 0, active_cameras: 0 });

            const cameraStats = results.map(row => ({
                camera_id: row.camera_id,
                records: row.camera_records,
                violations: row.camera_violations,
                avg_violations: Math.round(row.camera_violations / row.camera_records * 100) / 100
            }));

            res.json({
                success: true,
                data: {
                    time_range: timeRange,
                    summary: {
                        total_records: totalStats.total_records,
                        total_violations: totalStats.total_violations,
                        active_cameras: totalStats.active_cameras,
                        avg_violations_per_record: totalStats.total_records > 0 ?
                            Math.round(totalStats.total_violations / totalStats.total_records * 100) / 100 : 0
                    },
                    camera_breakdown: cameraStats
                }
            });
        });

    } catch (error) {
        console.error('获取违规统计异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误'
        });
    }
});

app.get('/api/violations/analytics', (req, res) => {
    try {
        const timeRange = req.query.range || '24h';
        const queryAll = req.query.all === 'true';

        console.log(`🔍 获取batch_out数据分析 - 范围: ${timeRange}, 查询所有: ${queryAll}`);

        let dateCondition = '';
        let intervalValue = '';
        let timeField = 'detection_timestamp';

        // 构建时间条件
        if (!queryAll && timeRange !== 'all') {
            switch(timeRange) {
                case '1h':
                    dateCondition = `AND ${timeField} >= DATE_SUB(NOW(), INTERVAL 1 HOUR)`;
                    intervalValue = '1小时';
                    break;
                case '24h':
                    dateCondition = `AND ${timeField} >= DATE_SUB(NOW(), INTERVAL 24 HOUR)`;
                    intervalValue = '24小时';
                    break;
                case '7d':
                    dateCondition = `AND ${timeField} >= DATE_SUB(NOW(), INTERVAL 7 DAY)`;
                    intervalValue = '7天';
                    break;
                case '30d':
                    dateCondition = `AND ${timeField} >= DATE_SUB(NOW(), INTERVAL 30 DAY)`;
                    intervalValue = '30天';
                    break;
                default:
                    dateCondition = '';
                    intervalValue = '所有时间';
            }
        } else {
            dateCondition = '';
            intervalValue = '所有时间';
        }

        console.log(`📅 时间条件: ${dateCondition || '查询所有数据'}`);

        // 执行查询
        const violationTypeQuery = `
            SELECT
                id,
                camera_id,
                detection_timestamp,
                violation_data,
                total_violations,
                created_at
            FROM violations_records
            WHERE 1=1 ${dateCondition}
            ORDER BY ${timeField} DESC, id DESC
        `;

        console.log(`🔍 执行数据查询: ${violationTypeQuery}`);

        analysis_reports.query(violationTypeQuery, (err, results) => {
            if (err) {
                console.error('❌ 获取违规分析失败:', err);
                return res.status(500).json({
                    success: false,
                    message: '查询失败: ' + err.message
                });
            }

            console.log(`📊 数据查询结果数量: ${results.length}`);

            // 处理数据
            const violationsByType = {};
            const violationsByCamera = {};
            const violationsByHour = {};
            const violationsByDate = {};
            let totalViolations = 0;
            const recentRecords = [];

            results.forEach((record, index) => {
                try {
                    // 解析违规数据
                    let violations = {};
                    let violationDataParsed = {};

                    try {
                        violationDataParsed = JSON.parse(record.violation_data || '{}');
                        violations = violationDataParsed.violations || {};

                        // 仅统计有效的违规数据
                        if (index < 5) {
                            console.log(`📝 数据记录 ${record.id} 解析:`, {
                                原始数据长度: record.violation_data ? record.violation_data.length : 0,
                                解析后: violationDataParsed,
                                违规字段: violations,
                                总违规数: record.total_violations
                            });
                        }
                    } catch (jsonError) {
                        console.warn(`⚠️ 跳过无法解析的记录 (ID: ${record.id}):`, jsonError.message);
                        return; // 跳过损坏的数据，不进行修复
                    }

                    const cameraId = record.camera_id;
                    const detectionTime = new Date(record.detection_timestamp);
                    const hour = detectionTime.getHours();
                    const dateStr = detectionTime.toISOString().split('T')[0];

                    // 统计违规类型
                    let recordViolationCount = 0;
                    for (const [type, count] of Object.entries(violations)) {
                        if (typeof count === 'number' && count > 0) {
                            violationsByType[type] = (violationsByType[type] || 0) + count;
                            totalViolations += count;
                            recordViolationCount += count;

                            if (index < 5) {
                                console.log(`📊 违规类型 ${type}: +${count} (总计: ${violationsByType[type]})`);
                            }
                        }
                    }

                    // 按摄像头统计（使用数据库字段确保准确性）
                    const dbViolations = record.total_violations || 0;
                    violationsByCamera[cameraId] = (violationsByCamera[cameraId] || 0) + dbViolations;

                    // 按小时统计
                    violationsByHour[hour] = (violationsByHour[hour] || 0) + dbViolations;

                    // 按日期统计
                    violationsByDate[dateStr] = (violationsByDate[dateStr] || 0) + dbViolations;

                    // 最近记录（前10条）
                    if (recentRecords.length < 10) {
                        recentRecords.push({
                            camera_id: record.camera_id,
                            timestamp: record.detection_timestamp,
                            total_violations: record.total_violations,
                            violations: violations,
                            created_at: record.created_at
                        });
                    }

                } catch (parseError) {
                    console.warn(`⚠️ 跳过解析失败的记录 (ID: ${record.id}):`, parseError.message);
                }
            });

            // 计算最终统计数据
            const dbTotalViolations = results.reduce((sum, record) => sum + (record.total_violations || 0), 0);
            const finalTotalViolations = Math.max(totalViolations, dbTotalViolations);

            console.log(`📊 数据最终统计结果:`);
            console.log(`   查询范围: ${intervalValue}`);
            console.log(`   数据记录: ${results.length}`);
            console.log(`   解析违规总数: ${totalViolations}`);
            console.log(`   数据库字段总数: ${dbTotalViolations}`);
            console.log(`   最终违规总数: ${finalTotalViolations}`);
            console.log(`   违规类型分布:`, violationsByType);
            console.log(`   违规类型数量: ${Object.keys(violationsByType).length}`);

            const responseData = {
                time_range: timeRange,
                summary: {
                    total_violations: finalTotalViolations,
                    total_records: results.length,
                    active_cameras: Object.keys(violationsByCamera).length,
                    query_interval: intervalValue,
                    time_field_used: timeField,
                    data_source: 'real_batch_out_only',
                    query_timestamp: new Date().toISOString()
                },
                violations_by_type: violationsByType,
                violations_by_camera: violationsByCamera,
                violations_by_hour: violationsByHour,
                violations_by_date: violationsByDate,
                recent_records: recentRecords
            };

            console.log(`✅ 数据API响应摘要:`, {
                range: timeRange,
                total_violations: finalTotalViolations,
                total_records: results.length,
                violations_by_type_count: Object.keys(violationsByType).length,
                violations_by_type_sample: Object.keys(violationsByType).slice(0, 3)
            });

            res.json({
                success: true,
                data: responseData
            });
        });

    } catch (error) {
        console.error('❌ 获取违规分析异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误: ' + error.message
        });
    }
});

// 清空数据API
app.post('/api/violations/clear', (req, res) => {
    try {
        const deleteQuery = 'DELETE FROM violations_records';

        analysis_reports.query(deleteQuery, (err, result) => {
            if (err) {
                console.error('清空违规数据失败:', err);
                return res.status(500).json({
                    success: false,
                    message: '清空数据失败: ' + err.message
                });
            }

            console.log(`已清空 ${result.affectedRows} 条违规记录`);

            res.json({
                success: true,
                message: `成功清空 ${result.affectedRows} 条违规记录`,
                cleared_records: result.affectedRows,
                timestamp: new Date().toISOString()
            });
        });

    } catch (error) {
        console.error('清空违规数据异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误: ' + error.message
        });
    }
});

// 数据状态检查API
app.get('/api/violations/status', (req, res) => {
    try {
        const statusQuery = `
            SELECT
                COUNT(*) as total_records,
                SUM(total_violations) as total_violations,
                MIN(detection_timestamp) as earliest_detection,
                MAX(detection_timestamp) as latest_detection,
                MIN(created_at) as earliest_created,
                MAX(created_at) as latest_created,
                COUNT(DISTINCT camera_id) as unique_cameras
            FROM violations_records
        `;

        analysis_reports.query(statusQuery, (err, results) => {
            if (err) {
                console.error('获取数据状态失败:', err);
                return res.status(500).json({
                    success: false,
                    message: '查询状态失败: ' + err.message
                });
            }

            const status = results[0];

            res.json({
                success: true,
                data: {
                    total_records: status.total_records,
                    total_violations: status.total_violations,
                    unique_cameras: status.unique_cameras,
                    time_range: {
                        detection_timestamp: {
                            earliest: status.earliest_detection,
                            latest: status.latest_detection
                        },
                        created_at: {
                            earliest: status.earliest_created,
                            latest: status.latest_created
                        }
                    },
                    current_time: new Date().toISOString(),
                    data_source: 'real_batch_out_only'
                },
                timestamp: new Date().toISOString()
            });
        });

    } catch (error) {
        console.error('获取数据状态异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误: ' + error.message
        });
    }
});

app.post('/api/yolo/process', (req, res) => {
    try {
        const { filename } = req.body;

        if (!filename) {
            return res.status(400).json({
                success: false,
                message: '请提供文件名'
            });
        }

        yoloProcessor.processFile(filename).then(() => {
            res.json({
                success: true,
                message: `文件 ${filename} 处理成功`
            });
        }).catch(error => {
            res.status(500).json({
                success: false,
                message: `文件处理失败: ${error.message}`
            });
        });

    } catch (error) {
        console.error('手动处理YOLO文件异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误'
        });
    }
});

app.get('/api/yolo/status', (req, res) => {
    try {
        const stats = yoloProcessor.getStats();
        res.json({
            success: true,
            status: 'running',
            stats: stats
        });
    } catch (error) {
        console.error('获取YOLO处理器状态异常:', error);
        res.status(500).json({
            success: false,
            message: '服务器内部错误'
        });
    }
});

// ==================== 分析相关API ==================== //

function createDefaultViolationData(totalViolations, cameraId) {
    const violations = createSmartViolations(totalViolations, cameraId, 'default');

    return JSON.stringify({
        violations: violations,
        total_violations: totalViolations,
        camera_id: cameraId,
        timestamp: new Date().toISOString(),
        source: 'default_creation_v2',
        repaired: true,
        repair_timestamp: new Date().toISOString()
    });
}

function createSmartViolations(totalViolations, cameraId, recordId) {
    const violations = {};

    console.log(`🔧 智能重构violations - 总数: ${totalViolations}, 摄像头: ${cameraId}, 记录ID: ${recordId}`);

    if (totalViolations <= 0) {
        return violations;
    }

    // 根据摄像头ID和记录特征推断可能的违规模式
    const cameraPrefix = cameraId.toLowerCase();
    let maskWeight = 0.5;
    let hatWeight = 0.3;
    let phoneWeight = 0.15;
    let uniformWeight = 0.05;

    // 根据摄像头类型调整权重
    if (cameraPrefix.includes('kitchen') || cameraPrefix.includes('cook') || cameraPrefix.includes('28')) {
        maskWeight = 0.6;
        hatWeight = 0.4;
    } else if (cameraPrefix.includes('entrance') || cameraPrefix.includes('front') || cameraPrefix.includes('11')) {
        maskWeight = 0.7;
        hatWeight = 0.2;
        uniformWeight = 0.1;
    } else if (cameraPrefix.includes('34')) {
        maskWeight = 0.5;
        hatWeight = 0.35;
        phoneWeight = 0.15;
    }

    // 按权重分配违规类型 - 使用原始字段名
    if (totalViolations === 1) {
        violations.mask = 1;
    } else if (totalViolations === 2) {
        violations.mask = 1;
        violations.hat = 1;
    } else {
        // 按权重分配
        violations.mask = Math.max(1, Math.round(totalViolations * maskWeight));
        violations.hat = Math.max(0, Math.round(totalViolations * hatWeight));

        if (totalViolations > 3) {
            violations.phone = Math.max(0, Math.round(totalViolations * phoneWeight));
        }

        if (totalViolations > 5) {
            violations.uniform = Math.max(0, Math.round(totalViolations * uniformWeight));
        }

        // 确保总数匹配
        const currentTotal = Object.values(violations).reduce((sum, count) => sum + count, 0);
        if (currentTotal < totalViolations) {
            violations.mask += (totalViolations - currentTotal);
        } else if (currentTotal > totalViolations) {
            // 按比例减少
            const diff = currentTotal - totalViolations;
            if (violations.phone && violations.phone >= diff) {
                violations.phone -= diff;
            } else if (violations.uniform && violations.uniform >= diff) {
                violations.uniform -= diff;
            } else {
                violations.hat = Math.max(0, violations.hat - diff);
            }
        }
    }

    // 移除0值
    Object.keys(violations).forEach(key => {
        if (violations[key] <= 0) {
            delete violations[key];
        }
    });

    console.log(`🔧 智能重构结果:`, violations);
    return violations;
}

// 数据重构函数
function reconstructViolationsFromData(violationData, totalViolations) {
    const violations = {};

    // 尝试从raw_data恢复
    if (violationData.raw_data && violationData.raw_data.violations) {
        for (const [type, count] of Object.entries(violationData.raw_data.violations)) {
            if (typeof count === 'number' && count > 0) {
                violations[type] = count;
            }
        }
    }

    // 尝试从class_numbers推断
    if (Object.keys(violations).length === 0 && violationData.raw_data && violationData.raw_data.class_numbers) {
        const classNumbers = violationData.raw_data.class_numbers;
        const personCount = classNumbers.person || 0;

        if (personCount > (classNumbers.mask || 0)) {
            violations.mask = personCount - (classNumbers.mask || 0);
        }
        if (personCount > (classNumbers.hat || 0)) {
            violations.hat = personCount - (classNumbers.hat || 0);
        }
        if (classNumbers.phone > 0) {
            violations.phone = classNumbers.phone;
        }
        if (classNumbers.cigarette > 0) {
            violations.cigarette = classNumbers.cigarette;
        }
    }

    // 如果仍然没有数据，基于总数创建估算
    if (Object.keys(violations).length === 0 && totalViolations > 0) {
        violations.mask = Math.ceil(totalViolations * 0.6);
        violations.hat = totalViolations - violations.mask;
    }

    console.log('🔧 重构的violations:', violations);
    return violations;
}

function reconstructViolationsFromTotal(totalViolations, cameraId) {
    const violations = {};

    console.log(`🔧 智能重构violations - 总数: ${totalViolations}, 摄像头: ${cameraId}`);

    if (totalViolations <= 0) {
        return violations;
    }

    // 根据摄像头ID推断可能的违规模式
    const cameraPrefix = cameraId.toLowerCase();
    let maskWeight = 0.5;
    let hatWeight = 0.3;
    let uniformWeight = 0.15;
    let phoneWeight = 0.05;

    // 根据摄像头类型调整权重
    if (cameraPrefix.includes('kitchen') || cameraPrefix.includes('cook')) {
        maskWeight = 0.6;
        hatWeight = 0.4;
    } else if (cameraPrefix.includes('entrance') || cameraPrefix.includes('front')) {
        maskWeight = 0.7;
        uniformWeight = 0.3;
    }

    // 按权重分配违规类型
    if (totalViolations === 1) {
        violations.mask = 1;
    } else if (totalViolations === 2) {
        violations.mask = 1;
        violations.hat = 1;
    } else {
        // 按权重分配
        violations.mask = Math.max(1, Math.round(totalViolations * maskWeight));
        violations.hat = Math.max(0, Math.round(totalViolations * hatWeight));

        if (totalViolations > 3) {
            violations.uniform = Math.max(0, Math.round(totalViolations * uniformWeight));
        }

        if (totalViolations > 5) {
            violations.phone = Math.max(0, Math.round(totalViolations * phoneWeight));
        }

        // 确保总数匹配
        const currentTotal = Object.values(violations).reduce((sum, count) => sum + count, 0);
        if (currentTotal < totalViolations) {
            violations.mask += (totalViolations - currentTotal);
        } else if (currentTotal > totalViolations) {
            // 按比例减少
            const diff = currentTotal - totalViolations;
            if (violations.phone >= diff) {
                violations.phone -= diff;
            } else if (violations.uniform >= diff) {
                violations.uniform -= diff;
            } else {
                violations.hat = Math.max(0, violations.hat - diff);
            }
        }
    }

    // 移除0值
    Object.keys(violations).forEach(key => {
        if (violations[key] <= 0) {
            delete violations[key];
        }
    });

    console.log(`🔧 智能重构结果:`, violations);
    return violations;
}

function inferViolationsFromClassNumbers(classNumbers) {
    const violations = {};

    console.log(`🔍 服务器端从class_numbers推断违规:`, classNumbers);

    const personCount = classNumbers.person || 0;
    const maskCount = classNumbers.mask || 0;
    const hatCount = classNumbers.hat || 0;
    const uniformCount = classNumbers.uniform || 0;
    const phoneCount = classNumbers.phone || 0;
    const cigaretteCount = classNumbers.cigarette || 0;
    const mouseCount = classNumbers.mouse || 0;

    // 推断逻辑
    if (personCount > maskCount) {
        violations.mask = personCount - maskCount;
    }
    if (personCount > hatCount) {
        violations.hat = personCount - hatCount;
    }
    if (personCount > uniformCount) {
        violations.uniform = personCount - uniformCount;
    }

    if (phoneCount > 0) {
        violations.phone = phoneCount;
    }
    if (cigaretteCount > 0) {
        violations.cigarette = cigaretteCount;
    }
    if (mouseCount > 0) {
        violations.mouse = mouseCount;
    }

    console.log(`📊 服务器端推断的违规结果:`, violations);
    return violations;
}

// 生成修复建议
function generateRecommendations(formatAnalysis) {
    const recommendations = [];

    if (formatAnalysis.invalid_json > 0) {
        recommendations.push(`发现 ${formatAnalysis.invalid_json} 条记录JSON格式无效，建议运行数据修复`);
    }

    if (formatAnalysis.no_violations > 0) {
        recommendations.push(`发现 ${formatAnalysis.no_violations} 条记录缺少violations详情，建议运行格式修复`);
    }

    if (formatAnalysis.valid_json === formatAnalysis.total_checked && formatAnalysis.has_violations === formatAnalysis.total_checked) {
        recommendations.push('数据格式良好，无需修复');
    }

    return recommendations;
}

// 保存分析结果到数据库
async function saveAnalysisResult(violationRecordId, analysisResult) {
    return new Promise((resolve, reject) => {
        const insertAnalysisQuery = `
            INSERT INTO ai_analysis_reports
            (analysis_id, violation_record_id, analysis_type, risk_level, analysis_result,
             summary, recommendations, compliance_score, confidence_score, processing_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;

        const analysisData = analysisResult.analysis_result || {};
        const summary = analysisData.executive_summary || analysisData.summary || '';
        const recommendations = JSON.stringify(analysisData.recommendations || []);
        const riskLevel = analysisResult.risk_level || '未知';
        const complianceScore = calculateComplianceScore(analysisResult);
        const confidenceScore = analysisData.analysis_metadata?.analysis_confidence || 0.8;
        const processingTime = analysisResult.timestamp || new Date().toISOString();

        analysis_reports.query(insertAnalysisQuery, [
            analysisResult.analysis_id || `analysis_${Date.now()}`,
            violationRecordId,
            analysisResult.analysis_type,
            riskLevel,
            JSON.stringify(analysisData),
            summary,
            recommendations,
            complianceScore,
            confidenceScore,
            processingTime
        ], (err, result) => {
            if (err) {
                console.error('保存分析结果失败:', err);
                reject(err);
            } else {
                console.log('分析结果保存成功');
                resolve(result);
            }
        });
    });
}

// 计算合规分数
function calculateComplianceScore(analysisResult) {
    const riskLevel = analysisResult.risk_level;
    const analysisData = analysisResult.analysis_result || {};

    let baseScore = 70;

    switch(riskLevel) {
        case '高风险': baseScore = 30; break;
        case '中风险': baseScore = 60; break;
        case '低风险': baseScore = 85; break;
        case '无风险': baseScore = 95; break;
    }

    const metadata = analysisData.analysis_metadata;
    if (metadata && metadata.total_violations) {
        const violationPenalty = Math.min(metadata.total_violations * 5, 30);
        baseScore -= violationPenalty;
    }

    return Math.max(0, Math.min(100, baseScore));
}

// ==================== 用户验证相关API ==================== //

// 验证企业管理员是否存在
app.post('/verify_manager', (req, res) => {
    const { username } = req.body;
    if (!username) {
        return res.status(400).json({ error: 'Username is required' });
    }
    const query = "SELECT * FROM Manager WHERE Name = ?";
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ error: 'Database error' });
        }
        res.json({ exists: results.length > 0 });
    });
});

// 验证系统管理员是否存在
app.post('/verify_admin', (req, res) => {
    const { username } = req.body;
    if (!username) {
        return res.status(400).json({ error: 'Username is required' });
    }
    const query = "SELECT * FROM Admin WHERE Name = ?";
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ error: 'Database error' });
        }
        res.json({ exists: results.length > 0 });
    });
});

// 验证访客是否存在
app.post('/verify_visitor', (req, res) => {
    const { username } = req.body;
    if (!username) {
        return res.status(400).json({ error: 'Username is required' });
    }
    const query = "SELECT * FROM Visitor WHERE Name = ?";
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ error: 'Database error' });
        }
        res.json({ exists: results.length > 0 });
    });
});

// 检查用户名是否存在
app.post('/api/check-username', (req, res) => {
    const { username } = req.body;
    if (!username) {
        return res.status(400).json({ success: false, message: '用户名不能为空' });
    }
    if (username.length < 3 || username.length > 20) {
        return res.status(400).json({ success: false, message: '用户名长度应在3-20个字符之间' });
    }

    const queries = [
        'SELECT Name FROM Visitor WHERE Name = ?',
        'SELECT Name FROM Manager WHERE Name = ?',
        'SELECT Name FROM Admin WHERE Name = ?',
    ];

    let userExists = false;
    let completed = 0;

    queries.forEach(query => {
        db.query(query, [username], (err, results) => {
            completed++;
            if (results && results.length > 0) {
                userExists = true;
            }
            if (completed === queries.length) {
                res.json({ success: true, exists: userExists });
            }
        });
    });
});

// ==================== 邮箱验证找回密码相关API ==================== //

// 验证用户邮箱
app.post('/verify-user-email', (req, res) => {
    const { username, email } = req.body;
    if (!username || !email) {
        return res.status(400).json({ success: false, message: '缺少必要参数' });
    }
    const query = "SELECT Name, Email FROM Verification WHERE Name = ?";
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error('Database error:', err);
            return res.status(500).json({ success: false, message: '数据库错误' });
        }
        if (results.length === 0) {
            return res.status(404).json({ success: false, message: '该用户不存在' });
        }
        const storedEmail = results[0].Email;
        if (storedEmail.toLowerCase() === email.toLowerCase()) {
            res.json({ success: true, message: '邮箱验证成功' });
        } else {
            res.status(400).json({ success: false, message: '邮箱地址不正确' });
        }
    });
});

// ==================== 访客注册相关API ==================== //

// 检查重复信息（访客注册时使用）
app.post('/check_duplicates', async (req, res) => {
    try {
        const { name, email, phone } = req.body;

        // 检查用户名
        const checkNameQuery = "SELECT COUNT(*) as count FROM Verification WHERE Name = ?";
        db.query(checkNameQuery, [name], (err, nameResults) => {
            if (err) {
                console.error("检查用户名错误:", err);
                return res.status(500).json({ error: "服务器错误" });
            }

            // 检查邮箱
            const checkEmailQuery = "SELECT COUNT(*) as count FROM Verification WHERE Email = ?";
            db.query(checkEmailQuery, [email], (err, emailResults) => {
                if (err) {
                    console.error("检查邮箱错误:", err);
                    return res.status(500).json({ error: "服务器错误" });
                }

                // 检查手机号
                const checkPhoneQuery = "SELECT COUNT(*) as count FROM Verification WHERE PhoneNumber = ?";
                db.query(checkPhoneQuery, [phone], (err, phoneResults) => {
                    if (err) {
                        console.error("检查手机号错误:", err);
                        return res.status(500).json({ error: "服务器错误" });
                    }

                    res.json({
                        nameExists: nameResults[0].count > 0,
                        emailExists: emailResults[0].count > 0,
                        phoneExists: phoneResults[0].count > 0
                    });
                });
            });
        });
    } catch (error) {
        console.error("检查重复信息错误:", error);
        res.status(500).json({ error: "服务器内部错误" });
    }
});

// 访客注册（完整版本）
app.post('/visitor_register', async (req, res) => {
    try {
        const { name, email, phone, password, email_code, phone_code } = req.body;

        // 验证邮箱验证码
        const emailVerified = await verifyEmailCode(email, email_code);
        if (!emailVerified) {
            return res.status(400).json({ success: false, message: "邮箱验证失败" });
        }

        // 验证手机验证码
        const phoneVerified = await verifyPhoneCode(phone, phone_code);
        if (!phoneVerified) {
            return res.status(400).json({ success: false, message: "手机验证失败" });
        }

        // 再次检查重复
        const nameExistsQuery = "SELECT COUNT(*) as count FROM Verification WHERE Name = ?";
        db.query(nameExistsQuery, [name], (err, results) => {
            if (err || results[0].count > 0) {
                return res.status(400).json({ success: false, message: "用户名已存在" });
            }

            const emailExistsQuery = "SELECT COUNT(*) as count FROM Verification WHERE Email = ?";
            db.query(emailExistsQuery, [email], (err, results) => {
                if (err || results[0].count > 0) {
                    return res.status(400).json({ success: false, message: "邮箱已存在" });
                }

                const phoneExistsQuery = "SELECT COUNT(*) as count FROM Verification WHERE PhoneNumber = ?";
                db.query(phoneExistsQuery, [phone], async (err, results) => {
                    if (err || results[0].count > 0) {
                        return res.status(400).json({ success: false, message: "手机号已存在" });
                    }

                    // 密码哈希
                    const hashedPassword = await bcrypt.hash(password, 10);

                    // 开始事务
                    db.beginTransaction((err) => {
                        if (err) {
                            return res.status(500).json({ success: false, message: "服务器错误" });
                        }

                        // 插入验证表
                        const insertVerificationQuery = "INSERT INTO Verification (Name, Email, PhoneNumber) VALUES (?, ?, ?)";
                        db.query(insertVerificationQuery, [name, email, phone], (err, result) => {
                            if (err) {
                                return db.rollback(() => {
                                    res.status(500).json({ success: false, message: "注册失败" });
                                });
                            }

                            // 插入访客表
                            const insertVisitorQuery = "INSERT INTO Visitor (Name, Password) VALUES (?, ?)";
                            db.query(insertVisitorQuery, [name, hashedPassword], (err, result) => {
                                if (err) {
                                    return db.rollback(() => {
                                        res.status(500).json({ success: false, message: "注册失败" });
                                    });
                                }

                                // 提交事务
                                db.commit((err) => {
                                    if (err) {
                                        return db.rollback(() => {
                                            res.status(500).json({ success: false, message: "注册失败" });
                                        });
                                    }

                                    res.json({ success: true, message: "注册成功" });
                                });
                            });
                        });
                    });
                });
            });
        });
    } catch (error) {
        console.error("注册错误:", error);
        res.status(500).json({ success: false, message: "注册失败" });
    }
});

// 经理注册
app.post('/manager_register', async (req, res) => {
    try {
        const { name, email, phone, password, email_code, phone_code } = req.body;

        // 验证邮箱验证码
        const emailVerified = await verifyEmailCode(email, email_code);
        if (!emailVerified) {
            return res.status(400).json({ success: false, message: "邮箱验证失败" });
        }

        // 验证手机验证码
        const phoneVerified = await verifyPhoneCode(phone, phone_code);
        if (!phoneVerified) {
            return res.status(400).json({ success: false, message: "手机验证失败" });
        }

        // 密码哈希
        const hashedPassword = await bcrypt.hash(password, 10);

        // 开始事务
        db.beginTransaction((err) => {
            if (err) {
                return res.status(500).json({ success: false, message: "服务器错误" });
            }

            // 插入验证表
            const insertVerificationQuery = "INSERT INTO Verification (Name, Email, PhoneNumber) VALUES (?, ?, ?)";
            db.query(insertVerificationQuery, [name, email, phone], (err, result) => {
                if (err) {
                    return db.rollback(() => {
                        res.status(500).json({ success: false, message: "注册失败" });
                    });
                }

                // 插入管理员表（需要企业ID，这里可能需要额外处理）
                const insertManagerQuery = "INSERT INTO Manager (Name, Password) VALUES (?, ?)";
                db.query(insertManagerQuery, [name, hashedPassword], (err, result) => {
                    if (err) {
                        return db.rollback(() => {
                            res.status(500).json({ success: false, message: "注册失败" });
                        });
                    }

                    // 提交事务
                    db.commit((err) => {
                        if (err) {
                            return db.rollback(() => {
                                res.status(500).json({ success: false, message: "注册失败" });
                            });
                        }

                        res.json({ success: true, message: "注册成功" });
                    });
                });
            });
        });
    } catch (error) {
        console.error("管理员注册错误:", error);
        res.status(500).json({ success: false, message: "注册失败" });
    }
});

// ==================== 验证码验证辅助函数 ==================== //

// 邮箱验证码验证函数
async function verifyEmailCode(email, code) {
    try {
        const storedCode = await redisClient.get(`verify_code:${email}`);
        return storedCode === code;
    } catch (error) {
        console.error('邮箱验证出错:', error);
        return false;
    }
}

// 手机验证码验证函数（需要实现SMS服务）
async function verifyPhoneCode(phone, code) {
    try {
        // 这里需要实现真实的SMS验证
        // 现在暂时返回true作为测试
        const storedCode = await redisClient.get(`sms_code:${phone}`);
        return storedCode === code;
    } catch (error) {
        console.error('手机验证出错:', error);
        return false;
    }
}

// ==================== OCR相关完整API ==================== //

// 重启Java OCR服务
app.post('/api/ocr/restart', (req, res) => {
    try {
        if (javaOcrProcess) {
            javaOcrProcess.kill();
            javaOcrProcess = null;
        }
        setTimeout(() => startJavaOcrApp(), 3000);
        res.json({ success: true, message: 'Java OCR服务重启中，请稍等...' });
    } catch (error) {
        res.status(500).json({ success: false, error: '重启OCR服务失败: ' + error.message });
    }
});

// 保存员工验证文件
app.post('/api/save-employee-verification', upload.single('idCard'), async (req, res) => {
    const { userName, enterpriseName, idNumber } = req.body;
    if (!userName || !enterpriseName || !req.file) {
        return res.status(400).json({ success: false, message: '缺少必要参数' });
    }
    try {
        const fileExtension = path.extname(req.file.originalname);
        const sanitizedUserName = userName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
        const sanitizedEnterpriseName = enterpriseName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
        const fileName = `${sanitizedUserName}-${sanitizedEnterpriseName}${fileExtension}`;
        const uploadDir = path.join(__dirname, 'Upload');
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        const filePath = path.join(uploadDir, fileName);
        fs.renameSync(req.file.path, filePath);
        console.log(`员工验证文件已保存: ${fileName}`);
        res.json({
            success: true,
            message: '身份验证信息已保存',
            data: { fileName, serverPath: `./Upload/${fileName}`, userName, enterpriseName }
        });
    } catch (error) {
        console.error('保存员工验证信息失败:', error);
        if (req.file && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }
        res.status(500).json({ success: false, message: '保存失败: ' + error.message });
    }
});

// 企业执照上传与数据库保存
app.post('/upload-license', upload.single('license'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, message: '未上传文件' });
    }
    const filePath = req.file.path;
    const pythonScriptPath = path.join(__dirname, 'enterprise_recognition.py');
    exec(`python "${pythonScriptPath}" "${filePath}"`, (error, stdout, stderr) => {
        fs.unlinkSync(filePath); // 确保删除临时文件
        if (error) {
            console.error('Python脚本执行错误:', error);
            return res.status(500).json({ success: false, message: '图像处理失败' });
        }
        try {
            const result = JSON.parse(stdout);
            if (result.status !== 'success') {
                return res.status(400).json({ success: false, message: result.message });
            }
            const query = "INSERT INTO Enterprise (EID, Name) VALUES (?, ?)";
            db.query(query, [result.eid, result.name], (err, dbResult) => {
                if (err) {
                    console.error('数据库错误:', err);
                    return res.status(500).json({ success: false, message: '数据库存储失败，企业可能已存在' });
                }
                res.json({ success: true, message: '营业执照处理成功', data: result });
            });
        } catch (parseError) {
            console.error('结果解析错误:', parseError, 'Stdout:', stdout);
            res.status(500).json({ success: false, message: '数据处理失败' });
        }
    });
});

// ==================== 分析相关完整API ==================== //

// 分析提交API
app.post('/api/analysis/submit', analysisUpload.fields([
    { name: 'image', maxCount: 1 },
    { name: 'violation_data', maxCount: 1 }
]), async (req, res) => {
    let tempFiles = [];

    try {
        const { violation_data, camera_id } = req.body;

        if (!violation_data) {
            return res.status(400).json({
                success: false,
                message: '缺少违规数据'
            });
        }

        let violationJson;
        try {
            violationJson = JSON.parse(violation_data);
        } catch (e) {
            return res.status(400).json({
                success: false,
                message: '违规数据格式错误'
            });
        }

        let imagePath = null;
        if (req.files && req.files.image && req.files.image[0]) {
            const imageFile = req.files.image[0];
            imagePath = imageFile.path;
            tempFiles.push(imagePath);
        }

        // 保存违规记录到数据库
        const insertViolationQuery = `
            INSERT INTO violations_records
            (camera_id, detection_timestamp, violation_data, image_path, total_violations)
            VALUES (?, ?, ?, ?, ?)
        `;

        const detectionTime = new Date(violationJson.timestamp || new Date());
        const totalViolations = violationJson.total_violations ||
            Object.values(violationJson.violations || {}).reduce((sum, count) => sum + count, 0);

        analysis_reports.query(insertViolationQuery, [
            violationJson.camera_id || camera_id || 'unknown',
            detectionTime,
            JSON.stringify(violationJson),
            imagePath,
            totalViolations
        ], (err, result) => {
            if (err) {
                console.error('保存违规记录失败:', err);
                return res.status(500).json({
                    success: false,
                    message: '保存违规记录失败'
                });
            }

            const violationRecordId = result.insertId;

            // 清理临时文件
            tempFiles.forEach(file => {
                if (fs.existsSync(file)) fs.unlinkSync(file);
            });

            res.json({
                success: true,
                message: '违规数据已保存',
                violation_record_id: violationRecordId
            });
        });

    } catch (error) {
        console.error('提交违规数据失败:', error);

        tempFiles.forEach(file => {
            if (fs.existsSync(file)) {
                fs.unlinkSync(file);
            }
        });

        res.status(500).json({
            success: false,
            message: '提交违规数据失败: ' + error.message
        });
    }
});

//app.post('/api/analysis/intelligent', async (req, res) => {
//    try {
//        const { violation_data, user_query, analysis_type = 'intelligent_analysis' } = req.body;
//
//        if (!violation_data) {
//            return res.status(400).json({
//                success: false,
//                message: '缺少违规数据'
//            });
//        }
//
//        // 调用Janus智能分析服务
//        const analysisPayload = {
//            violation_data: violation_data,
//            user_query: user_query,
//            analysis_type: analysis_type
//        };
//
//        console.log(`🤖 发送智能分析请求: ${user_query || '无查询'}`);
//
//        const response = await axios.post(`${JANUS_SERVICE_URL}/api/analyze`, analysisPayload, {
//            headers: { 'Content-Type': 'application/json' },
//            timeout: 60000
//        });
//
//        if (response.data.success) {
//            res.json({
//                success: true,
//                message: '智能分析完成',
//                analysis_result: response.data,
//                user_query: user_query
//            });
//        } else {
//            throw new Error('智能分析服务返回错误: ' + response.data.error);
//        }
//
//    } catch (error) {
//        console.error('智能分析失败:', error.message);
//        res.status(500).json({
//            success: false,
//            message: '智能分析失败: ' + error.message
//        });
//    }
//});

//// 从记录提交分析
//app.post('/api/analysis/submit-from-record', async (req, res) => {
//    try {
//        const { violation_record_id, analysis_type = 'comprehensive' } = req.body;
//
//        if (!violation_record_id) {
//            return res.status(400).json({
//                success: false,
//                message: '缺少违规记录ID'
//            });
//        }
//
//        // 从数据库获取违规记录
//        const getRecordQuery = `SELECT * FROM violations_records WHERE id = ?`;
//
//        analysis_reports.query(getRecordQuery, [violation_record_id], async (err, results) => {
//            if (err) {
//                console.error('获取违规记录失败:', err);
//                return res.status(500).json({
//                    success: false,
//                    message: '查询违规记录失败'
//                });
//            }
//
//            if (results.length === 0) {
//                return res.status(404).json({
//                    success: false,
//                    message: '违规记录不存在'
//                });
//            }
//
//            const record = results[0];
//            let violationData;
//
//            try {
//                violationData = JSON.parse(record.violation_data);
//            } catch (parseError) {
//                console.error('解析违规数据失败:', parseError);
//                return res.status(400).json({
//                    success: false,
//                    message: '违规数据格式错误'
//                });
//            }
//
//            // 读取图片数据
//            let imageBase64 = null;
//            if (record.image_path && fs.existsSync(record.image_path)) {
//                try {
//                    const imageBuffer = fs.readFileSync(record.image_path);
//                    const mimeType = record.image_path.endsWith('.png') ? 'image/png' : 'image/jpeg';
//                    imageBase64 = `data:${mimeType};base64,${imageBuffer.toString('base64')}`;
//                } catch (imageError) {
//                    console.error('读取图片失败:', imageError);
//                }
//            }
//
//            try {
//                // 调用分析服务
//                const analysisPayload = {
//                    violation_data: violationData,
//                    analysis_type: analysis_type,
//                    violation_record_id: violation_record_id
//                };
//
//                if (imageBase64) {
//                    analysisPayload.image_base64 = imageBase64;
//                }
//
//                const analysisResponse = await axios.post(
//                    `${ANALYSIS_SERVICE_URL}/api/analysis/submit-violation`,
//                    analysisPayload,
//                    {
//                        headers: { 'Content-Type': 'application/json' },
//                        timeout: 60000
//                    }
//                );
//
//                if (analysisResponse.data.success) {
//                    // 保存分析结果
//                    const analysisResult = analysisResponse.data;
//                    await saveAnalysisResult(violation_record_id, analysisResult);
//
//                    res.json({
//                        success: true,
//                        message: '分析完成',
//                        violation_record_id: violation_record_id,
//                        analysis_result: analysisResult,
//                        analysis_type: analysis_type
//                    });
//                } else {
//                    throw new Error('分析服务返回错误: ' + analysisResponse.data.error);
//                }
//
//            } catch (analysisError) {
//                console.error('调用分析服务失败:', analysisError.message);
//                res.status(500).json({
//                    success: false,
//                    message: '分析服务异常',
//                    error: analysisError.message
//                });
//            }
//        });
//
//    } catch (error) {
//        console.error('从记录提交分析异常:', error);
//        res.status(500).json({
//            success: false,
//            message: '服务器内部错误'
//        });
//    }
//});
//
//app.post('/api/analysis/query', async (req, res) => {
//    try {
//        const { query } = req.body;
//
//        if (!query) {
//            return res.status(400).json({
//                success: false,
//                message: '缺少查询内容'
//            });
//        }
//
//        console.log(`💬 处理自然语言查询: ${query}`);
//
//        // 获取最新的违规数据作为上下文
//        const getDataQuery = `
//            SELECT * FROM violations_records
//            ORDER BY detection_timestamp DESC
//            LIMIT 10
//        `;
//
//        analysis_reports.query(getDataQuery, async (err, records) => {
//            let contextData = {
//                violations: {},
//                camera_id: 'system',
//                total_violations: 0,
//                timestamp: new Date().toISOString()
//            };
//
//            if (!err && records.length > 0) {
//                // 聚合最近的违规数据
//                let totalViolations = 0;
//                const aggregatedViolations = {};
//
//                records.forEach(record => {
//                    try {
//                        const violationData = JSON.parse(record.violation_data);
//                        if (violationData.violations) {
//                            for (const [type, count] of Object.entries(violationData.violations)) {
//                                aggregatedViolations[type] = (aggregatedViolations[type] || 0) + count;
//                                totalViolations += count;
//                            }
//                        }
//                    } catch (parseError) {
//                        console.warn('解析违规数据失败:', parseError);
//                    }
//                });
//
//                contextData = {
//                    violations: aggregatedViolations,
//                    camera_id: 'system',
//                    total_violations: totalViolations,
//                    timestamp: new Date().toISOString()
//                };
//            }
//
//            try {
//                // 调用Janus查询API
//                const queryResponse = await axios.post(`${JANUS_SERVICE_URL}/api/query`, {
//                    query: query,
//                    context_data: contextData
//                }, {
//                    headers: { 'Content-Type': 'application/json' },
//                    timeout: 30000
//                });
//
//                res.json(queryResponse.data);
//
//            } catch (queryError) {
//                console.error('查询处理失败:', queryError.message);
//                res.status(500).json({
//                    success: false,
//                    message: '查询处理失败: ' + queryError.message
//                });
//            }
//        });
//
//    } catch (error) {
//        console.error('自然语言查询异常:', error);
//        res.status(500).json({
//            success: false,
//            message: '服务器内部错误'
//        });
//    }
//});

app.post('/api/batch-output/upload', upload.fields([
    { name: 'images', maxCount: 50 },
    { name: 'jsonFiles', maxCount: 50 }
]), async (req, res) => {
    let tempFiles = [];

    try {
        if (!req.files || (!req.files.images && !req.files.jsonFiles)) {
            return res.status(400).json({
                success: false,
                message: '请上传图片或JSON文件'
            });
        }

        // 确保batch_out目录结构存在
        const batchDir = path.join(__dirname, 'batch_out');
        const imagesDir = path.join(batchDir, 'images');
        const jsonDir = path.join(batchDir, 'json');

        [batchDir, imagesDir, jsonDir].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
        });

        let processedCount = 0;

        // 处理图片文件
        if (req.files.images) {
            for (const imageFile of req.files.images) {
                const fileName = imageFile.originalname;
                const targetPath = path.join(imagesDir, fileName);

                fs.renameSync(imageFile.path, targetPath);
                processedCount++;
                tempFiles.push(imageFile.path);
            }
        }

        // 处理JSON文件
        if (req.files.jsonFiles) {
            for (const jsonFile of req.files.jsonFiles) {
                const fileName = jsonFile.originalname;
                const targetPath = path.join(jsonDir, fileName);

                fs.renameSync(jsonFile.path, targetPath);
                processedCount++;
                tempFiles.push(jsonFile.path);
            }
        }

        console.log(`📁 batch_out上传完成: ${processedCount} 个文件`);

        // 触发YOLO处理器处理新文件
        setTimeout(() => {
            yoloProcessor.processNewFiles();
        }, 1000);

        res.json({
            success: true,
            message: `成功上传 ${processedCount} 个文件到batch_out目录`,
            processed_count: processedCount
        });

    } catch (error) {
        console.error('batch_out文件上传失败:', error);

        // 清理临时文件
        tempFiles.forEach(file => {
            if (fs.existsSync(file)) {
                fs.unlinkSync(file);
            }
        });

        res.status(500).json({
            success: false,
            message: '文件上传失败: ' + error.message
        });
    }
});

app.get('/api/batch-output/status', (req, res) => {
    try {
        const batchDir = path.join(__dirname, 'batch_out');
        const imagesDir = path.join(batchDir, 'images');
        const jsonDir = path.join(batchDir, 'json');

        let imageCount = 0;
        let jsonCount = 0;

        if (fs.existsSync(imagesDir)) {
            imageCount = fs.readdirSync(imagesDir).filter(f =>
                f.toLowerCase().endsWith('.jpg') ||
                f.toLowerCase().endsWith('.jpeg') ||
                f.toLowerCase().endsWith('.png')
            ).length;
        }

        if (fs.existsSync(jsonDir)) {
            jsonCount = fs.readdirSync(jsonDir).filter(f =>
                f.toLowerCase().endsWith('.json')
            ).length;
        }

        const processorStats = yoloProcessor.getStats();

        res.json({
            success: true,
            batch_output_status: {
                images_count: imageCount,
                json_count: jsonCount,
                processed_files: processorStats.processedFiles,
                is_processing: processorStats.isProcessing,
                last_check: processorStats.lastCheck
            }
        });

    } catch (error) {
        console.error('获取batch_output状态失败:', error);
        res.status(500).json({
            success: false,
            message: '获取状态失败: ' + error.message
        });
    }
});

// ==================== SMS验证码相关API (需要实现) ==================== //

// 发送短信验证码
app.post('/api/send-sms-code', async (req, res) => {
    const { phone } = req.body;

    if (!phone) {
        return res.status(400).json({ success: false, message: '手机号不能为空' });
    }

    // 验证手机号格式
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(phone)) {
        return res.status(400).json({ success: false, message: '手机号格式不正确' });
    }

    try {
        const code = Math.floor(100000 + Math.random() * 900000).toString();

        // 这里需要实现真实的SMS发送逻辑
        // 暂时将验证码存储到Redis
        await redisClient.setEx(`sms_code:${phone}`, 300, code);

        // 模拟发送成功
        console.log(`SMS验证码已生成 ${phone}: ${code}`);

        res.json({
            success: true,
            message: '验证码已发送到您的手机',
            // 开发环境下可以返回验证码，生产环境应该删除
            dev_code: process.env.NODE_ENV === 'development' ? code : undefined
        });
    } catch (error) {
        console.error('发送短信失败:', error);
        res.status(500).json({ success: false, message: '验证码发送失败，请稍后重试' });
    }
});

// 验证短信验证码
app.post('/api/verify-sms', async (req, res) => {
    const { phone_number, verification_code } = req.body;

    if (!phone_number || !verification_code) {
        return res.status(400).json({
            status: 'error',
            message: '手机号和验证码不能为空'
        });
    }

    try {
        const storedCode = await redisClient.get(`sms_code:${phone_number}`);
        if (!storedCode) {
            return res.status(400).json({
                status: 'error',
                message: '验证码已过期或不存在'
            });
        }

        if (storedCode === verification_code.toString()) {
            await redisClient.del(`sms_code:${phone_number}`);
            res.json({
                status: 'success',
                message: '验证成功'
            });
        } else {
            res.status(400).json({
                status: 'error',
                message: '验证码错误'
            });
        }
    } catch (error) {
        console.error('验证短信失败:', error);
        return res.status(500).json({
            status: 'error',
            message: '验证失败'
        });
    }
});

// ==================== 辅助函数 ==================== //

// 验证用户是否存在于对应的表中
function verifyUserInTable(username, userType, callback) {
    let db;
    let tableName;

    switch(userType) {
        case 'visitor':
            db = visitor;
            tableName = 'visitor';
            break;
        case 'manager':
            db = manager;
            tableName = 'manager';
            break;
        case 'admin':
            db = admin;
            tableName = 'admin';
            break;
        default:
            callback(false);
            return;
    }

    const query = `SELECT Name FROM ${tableName} WHERE Name = ?`;
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error('Database error:', err);
            callback(false);
        } else {
            callback(results.length > 0);
        }
    });
}

// ==================== 静态文件服务 ==================== //

app.use('/fontend', express.static(path.join(__dirname, 'fontend')));
app.use('/uploads/analysis', express.static(path.join(__dirname, 'uploads/analysis')));

// AI分析仪表板路由
app.get('/ai_analysis_dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'fontend/feedback_reports/ai_analysis_dashboard.html'));
});

// ==================== 邮箱验证配置 ==================== //

const qqEmailConfig = {
    service: 'qq',
    host: 'smtp.qq.com',
    port: 587,
    secure: false,
    auth: {
        user: '2701754557@qq.com',
        pass: 'nxpfujhywattddjf'
    }
};

const transporter = nodemailer.createTransport(qqEmailConfig);

transporter.verify((error, success) => {
    if (error) console.error('QQ邮箱配置错误:', error);
    else console.log('QQ邮箱配置成功，可以发送邮件');
});

const redisClient = redis.createClient({
    socket: {
        host: 'localhost',
        port: 6379
    }
});

(async () => {
    try {
        await redisClient.connect();
        console.log('Redis连接成功');
    } catch (err) {
        console.error('Redis连接失败:', err);
    }
})();

redisClient.on('error', (err) => {
    console.error('Redis连接错误:', err);
});

// ==================== 服务器启动 ==================== //

function startAllServices() {
    console.log('\n启动餐饮环境行为检测系统...');
    console.log('功能: 人脸识别、OCR、YOLO数据处理');

    startPythonApp();        // 人脸识别服务
    yoloProcessor.start();   // YOLO数据处理器

    console.log('YOLO数据处理器已启动 (batch_out格式)');
    console.log('WebSocket服务已启用');
    console.log(`违规数据面板: http://localhost:${PORT}/violations_dashboard`);
}

app.get('/intelligent_analysis', (req, res) => {
    res.sendFile(path.join(__dirname, 'fontend/analysis/intelligent_analysis_dashboard.html'));
});

// 启动服务器
server.listen(PORT, () => {
    console.log(`✅ 主服务器启动成功: http://localhost:${PORT}`);
    console.log('邮箱服务已配置:', qqEmailConfig.auth.user);
    console.log('人脸识别服务正在启动...');

    // 启动所有服务
    startAllServices();
});

// ==================== 优雅关闭处理 ==================== //

process.on('SIGINT', async () => {
    console.log('正在关闭服务器...');

    yoloProcessor.stop();
    console.log('YOLO数据处理器已关闭');

    if (pythonProcess) {
        pythonProcess.kill();
        console.log('Python进程已关闭');
    }

    if (javaOcrProcess) {
        javaOcrProcess.kill();
        console.log('Java OCR进程已关闭');
    }

    io.close(() => {
        console.log('WebSocket服务已关闭');
    });

    server.close(() => {
        console.log('HTTP服务器已关闭');
        process.exit(0);
    });
});

process.on('SIGTERM', () => {
    console.log('收到SIGTERM信号，正在优雅关闭...');

    yoloProcessor.stop();

    if (analysisProcess) {
        analysisProcess.kill('SIGTERM');
    }

    io.close(() => {
        console.log('WebSocket服务已关闭');
    });

    server.close(() => {
        console.log('HTTP服务器已关闭');
        process.exit(0);
    });
});

// 全局未捕获异常处理
process.on('uncaughtException', (error) => {
    console.error('未捕获异常:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('未处理的Promise拒绝:', reason);
});

// ==================== 用户登录API ==================== //

// 访客登录
app.post('/visitor_login', (req, res) => {
    const { username, password } = req.body;
    const query = "SELECT * FROM Visitor WHERE Name = ? AND Password = ?";
    db.query(query, [username, password], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "服务器错误" });
        }
        if (results.length === 0) {
            return res.status(401).json({ success: false, message: "用户名或密码错误" });
        }
        return res.json({ success: true, message: "登录成功" });
    });
});

// 企业管理员登录
app.post('/manager_login', (req, res) => {
    const { username, password } = req.body;
    const query = "SELECT * FROM Manager WHERE Name = ? AND Password = ?";
    db.query(query, [username, password], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "服务器错误" });
        }
        if (results.length === 0) {
            return res.status(401).json({ success: false, message: "用户名或密码错误" });
        }
        return res.json({ success: true, message: "登录成功" });
    });
});

// 系统管理员登录
app.post('/admin_login', (req, res) => {
    const { username, password } = req.body;
    const query = "SELECT * FROM Admin WHERE Name = ? AND Password = ?";
    db.query(query, [username, password], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "服务器错误" });
        }
        if (results.length === 0) {
            return res.status(401).json({ success: false, message: "用户名或密码错误" });
        }
        return res.json({ success: true, message: "登录成功" });
    });
});

// ==================== 密码找回与验证 ==================== //

// 获取用户安全问题
app.get('/get-security-questions', (req, res) => {
    const username = req.query.username;
    if (!username) {
        return res.status(400).json({ success: false, message: 'Username is required' });
    }
    const query = "SELECT Problem1, Problem2 FROM Security_Problem WHERE Name = ?";
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error('Error fetching security questions:', err);
            return res.status(500).json({ success: false, message: 'Server error' });
        }
        if (results.length === 0) {
            return res.status(404).json({ success: false, message: 'No security questions found for this user' });
        }
        const questions = [results[0].Problem1, results[0].Problem2].filter(q => q);
        res.json({ success: true, questions });
    });
});

// 验证安全问题答案
app.post('/verify-security-answers', (req, res) => {
    const { username, answers } = req.body;
    if (!username || !answers || !Array.isArray(answers)) {
        return res.status(400).json({ success: false, message: 'Invalid request' });
    }
    const query = "SELECT Answer1, Answer2 FROM Security_Problem WHERE Name = ?";
    db.query(query, [username], (err, results) => {
        if (err) {
            console.error('Error verifying security answers:', err);
            return res.status(500).json({ success: false, message: 'Server error' });
        }
        if (results.length === 0) {
            return res.status(404).json({ success: false, message: 'No answers found for this user' });
        }
        const correctAnswers = [results[0].Answer1, results[0].Answer2].filter(a => a);
        const allCorrect = correctAnswers.every((answer, index) => answer === answers[index]);

        if (allCorrect) {
            res.json({ success: true });
        } else {
            res.json({ success: false, message: 'Incorrect answers' });
        }
    });
});

// ==================== OCR与文件上传 ==================== //

// 身份证OCR识别API
app.post('/api/ocr-idcard', upload.single('idCard'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, message: '未上传文件' });
    }
    try {
        const form = new FormData();
        form.append('idCard', fs.createReadStream(req.file.path), {
            filename: req.file.originalname,
            contentType: req.file.mimetype
        });
        const response = await axios.post(`${JAVA_OCR_URL}/api/ocr/idcard-front`, form, {
            headers: form.getHeaders(),
            timeout: 30000
        });
        fs.unlinkSync(req.file.path);
        res.json(response.data);
    } catch (error) {
        if (req.file && req.file.path && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }
        console.error('调用Java OCR服务失败:', error);
        let errorMessage = '身份证识别服务异常';
        if (error.code === 'ECONNREFUSED') {
            errorMessage = 'OCR服务未启动，请稍后重试';
        } else if (error.response && error.response.data) {
            return res.status(error.response.status || 500).json(error.response.data);
        }
        res.status(500).json({ success: false, message: errorMessage });
    }
});

// 检查Java OCR服务状态
app.get('/api/ocr/health', async (req, res) => {
    try {
        const response = await axios.get(`${JAVA_OCR_URL}/actuator/health`, { timeout: 5000 });
        res.json({ success: true, message: 'Java OCR服务正常', java_service: 'running', details: response.data });
    } catch (error) {
        res.status(503).json({ success: false, message: 'Java OCR服务不可用', java_service: 'down', error: error.message });
    }
});

// ==================== 邮箱验证相关API ==================== //

// 发送验证码
app.post('/api/send-verification-code', async (req, res) => {
    const { email } = req.body;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return res.status(400).json({ success: false, message: '邮箱格式不正确' });
    }
    try {
        const code = Math.floor(100000 + Math.random() * 900000).toString();
        const mailOptions = {
            from: `"餐饮环境监测系统" <${qqEmailConfig.auth.user}>`,
            to: email,
            subject: '【餐饮环境监测系统】邮箱验证码',
            html: `
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>邮箱验证码</h2>
                    <p>您的验证码是: <strong style="font-size: 24px; color: #2563eb;">${code}</strong></p>
                    <p>验证码5分钟内有效，请及时使用。</p>
                </div>
            `
        };
        await transporter.sendMail(mailOptions);
        await redisClient.setEx(`verify_code:${email}`, 300, code);
        res.json({ success: true, message: '验证码已发送到您的邮箱' });
    } catch (error) {
        console.error('发送邮件失败:', error);
        res.status(500).json({ success: false, message: '验证码发送失败，请稍后重试' });
    }
});

// 验证验证码
app.post('/api/verify-code', async (req, res) => {
    const { email, code } = req.body;
    if (!email || !code) {
        return res.status(400).json({ success: false, message: '邮箱和验证码不能为空' });
    }
    try {
        const storedCode = await redisClient.get(`verify_code:${email}`);
        if (!storedCode) {
            return res.status(400).json({ success: false, message: '验证码已过期或不存在' });
        }
        if (storedCode === code.toString()) {
            await redisClient.del(`verify_code:${email}`);
            res.json({ success: true, message: '验证成功' });
        } else {
            res.status(400).json({ success: false, message: '验证码错误' });
        }
    } catch (error) {
        console.error('Redis读取错误:', error);
        return res.status(500).json({ success: false, message: '验证失败' });
    }
});

// ==================== 访客注册API ==================== //

app.post('/api/visitor-register', (req, res) => {
    const { username, email, password } = req.body;

    if (!username || !email || !password) {
        return res.status(400).json({ success: false, message: '所有字段都是必填的' });
    }

    db.beginTransaction((err) => {
        if (err) {
            console.error('开始事务失败:', err);
            return res.status(500).json({ success: false, message: '服务器错误' });
        }

        const insertVisitorQuery = "INSERT INTO Visitor (Name, Password) VALUES (?, ?)";
        db.query(insertVisitorQuery, [username, password], (err, visitorResult) => {
            if (err) {
                console.error('插入Visitor表错误:', err);
                return db.rollback(() => {
                    res.status(400).json({ success: false, message: '注册失败，用户名可能已存在' });
                });
            }

            const insertVerificationQuery = "INSERT INTO Verification (Name, Email) VALUES (?, ?)";
            db.query(insertVerificationQuery, [username, email], (err, verificationResult) => {
                if (err) {
                    console.error('插入Verification表错误:', err);
                    return db.rollback(() => {
                        res.status(400).json({ success: false, message: '注册失败，邮箱可能已存在' });
                    });
                }

                db.commit((err) => {
                    if (err) {
                        console.error('提交事务失败:', err);
                        return db.rollback(() => {
                            res.status(500).json({ success: false, message: '注册失败，请重试' });
                        });
                    }

                    console.log(`用户 ${username} 注册成功`);
                    res.json({ success: true, message: '注册成功' });
                });
            });
        });
    });
});

// ==================== 密码重置功能 ==================== //

app.post('/reset-password', (req, res) => {
    const { username, userType, newPassword } = req.body;

    if (!username || !userType || !newPassword) {
        return res.status(400).json({
            success: false,
            message: '缺少必要参数'
        });
    }

    const passwordRegex = /^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,16}$/;
    if (!passwordRegex.test(newPassword)) {
        return res.status(400).json({
            success: false,
            message: '密码格式不符合要求'
        });
    }

    let tableName;
    switch(userType) {
        case 'visitor':
            tableName = 'Visitor';
            break;
        case 'manager':
            tableName = 'Manager';
            break;
        case 'admin':
            tableName = 'Admin';
            break;
        default:
            return res.status(400).json({
                success: false,
                message: '无效的用户类型'
            });
    }

    const updateQuery = `UPDATE ${tableName} SET Password = ? WHERE Name = ?`;

    db.query(updateQuery, [newPassword, username], (err, results) => {
        if (err) {
            console.error('Database error:', err);
            return res.status(500).json({
                success: false,
                message: '数据库错误'
            });
        }

        if (results.affectedRows === 0) {
            return res.status(404).json({
                success: false,
                message: '用户不存在'
            });
        }

        console.log(`Password reset successful for user: ${username} (${userType})`);
        res.json({
            success: true,
            message: '密码修改成功'
        });
    });
});

// ==================== Janus服务配置（仅用于查询分析） ==================== //

const JANUS_SERVICE_PORT = 5001;
const JANUS_SERVICE_URL = `http://localhost:${JANUS_SERVICE_PORT}`;
let janusProcess = null;

// ==================== 启动Janus查询服务 ==================== //

function startJanusQueryService() {
    if (janusProcess) {
        console.log('Enhanced Janus查询分析服务已在运行中...');
        return;
    }

    console.log('启动Enhanced Janus查询分析服务 (支持Janus-Pro-1B)...');
    janusProcess = spawn('python', ['enhanced_janus_service.py'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: __dirname,
        env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8',
            PYTHONUNBUFFERED: '1',
            TRANSFORMERS_CACHE: './models/.cache',
            HF_HOME: './models/.cache'
        }
    });

    janusProcess.stdout.on('data', (data) => {
        const output = data.toString('utf8');
        console.log(`Enhanced Janus服务输出: ${output}`);
    });

    janusProcess.stderr.on('data', (data) => {
        const output = data.toString('utf8');
        console.error(`Enhanced Janus服务输出: ${output}`);
    });

    janusProcess.on('close', (code) => {
        console.log(`Enhanced Janus服务已关闭，退出代码: ${code}`);
        janusProcess = null;
    });

    janusProcess.on('error', (error) => {
        console.error(`Enhanced Janus服务: ${error}`);
        janusProcess = null;
    });

    setTimeout(() => {
        checkJanusQueryServiceHealth();
    }, 10000); // 增加启动时间，因为要加载模型
}

// 检查Janus查询服务健康状态
async function checkJanusQueryServiceHealth() {
    try {
        const response = await axios.get(`${JANUS_SERVICE_URL}/api/health`, { timeout: 5000 });
        console.log('Janus查询分析服务启动成功，已连接');
        return true;
    } catch (error) {
        console.log('Janus查询分析服务尚未就绪，等待中...');
        return false;
    }
}

// ==================== Janus查询API路由 ==================== //

// 自然语言查询API
app.post('/api/ai-query', async (req, res) => {
    try {
        const { query, time_range_hours = 24 } = req.body;

        if (!query) {
            return res.status(400).json({
                success: false,
                message: '缺少查询内容'
            });
        }

        console.log(`Enhanced AI查询: ${query} (时间范围: ${time_range_hours}小时)`);

        // 准备请求数据
        const requestData = {
            query: query,
            time_range_hours: parseInt(time_range_hours) || 24
        };

        // 如果是0，表示查询所有数据
        if (parseInt(time_range_hours) === 0) {
            requestData.query_all = true;
        }

        // 调用Enhanced Janus查询服务
        const response = await axios.post(`${JANUS_SERVICE_URL}/query`, requestData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 60000 // 增加超时时间，因为Janus-Pro需要更多时间
        });

        res.json(response.data);

    } catch (error) {
        console.error('Enhanced AI查询失败:', error.message);
        res.status(500).json({
            success: false,
            message: 'AI查询失败: ' + error.message
        });
    }
});

app.get('/api/janus-pro/status', async (req, res) => {
    try {
        const response = await axios.get(`${JANUS_SERVICE_URL}/janus/status`, {
            timeout: 5000
        });

        res.json({
            success: true,
            janus_pro_status: response.data,
            service_url: JANUS_SERVICE_URL
        });

    } catch (error) {
        console.error('获取Janus-Pro状态失败:', error.message);
        res.status(503).json({
            success: false,
            message: 'Janus-Pro服务不可用',
            error: error.message
        });
    }
});

app.post('/api/janus-pro/reload', async (req, res) => {
    try {
        // 重启Janus服务以重新加载模型
        if (janusProcess) {
            janusProcess.kill();
            janusProcess = null;
        }

        setTimeout(() => {
            startJanusQueryService();
        }, 2000);

        res.json({
            success: true,
            message: 'Janus-Pro服务重启中，正在重新加载模型...'
        });

    } catch (error) {
        console.error('重新加载Janus-Pro失败:', error);
        res.status(500).json({
            success: false,
            message: '重新加载失败: ' + error.message
        });
    }
});

// 获取数据摘要API
app.get('/api/data-summary', async (req, res) => {
    try {
        const hours = parseInt(req.query.hours) || 24;

        const response = await axios.get(`${JANUS_SERVICE_URL}/api/data-summary?hours=${hours}`, {
            timeout: 10000
        });

        res.json(response.data);

    } catch (error) {
        console.error('获取数据摘要失败:', error.message);
        res.status(500).json({
            success: false,
            message: '获取数据摘要失败: ' + error.message
        });
    }
});

// 检查Janus服务状态API
app.get('/api/janus/health', async (req, res) => {
    try {
        const response = await axios.get(`${JANUS_SERVICE_URL}/api/health`, { timeout: 5000 });
        res.json({
            success: true,
            message: 'Janus查询服务正常',
            service_details: response.data
        });
    } catch (error) {
        res.status(503).json({
            success: false,
            message: 'Janus查询服务不可用',
            error: error.message
        });
    }
});

// 重启Janus服务API
app.post('/api/janus/restart', (req, res) => {
    try {
        if (janusProcess) {
            janusProcess.kill();
            janusProcess = null;
        }

        setTimeout(() => {
            startJanusQueryService();
        }, 2000);

        res.json({
            success: true,
            message: 'Janus查询服务重启中，请稍等...'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: '重启Janus服务失败: ' + error.message
        });
    }
});

// ==================== 修改服务启动函数 ==================== //

function startAllServices() {
    console.log('\n启动餐饮环境行为检测系统...');
    console.log('功能: 人脸识别、OCR、YOLO数据处理、AI查询分析');

    startPythonApp();              // 人脸识别服务
    startJanusQueryService();      // Janus查询分析服务
    yoloProcessor.start();         // YOLO数据处理器

    console.log('YOLO数据处理器已启动 (batch_out格式)');
    console.log('Janus查询分析服务已启动');
    console.log('WebSocket服务已启用');
    console.log(`违规数据面板: http://localhost:${PORT}/violations_dashboard`);
}

// ==================== 违规数据面板路由 ==================== //

app.get('/violations_dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'fontend/violations/violations_dashboard.html'));
});

// ==================== 健康检查API ==================== //

app.get('/api/health', async (req, res) => {
    const status = {
        redis: 'ERROR',
        email: 'ERROR',
        yolo_processor: 'ERROR',
        janus_query_service: 'ERROR',
        janus_pro_model: 'UNKNOWN'
    };

    // 检查Redis
    try {
        await redisClient.ping();
        status.redis = 'OK';
    } catch (err) {
        console.error('Redis健康检查失败:', err);
    }

    // 检查邮件服务
    try {
        await transporter.verify();
        status.email = 'OK';
    } catch (err) {
        console.error('邮件服务健康检查失败:', err);
    }

    // 检查YOLO处理器
    try {
        const yoloStats = yoloProcessor.getStats();
        status.yolo_processor = 'OK';
    } catch (err) {
        console.error('YOLO处理器健康检查失败:', err);
    }

    // 检查Janus查询服务
    try {
        const janusResponse = await axios.get(`${JANUS_SERVICE_URL}/api/health`, { timeout: 3000 });
        status.janus_query_service = 'OK';

        // 检查Janus-Pro模型状态
        if (janusResponse.data.janus_model_status) {
            status.janus_pro_model = janusResponse.data.janus_model_status === 'loaded' ? 'LOADED' : 'NOT_LOADED';
        }
    } catch (err) {
        console.error('Janus查询服务健康检查失败:', err);
    }

    const allOk = Object.values(status).every(s => s === 'OK' || s === 'LOADED');

    res.status(allOk ? 200 : 503).json({
        success: allOk,
        message: allOk ? '所有服务正常' : '部分服务异常',
        services: status,
        janus_pro_available: status.janus_pro_model === 'LOADED',
        timestamp: new Date().toISOString()
    });
});

// ==================== 关闭处理 ==================== //

process.on('SIGINT', async () => {
    console.log('正在关闭服务器...');

    yoloProcessor.stop();
    console.log('YOLO数据处理器已关闭');

    if (pythonProcess) {
        pythonProcess.kill();
        console.log('Python进程已关闭');
    }

    if (janusProcess) {
        janusProcess.kill();
        console.log('Janus查询服务已关闭');
    }

    if (javaOcrProcess) {
        javaOcrProcess.kill();
        console.log('Java OCR进程已关闭');
    }

    io.close(() => {
        console.log('WebSocket服务已关闭');
    });

    server.close(() => {
        console.log('HTTP服务器已关闭');
        process.exit(0);
    });
});

// ==================== 健康检查API ==================== //

app.get('/api/health', async (req, res) => {
    const status = {
        redis: 'ERROR',
        email: 'ERROR',
        yolo_processor: 'ERROR'
    };

    try {
        await redisClient.ping();
        status.redis = 'OK';
    } catch (err) {
        console.error('Redis健康检查失败:', err);
    }

    try {
        await transporter.verify();
        status.email = 'OK';
    } catch (err) {
        console.error('邮件服务健康检查失败:', err);
    }

    try {
        const yoloStats = yoloProcessor.getStats();
        status.yolo_processor = 'OK';
    } catch (err) {
        console.error('YOLO处理器健康检查失败:', err);
    }

    const allOk = Object.values(status).every(s => s === 'OK');

    res.status(allOk ? 200 : 503).json({
        success: allOk,
        message: allOk ? '所有服务正常' : '部分服务异常',
        services: status,
        timestamp: new Date().toISOString()
    });
});

console.log('餐饮环境行为检测系统集成完成');
console.log('主要功能:');
console.log('   - 人脸识别服务 (端口5000)');
console.log('   - OCR识别服务 (端口8080)');
console.log('   - YOLO数据处理器');
console.log('   - Janus AI查询服务 (端口5001)');
console.log('   - WebSocket实时通信');
console.log('   - 违规数据管理与AI分析');

// 导出配置供其他模块使用
module.exports = {
    ANALYSIS_SERVICE_URL,
    saveAnalysisResult,
    calculateComplianceScore,
    yoloProcessor,
    io
};