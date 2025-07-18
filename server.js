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
const axios = require('axios'); // 添加axios用于HTTP请求
const FormData = require('form-data');

// 配置文件上传
const upload = multer({
    dest: 'uploads/',
    limits: { fileSize: 5 * 1024 * 1024 } // 限制5MB
});

// 设置静态文件目录（假设文件在项目的根目录下）
app.use(express.static(path.join(__dirname)));
app.use(cors());
app.use(bodyParser.json());

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

    // 等待Java应用启动
    setTimeout(() => {
        checkJavaOcrHealth();
    }, 10000); // Java应用启动可能需要更长时间
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
        cwd: __dirname
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python应用输出: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python应用错误: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python应用已关闭，退出代码: ${code}`);
        pythonProcess = null;
    });

    pythonProcess.on('error', (error) => {
        console.error(`启动Python应用失败: ${error}`);
        pythonProcess = null;
    });

    // 等待Flask应用启动
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

// 在服务器启动时启动Python应用
startPythonApp();

const visitor = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2024379585',
    database: 'visitor'
});

const manager = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2024379585',
    database: 'manager'
});

const admin = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2024379585',
    database: 'admin'
});

const security_question = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2024379585',
    database: 'security_question'
});

const verification = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2024379585',
    database: 'verification'
});

const enterprise = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2024379585',
    database: 'enterprise'
});

// 连接到 'visitor' 数据库
visitor.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Connected to visitor database...');
});

// 连接到 'manager' 数据库
manager.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Connected to manager database...');
});

// 连接到 'admin' 数据库
admin.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Connected to admin database...');
});

// 连接到 'security_question' 数据库
security_question.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Connected to security_question database...');
});

// 连接到 'verification' 数据库
verification.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Connected to verification database...');
});

// 连接到 'enterprise' 数据库
enterprise.connect((err) => {
    if (err) {
        throw err;
    }
    console.log('Connected to enterprise database...');
});


// ==================== 人脸识别相关API路由 ==================== //

// 获取已注册用户列表
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

// 人脸验证
app.post('/api/face/verify', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_APP_URL}/api/verify_face`, req.body, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 30000 // 30秒超时
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

// 重新加载人脸数据库
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

// 检查人脸识别服务状态
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

// 重启人脸识别服务
app.post('/api/face/restart', (req, res) => {
    try {
        // 关闭现有进程
        if (pythonProcess) {
            pythonProcess.kill();
            pythonProcess = null;
        }

        // 延迟重启
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


// -------------------- visitor的登录功能（使用 visitor 数据库） -------------------- //
app.post('/visitor_login', (req, res) => {
    const { username, password } = req.body;

    // 查询数据库中是否有匹配的用户名和密码
    const queryVisitor = "SELECT * FROM visitor WHERE Name = ? AND Password = ?";
    visitor.query(queryVisitor, [username, password], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "服务器错误" });
        }

        // 如果没有找到用户，返回错误信息
        if (results.length === 0) {
            return res.status(401).json({ success: false, message: "用户名或密码错误" });
        }

        // 找到用户，登录成功
        return res.json({ success: true, message: "登录成功" });
    });
});



//-------------------- manager的登录功能（使用 manager 数据库） -------------------- //
app.post('/manager_login', (req, res) => {
    const { username, password } = req.body;

    // 查询数据库中是否有匹配的用户名和密码
    const queryManager = "SELECT * FROM manager WHERE Name = ? AND Password = ?";
    manager.query(queryManager, [username, password], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "服务器错误" });
        }

        // 如果没有找到用户，返回错误信息
        if (results.length === 0) {
            return res.status(401).json({ success: false, message: "用户名或密码错误" });
        }

        // 找到用户，登录成功
        return res.json({ success: true, message: "登录成功" });
    });
});


// -------------------- admin的登录功能（使用 admin 数据库） -------------------- //
app.post('/admin_login', (req, res) => {
    const { username, password } = req.body;

    // 查询数据库中是否有匹配的用户名和密码
    const queryAdmin = "SELECT * FROM admin WHERE Name = ? AND Password = ?";
    admin.query(queryAdmin, [username, password], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "服务器错误" });
        }

        // 如果没有找到用户，返回错误信息
        if (results.length === 0) {
            return res.status(401).json({ success: false, message: "用户名或密码错误" });
        }

        // 找到用户，登录成功
        return res.json({ success: true, message: "登录成功" });
    });
});

//-----------------------------密保更改密码-------------------------------
app.get('/get-security-questions', (req, res) => {
    const username = req.query.username;

    if (!username) {
        return res.status(400).json({ success: false, message: 'Username is required' });
    }

    // 使用正确的表名 Security_Problem 和列名
    const query = "SELECT Problem1, Problem2 FROM SecurityProblem WHERE Name = ?";
    security_question.query(query, [username], (err, results) => {
        if (err) {
            console.error('Error fetching security questions:', err);
            return res.status(500).json({ success: false, message: 'Server error' });
        }

        if (results.length === 0) {
            return res.status(404).json({ success: false, message: 'No security questions found for this user' });
        }

        // 使用正确的列名，只获取2个问题
        const questions = [results[0].Problem1, results[0].Problem2].filter(q => q);
        res.json({ success: true, questions });
    });
});

//---------------------------------------------密保问题验证-----------------------------------------------------
app.post('/verify-security-answers', (req, res) => {
    const { username, answers } = req.body;

    if (!username || !answers || !Array.isArray(answers)) {
        return res.status(400).json({ success: false, message: 'Invalid request' });
    }

    // 使用正确的表名 Security_Problem 和列名
    const query = "SELECT Answer1, Answer2 FROM SecurityProblem WHERE Name = ?";
    security_question.query(query, [username], (err, results) => {
        if (err) {
            console.error('Error verifying security answers:', err);
            return res.status(500).json({ success: false, message: 'Server error' });
        }

        if (results.length === 0) {
            return res.status(404).json({ success: false, message: 'No answers found for this user' });
        }

        // 使用正确的列名，只获取2个答案
        const correctAnswers = [results[0].Answer1, results[0].Answer2].filter(a => a);
        const allCorrect = correctAnswers.every((answer, index) => answer === answers[index]);

        if (allCorrect) {
            res.json({ success: true});
        } else {
            res.json({ success: false, message: 'Incorrect answers' });
        }
    });
});

//-----------------------------------------经理找回密码身份识别------------------------------------
app.post('/verify_manager', (req, res) => {
    const { username } = req.body;

    if (!username) {
        return res.status(400).json({ error: 'Username is required' });
    }

    // 使用已连接的manager数据库
    const query = "SELECT * FROM manager WHERE Name = ?";
    manager.query(query, [username], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ error: 'Database error' });
        }

        if (results.length > 0) {
            res.json({ message: 'User exists' });
        } else {
            res.status(404).json({ error: 'User not found' });
        }
    });
});


//-----------------------------------------工作人员找回密码身份识别------------------------------------
app.post('/verify_admin', (req, res) => {
    const { username } = req.body;

    if (!username) {
        return res.status(400).json({ error: 'Username is required' });
    }

    // 使用已连接的manager数据库
    const query = "SELECT * FROM admin WHERE Name = ?";
    admin.query(query, [username], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ error: 'Database error' });
        }

        if (results.length > 0) {
            res.json({ message: 'User exists' });
        } else {
            res.status(404).json({ error: 'User not found' });
        }
    });
});

//-----------------------------------------游客找回密码身份识别------------------------------------
app.post('/verify_visitor', (req, res) => {
    const { username } = req.body;

    if (!username) {
        return res.status(400).json({ error: 'Username is required' });
    }

    // 使用已连接的manager数据库
    const query = "SELECT * FROM visitor WHERE Name = ?";
    visitor.query(query, [username], (err, results) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ error: 'Database error' });
        }

        if (results.length > 0) {
            res.json({ message: 'User exists' });
        } else {
            res.status(404).json({ error: 'User not found' });
        }
    });
});

//---------------------------------------访客注册-----------------------------------------------

// Check for duplicate name, email, or phone
app.post('/check_duplicates', async (req, res) => {
    try {
        const { name, email, phone } = req.body;

        // Check name in Verification table
        const nameExists = await verification.findOne({ where: { name } });

        // Check email in Verification table
        const emailExists = await verification.findOne({ where: { email } });

        // Check phone in Verification table
        const phoneExists = await verification.findOne({ where: { phoneNumber: phone } });

        res.json({
            nameExists: !!nameExists,
            emailExists: !!emailExists,
            phoneExists: !!phoneExists
        });
    } catch (error) {
        console.error("Error checking duplicates:", error);
        res.status(500).json({ error: "Internal server error" });
    }
});

// Handle registration
app.post('/visitor_register', async (req, res) => {
    try {
        const { name, email, phone, password, email_code, phone_code } = req.body;

        // Verify email code (using your existing verification system)
        const emailVerified = await verifyEmailCode(email, email_code);
        if (!emailVerified) {
            return res.status(400).json({ success: false, message: "Email verification failed" });
        }

        // Verify phone code (using your existing verification system)
        const phoneVerified = await verifyPhoneCode(phone, phone_code);
        if (!phoneVerified) {
            return res.status(400).json({ success: false, message: "Phone verification failed" });
        }

        // Check for duplicates one more time
        const nameExists = await verification.findOne({ where: { name } });
        if (nameExists) {
            return res.status(400).json({ success: false, message: "Name already exists" });
        }

        const emailExists = await verification.findOne({ where: { email } });
        if (emailExists) {
            return res.status(400).json({ success: false, message: "Email already exists" });
        }

        const phoneExists = await verification.findOne({ where: { phoneNumber: phone } });
        if (phoneExists) {
            return res.status(400).json({ success: false, message: "Phone already exists" });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Add to Verification table
        await verification.create({
            name,
            email,
            phoneNumber: phone,
            // any other required fields
        });

        // Add to Visitor table
        await visitor.create({
            name,
            password: hashedPassword,
            // any other required fields
        });

        res.json({ success: true, message: "Registration successful" });
    } catch (error) {
        console.error("Registration error:", error);
        res.status(500).json({ success: false, message: "Registration failed" });
    }
});

//---------------------------------------经理注册-----------------------------------------------
app.post('/manager_register', async (req, res) => {
    try {
        const { name, email, phone, password, email_code, phone_code } = req.body;

        // Verify email code (using your existing verification system)
        const emailVerified = await verifyEmailCode(email, email_code);
        if (!emailVerified) {
            return res.status(400).json({ success: false, message: "Email verification failed" });
        }

        // Verify phone code (using your existing verification system)
        const phoneVerified = await verifyPhoneCode(phone, phone_code);
        if (!phoneVerified) {
            return res.status(400).json({ success: false, message: "Phone verification failed" });
        }

        // Check for duplicates one more time
        const nameExists = await verification.findOne({ where: { name } });
        if (nameExists) {
            return res.status(400).json({ success: false, message: "Name already exists" });
        }

        const emailExists = await verification.findOne({ where: { email } });
        if (emailExists) {
            return res.status(400).json({ success: false, message: "Email already exists" });
        }

        const phoneExists = await verification.findOne({ where: { phoneNumber: phone } });
        if (phoneExists) {
            return res.status(400).json({ success: false, message: "Phone already exists" });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Add to Verification table
        await verification.create({
            name,
            email,
            phoneNumber: phone,
            // any other required fields
        });

        // Add to Visitor table
        await manager.create({
            name,
            password: hashedPassword,
            // any other required fields
        });

        res.json({ success: true, message: "Registration successful" });
    } catch (error) {
        console.error("Registration error:", error);
        res.status(500).json({ success: false, message: "Registration failed" });
    }
});


// 邮箱验证码验证函数
async function verifyEmailCode(email, code) {
    try {
        const response = await fetch('/verify_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                code: code
            })
        });

        const data = await response.json();
        return data.message === "验证成功！";
    } catch (error) {
        console.error('邮箱验证出错:', error);
        return false;
    }
}

// 手机验证码验证函数
async function verifyPhoneCode(phone, code) {
    try {
        const response = await fetch('/verify_sms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                phone_number: phone,
                verification_code: code
            })
        });

        const data = await response.json();
        return data.status === "success";
    } catch (error) {
        console.error('手机验证出错:', error);
        return false;
    }
}

//-------------------------------检查企业是否已经注册-------------------------------
app.post('/api/check-enterprise', (req, res) => {
    const { enterpriseName } = req.body;

    if (!enterpriseName) {
        return res.status(400).json({
            success: false,
            message: '企业名称不能为空'
        });
    }

    // 查询Enterprise表中是否存在该企业名称
    const query = "SELECT Name FROM Enterprise WHERE Name = ?";
    enterprise.query(query, [enterpriseName], (err, results) => {
        if (err) {
            console.error('查询企业错误:', err);
            return res.status(500).json({
                success: false,
                message: '服务器错误'
            });
        }

        if (results.length > 0) {
            // 企业存在
            res.json({
                success: true,
                exists: true
            });
        } else {
            // 企业不存在
            res.json({
                success: true,
                exists: false
            });
        }
    });
});

//--------------------------------------身份证OCR识别API----------------------------------
app.post('/api/ocr-idcard', upload.single('idCard'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({
            success: false,
            message: '未上传文件'
        });
    }

    try {
        // 创建FormData对象发送给Java服务
        const form = new FormData();
        form.append('idCard', req.file.buffer, {
            filename: req.file.originalname,
            contentType: req.file.mimetype
        });

        // 调用Java OCR服务
        const response = await axios.post(`${JAVA_OCR_URL}/api/ocr/idcard-front`, form, {
            headers: {
                ...form.getHeaders(),
                'Content-Type': 'multipart/form-data'
            },
            timeout: 30000 // 30秒超时
        });

        // 删除临时文件
        if (req.file.path && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }

        // 返回Java服务的响应
        res.json(response.data);

    } catch (error) {
        // 删除临时文件
        if (req.file && req.file.path && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }

        console.error('调用Java OCR服务失败:', error);

        let errorMessage = '身份证识别服务异常';
        if (error.code === 'ECONNREFUSED') {
            errorMessage = 'OCR服务未启动，请稍后重试';
        } else if (error.response && error.response.data) {
            // 如果Java服务返回了错误信息，直接传递
            return res.status(error.response.status || 500).json(error.response.data);
        }

        res.status(500).json({
            success: false,
            message: errorMessage
        });
    }
});

// 检查Java OCR服务状态
app.get('/api/ocr/health', async (req, res) => {
    try {
        const response = await axios.get(`${JAVA_OCR_URL}/actuator/health`, {
            timeout: 5000
        });
        res.json({
            success: true,
            message: 'Java OCR服务正常',
            java_service: 'running',
            details: response.data
        });
    } catch (error) {
        res.status(503).json({
            success: false,
            message: 'Java OCR服务不可用',
            java_service: 'down',
            error: error.message
        });
    }
});

//----------------------------------重启Java OCR服务--------------------------------
app.post('/api/ocr/restart', (req, res) => {
    try {
        // 关闭现有进程
        if (javaOcrProcess) {
            javaOcrProcess.kill();
            javaOcrProcess = null;
        }

        // 延迟重启
        setTimeout(() => {
            startJavaOcrApp();
        }, 3000);

        res.json({
            success: true,
            message: 'Java OCR服务重启中，请稍等...'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: '重启OCR服务失败: ' + error.message
        });
    }
});

//--------------------------------------保存员工验证文件----------------------------------
app.post('/api/save-employee-verification', upload.single('idCard'), async (req, res) => {
    const { userName, enterpriseName, idNumber } = req.body;

    if (!userName || !enterpriseName || !req.file) {
        return res.status(400).json({
            success: false,
            message: '缺少必要参数'
        });
    }

    try {
        // 生成文件名
        const fileExtension = req.file.originalname.split('.').pop();
        const sanitizedUserName = userName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
        const sanitizedEnterpriseName = enterpriseName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
        const fileName = `${sanitizedUserName}-${sanitizedEnterpriseName}.${fileExtension}`;

        // 创建Upload目录（如果不存在）
        const uploadDir = path.join(__dirname, 'Upload');
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }

        // 保存文件
        const filePath = path.join(uploadDir, fileName);
        fs.renameSync(req.file.path, filePath);

        // 可选：将验证记录保存到数据库
        // 这里您可以创建一个新表来存储员工验证信息
        // 例如：
        /*
        const insertQuery = "INSERT INTO employee_verification (user_name, enterprise_name, id_number, file_path) VALUES (?, ?, ?, ?)";
        verification.query(insertQuery, [userName, enterpriseName, idNumber, `./Upload/${fileName}`], (err, result) => {
            if (err) console.error('保存验证记录到数据库失败:', err);
        });
        */

        console.log(`员工验证文件已保存: ${fileName}`);

        res.json({
            success: true,
            message: '身份验证信息已保存',
            data: {
                fileName: fileName,
                serverPath: `./Upload/${fileName}`,
                userName: userName,
                enterpriseName: enterpriseName
            }
        });

    } catch (error) {
        console.error('保存员工验证信息失败:', error);

        // 清理临时文件
        if (req.file && fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }

        res.status(500).json({
            success: false,
            message: '保存失败: ' + error.message
        });
    }
});

//--------------------------------经营执照上传与数据库保存--------------------------
// 企业执照上传处理
app.post('/upload-license', upload.single('license'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, message: '未上传文件' });
    }

    const filePath = req.file.path;
    const pythonScriptPath = path.join(__dirname, 'enterprise_recognition.py');

    // 调用Python脚本处理图像
    exec(`python ${pythonScriptPath} "${filePath}"`, (error, stdout, stderr) => {
        try {
            // 删除临时文件
            fs.unlinkSync(filePath);

            if (error) {
                console.error('Python脚本执行错误:', error);
                return res.status(500).json({ success: false, message: '图像处理失败' });
            }

            const result = JSON.parse(stdout);
            if (result.status !== 'success') {
                return res.status(400).json({ success: false, message: result.message });
            }

            // 存入数据库
            const query = "INSERT INTO Enterprise (EID, Name) VALUES (?, ?)";
            enterprise.query(query, [result.eid, result.name], (err, dbResult) => {
                if (err) {
                    console.error('数据库错误:', err);
                    return res.status(500).json({ success: false, message: '数据库存储失败' });
                }

                res.json({
                    success: true,
                    message: '营业执照处理成功',
                    data: {
                        eid: result.eid,
                        name: result.name
                    }
                });
            });
        } catch (parseError) {
            console.error('结果解析错误:', parseError);
            res.status(500).json({ success: false, message: '数据处理失败' });
        }
    });
});

//
//-----------------------------邮箱验证找回密码-------------------------------
app.post('/verify-user-email', (req, res) => {
    const { username, userType, email } = req.body;

    if (!username || !userType || !email) {
        return res.status(400).json({
            success: false,
            message: '缺少必要参数'
        });
    }

    // 查询 verification 表（小写）中的邮箱信息
    const query = "SELECT Name, Email FROM verification WHERE Name = ?";

    verification.query(query, [username], (err, results) => {
        if (err) {
            console.error('Database error:', err);
            return res.status(500).json({
                success: false,
                message: '数据库错误'
            });
        }

        if (results.length === 0) {
            return res.status(404).json({
                success: false,
                message: '该用户不存在'
            });
        }

        // 比较邮箱是否匹配（忽略大小写）
        const storedEmail = results[0].Email;
        if (storedEmail.toLowerCase() === email.toLowerCase()) {
            // 验证用户是否存在于对应的用户类型表中
            verifyUserInTable(username, userType, (exists) => {
                if (exists) {
                    res.json({
                        success: true,
                        message: '邮箱验证成功'
                    });
                } else {
                    res.status(400).json({
                        success: false,
                        message: '用户类型不匹配'
                    });
                }
            });
        } else {
            res.status(400).json({
                success: false,
                message: '邮箱地址不正确，请输入注册时使用的邮箱'
            });
        }
    });
});

// 辅助函数：验证用户是否存在于对应的表中
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

//-----------------------------------------邮箱验证--------------------------------
const qqEmailConfig = {
    service: 'qq',
    host: 'smtp.qq.com',
    port: 587,
    secure: false,
    auth: {
        user: '2024379585@qq.com',   // 替换为您的QQ邮箱
        pass: 'qawerampuxdhjiad'         // 替换为您的16位SMTP授权码
    }
};

// 创建邮件发送器
const transporter = nodemailer.createTransport(qqEmailConfig);

// 验证邮件配置
transporter.verify(function(error, success) {
    if (error) {
        console.error('QQ邮箱配置错误:', error);
        console.log('请检查邮箱账号和授权码是否正确');
    } else {
        console.log('QQ邮箱配置成功，可以发送邮件');
    }
});
// 创建Redis客户端
const redisClient = redis.createClient({
    socket: {
        host: 'localhost',
        port: 6379
    }
});

// 连接Redis
(async () => {
    try {
        await redisClient.connect();
        console.log('Redis连接成功');
    } catch (err) {
        console.error('Redis连接失败:', err);
    }
})();

// Redis错误处理
redisClient.on('error', (err) => {
    console.error('Redis连接错误:', err);
});

// 发送验证码
app.post('/api/send-verification-code', async (req, res) => {
    const { email } = req.body;

    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return res.status(400).json({
            success: false,
            message: '邮箱格式不正确'
        });
    }

    try {
        // 生成6位验证码
        const code = Math.floor(100000 + Math.random() * 900000).toString();

        console.log(`发送验证码 ${code} 到邮箱: ${email}`);

        // 邮件内容
        const mailOptions = {
            from: `"餐饮环境监测系统" <${qqEmailConfig.auth.user}>`,
            to: email,
            subject: '【餐饮环境监测系统】邮箱验证码',
            html: `
                <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
                    <div style="background-color: #667eea; padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0;">餐饮环境监测系统</h1>
                    </div>
                    <div style="background-color: #f9f9f9; padding: 40px;">
                        <h2 style="color: #333; text-align: center;">邮箱验证码</h2>
                        <p style="color: #666; text-align: center; font-size: 16px;">
                            您正在进行邮箱验证，请使用以下验证码：
                        </p>
                        <div style="background-color: white; border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                            <span style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 5px;">${code}</span>
                        </div>
                        <p style="color: #999; text-align: center; font-size: 14px;">
                            验证码有效期为5分钟，请尽快使用。<br>
                            如果这不是您的操作，请忽略此邮件。
                        </p>
                    </div>
                    <div style="background-color: #f0f0f0; padding: 20px; text-align: center;">
                        <p style="color: #999; font-size: 12px; margin: 0;">
                            此邮件由系统自动发送，请勿回复
                        </p>
                    </div>
                </div>
            `,
            text: `您的验证码是：${code}\n\n验证码有效期为5分钟，请尽快使用。`
        };

        // 发送邮件
        await transporter.sendMail(mailOptions);

        // 存储验证码到Redis (5分钟过期) - 使用新版API
        try {
            await redisClient.setEx(`verify_code:${email}`, 300, code);
            console.log('验证码已存储到Redis');
        } catch (redisErr) {
            console.error('Redis存储验证码失败:', redisErr);
            // 即使Redis失败，邮件已发送，可以考虑使用内存存储作为备份
        }

        res.json({
            success: true,
            message: '验证码已发送到您的邮箱'
        });

    } catch (error) {
        console.error('发送邮件失败:', error);

        let errorMessage = '验证码发送失败，请稍后重试';
        if (error.responseCode === 535) {
            errorMessage = '邮箱认证失败，请检查QQ邮箱和授权码';
        }

        res.status(500).json({
            success: false,
            message: errorMessage
        });
    }
});

// 验证验证码
app.post('/api/verify-code', async (req, res) => {
    const { email, code } = req.body;

    if (!email || !code) {
        return res.status(400).json({
            success: false,
            message: '邮箱和验证码不能为空'
        });
    }

    try {
        // 从Redis获取验证码 - 使用新版API
        const storedCode = await redisClient.get(`verify_code:${email}`);

        if (!storedCode) {
            return res.status(400).json({
                success: false,
                message: '验证码已过期或不存在'
            });
        }

        if (storedCode === code.toString()) {
            // 验证成功，删除验证码
            await redisClient.del(`verify_code:${email}`);
            console.log(`邮箱 ${email} 验证成功`);

            res.json({
                success: true,
                message: '验证成功'
            });
        } else {
            res.status(400).json({
                success: false,
                message: '验证码错误'
            });
        }
    } catch (error) {
        console.error('Redis读取错误:', error);
        return res.status(500).json({
            success: false,
            message: '验证失败'
        });
    }
});

// 4. 修改健康检查部分（约在第889行附近）
app.get('/api/health', async (req, res) => {
    const status = {
        redis: 'ERROR',
        email: 'ERROR'
    };

    // 检查Redis - 使用新版API
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

    const allOk = status.redis === 'OK' && status.email === 'OK';

    res.status(allOk ? 200 : 503).json({
        success: allOk,
        message: allOk ? '所有服务正常' : '部分服务异常',
        services: status,
        timestamp: new Date().toISOString()
    });
});

// 健康检查
app.get('/api/health', async (req, res) => {
    const status = {
        redis: 'ERROR',
        email: 'ERROR'
    };

    // 检查Redis
    try {
        await new Promise((resolve, reject) => {
            redisClient.ping((err) => err ? reject(err) : resolve());
        });
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

    const allOk = status.redis === 'OK' && status.email === 'OK';

    res.status(allOk ? 200 : 503).json({
        success: allOk,
        message: allOk ? '所有服务正常' : '部分服务异常',
        services: status,
        timestamp: new Date().toISOString()
    });
});

//-----------------------------密码重置功能-------------------------------
app.post('/reset-password', (req, res) => {
    const { username, userType, newPassword } = req.body;

    // 验证参数
    if (!username || !userType || !newPassword) {
        return res.status(400).json({
            success: false,
            message: '缺少必要参数'
        });
    }

    // 验证密码格式（后端也要验证）
    const passwordRegex = /^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,16}$/;
    if (!passwordRegex.test(newPassword)) {
        return res.status(400).json({
            success: false,
            message: '密码格式不符合要求'
        });
    }

    // 根据 userType 选择对应的数据库连接
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
            return res.status(400).json({
                success: false,
                message: '无效的用户类型'
            });
    }

    // 更新密码
    const updateQuery = `UPDATE ${tableName} SET Password = ? WHERE Name = ?`;

    db.query(updateQuery, [newPassword, username], (err, results) => {
        if (err) {
            console.error('Database error:', err);
            return res.status(500).json({
                success: false,
                message: '数据库错误'
            });
        }

        // 检查是否有记录被更新
        if (results.affectedRows === 0) {
            return res.status(404).json({
                success: false,
                message: '用户不存在'
            });
        }

        // 密码修改成功
        console.log(`Password reset successful for user: ${username} (${userType})`);
        res.json({
            success: true,
            message: '密码修改成功'
        });
    });
});


//--------------------------------------检查用户名是否存在----------------------------------
app.post('/api/check-username', (req, res) => {
    const { username } = req.body;

    console.log('检查用户名请求:', username); // 添加日志以便调试

    if (!username) {
        return res.status(400).json({
            success: false,
            message: '用户名不能为空'
        });
    }

    // 检查用户名长度
    if (username.length < 3 || username.length > 20) {
        return res.status(400).json({
            success: false,
            message: '用户名长度应在3-20个字符之间'
        });
    }

    // 检查用户名是否已存在于visitor表
    const checkVisitorQuery = "SELECT Name FROM visitor WHERE Name = ?";
    visitor.query(checkVisitorQuery, [username], (err, results) => {
        if (err) {
            console.error('检查用户名错误:', err);
            return res.status(500).json({
                success: false,
                message: '服务器错误'
            });
        }

        if (results.length > 0) {
            return res.json({
                success: true,
                exists: true
            });
        }

        // 检查验证表中是否存在该用户名
        const checkVerificationQuery = "SELECT Name FROM verification WHERE Name = ?";
        verification.query(checkVerificationQuery, [username], (err, verificationResults) => {
            if (err) {
                console.error('检查验证表错误:', err);
                return res.status(500).json({
                    success: false,
                    message: '服务器错误'
                });
            }

            res.json({
                success: true,
                exists: verificationResults.length > 0
            });
        });
    });
});

//--------------------------------------访客注册API----------------------------------
app.post('/api/visitor-register', (req, res) => {
    const { username, email, password } = req.body;

    console.log('注册请求:', { username, email }); // 不要记录密码

    // 验证输入参数
    if (!username || !email || !password) {
        return res.status(400).json({
            success: false,
            message: '所有字段都是必填的'
        });
    }

    // 验证用户名长度
    if (username.length < 3 || username.length > 20) {
        return res.status(400).json({
            success: false,
            message: '用户名长度应在3-20个字符之间'
        });
    }

    // 验证密码格式
    const passwordRegex = /^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,16}$/;
    if (!passwordRegex.test(password)) {
        return res.status(400).json({
            success: false,
            message: '密码格式不符合要求'
        });
    }

    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return res.status(400).json({
            success: false,
            message: '邮箱格式不正确'
        });
    }

    // 检查用户名是否已存在（在visitor表中）
    const checkUsernameQuery = "SELECT Name FROM visitor WHERE Name = ?";
    visitor.query(checkUsernameQuery, [username], (err, usernameResults) => {
        if (err) {
            console.error('检查用户名错误:', err);
            return res.status(500).json({
                success: false,
                message: '服务器错误'
            });
        }

        if (usernameResults.length > 0) {
            return res.status(400).json({
                success: false,
                message: '用户名已存在，请选择其他用户名'
            });
        }

        // 检查邮箱是否已存在（在verification表中）
        const checkEmailQuery = "SELECT Email FROM verification WHERE Email = ?";
        verification.query(checkEmailQuery, [email], (err, emailResults) => {
            if (err) {
                console.error('检查邮箱错误:', err);
                return res.status(500).json({
                    success: false,
                    message: '服务器错误'
                });
            }

            if (emailResults.length > 0) {
                return res.status(400).json({
                    success: false,
                    message: '邮箱已被使用，请选择其他邮箱'
                });
            }

            // 开始数据库事务
            visitor.beginTransaction((err) => {
                if (err) {
                    console.error('开始事务失败:', err);
                    return res.status(500).json({
                        success: false,
                        message: '服务器错误'
                    });
                }

                // 插入到visitor表
                const insertVisitorQuery = "INSERT INTO visitor (Name, Password) VALUES (?, ?)";
                visitor.query(insertVisitorQuery, [username, password], (err, visitorResult) => {
                    if (err) {
                        console.error('插入visitor表错误:', err);
                        return visitor.rollback(() => {
                            res.status(500).json({
                                success: false,
                                message: '注册失败，请重试'
                            });
                        });
                    }

                    // 插入到verification表
                    const insertVerificationQuery = "INSERT INTO verification (Name, Email) VALUES (?, ?)";
                    verification.query(insertVerificationQuery, [username, email], (err, verificationResult) => {
                        if (err) {
                            console.error('插入verification表错误:', err);
                            return visitor.rollback(() => {
                                res.status(500).json({
                                    success: false,
                                    message: '注册失败，请重试'
                                });
                            });
                        }

                        // 提交事务
                        visitor.commit((err) => {
                            if (err) {
                                console.error('提交事务失败:', err);
                                return visitor.rollback(() => {
                                    res.status(500).json({
                                        success: false,
                                        message: '注册失败，请重试'
                                    });
                                });
                            }

                            console.log(`用户 ${username} 注册成功`);
                            res.json({
                                success: true,
                                message: '注册成功'
                            });
                        });
                    });
                });
            });
        });
    });
});

//-----------------------------Connect to port--------------------------------
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log('邮箱服务已配置:', qqEmailConfig.auth.user);
  console.log('人脸识别服务正在启动...');
});

//----------------------------Handle disconnect------------------------------
process.on('SIGINT', async () => {
    console.log('正在关闭服务器...');

    // 关闭Redis连接
    if (redisClient.isOpen) {
        await redisClient.quit();
        console.log('Redis连接已关闭');
    }

    // 关闭Python进程
    if (pythonProcess) {
        pythonProcess.kill();
        console.log('Python进程已关闭');
    }

    process.exit(0);
});