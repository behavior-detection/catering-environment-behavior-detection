        // 全局变量存储识别结果
        let licenseData = null;
        let idData = null;
        let uploadedFiles = {};

        // 文件上传处理
        function setupFileUpload(inputId, cardId, progressId, previewId, type) {
            const input = document.getElementById(inputId);
            const card = document.getElementById(cardId);
            const progressBar = document.getElementById(progressId);
            const preview = document.getElementById(previewId);

            // 拖拽功能
            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                card.classList.add('dragover');
            });

            card.addEventListener('dragleave', () => {
                card.classList.remove('dragover');
            });

            card.addEventListener('drop', (e) => {
                e.preventDefault();
                card.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFile(files[0], type);
                }
            });

            input.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFile(e.target.files[0], type);
                }
            });

            function handleFile(file, type) {
                // 文件大小验证
                if (file.size > 10 * 1024 * 1024) {
                    showStatus('文件大小不能超过10MB', 'error');
                    return;
                }

                // 文件类型验证
                const allowedTypes = type === 'license' ?
                    ['image/jpeg', 'image/png', 'application/pdf'] :
                    ['image/jpeg', 'image/png'];

                if (!allowedTypes.includes(file.type)) {
                    showStatus('文件格式不支持', 'error');
                    return;
                }

                uploadedFiles[type] = file;
                showProgress(progressId);
                showPreview(file, previewId);
                card.classList.add('uploaded');

                // 模拟上传进度
                simulateProgress(progressId, () => {
                    // 上传完成后进行OCR识别
                    performOCR(file, type);
                });
            }
        }

        // 显示进度条
        function showProgress(progressId) {
            const progressBar = document.getElementById(progressId);
            progressBar.style.display = 'block';
        }

        // 模拟进度
        function simulateProgress(progressId, callback) {
            const progressFill = document.querySelector(`#${progressId} .progress-fill`);
            let width = 0;
            const interval = setInterval(() => {
                width += Math.random() * 20;
                if (width >= 100) {
                    width = 100;
                    clearInterval(interval);
                    setTimeout(callback, 500);
                }
                progressFill.style.width = width + '%';
            }, 200);
        }

        // 显示预览
        function showPreview(file, previewId) {
            const preview = document.getElementById(previewId);
            preview.style.display = 'block';

            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.innerHTML = `<img src="${e.target.result}" class="preview-img" alt="预览图">`;
                };
                reader.readAsDataURL(file);
            } else {
                preview.innerHTML = `<div style="padding: 20px; text-align: center; color: #666;">📄 ${file.name}</div>`;
            }
        }

        // 模拟OCR识别
        function performOCR(file, type) {
            setTimeout(() => {
                if (type === 'license') {
                    // 模拟营业执照识别结果
                    licenseData = {
                        companyName: '深圳市科技创新有限公司',
                        legalRepresentative: '张三',
                        unifiedSocialCreditCode: '91440300MA5DC6QX9X',
                        registeredCapital: '100万人民币',
                        establishmentDate: '2020-01-15',
                        validationScore: 0.95,
                        isValid: true
                    };
                    displayLicenseResult(licenseData);
                } else {
                    // 模拟身份证识别结果
                    idData = {
                        name: '张三',
                        idNumber: '440300199001011234',
                        address: '广东省深圳市南山区科技园',
                        issueDate: '2015-06-20',
                        validationScore: 0.92,
                        isValid: true
                    };
                    displayIdResult(idData);
                }

                checkSubmitConditions();
            }, 2000);
        }

        // 显示营业执照识别结果
        function displayLicenseResult(data) {
            const resultSection = document.getElementById('resultSection');
            const licenseResult = document.getElementById('licenseResult');
            const licenseInfo = document.getElementById('licenseInfo');
            const licenseValidation = document.getElementById('licenseValidation');

            resultSection.style.display = 'block';
            licenseResult.style.display = 'block';

            licenseInfo.innerHTML = `
                <div class="info-item">
                    <div class="info-label">企业名称</div>
                    <div class="info-value">${data.companyName}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">法定代表人</div>
                    <div class="info-value">${data.legalRepresentative}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">统一社会信用代码</div>
                    <div class="info-value">${data.unifiedSocialCreditCode}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">注册资本</div>
                    <div class="info-value">${data.registeredCapital}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">成立日期</div>
                    <div class="info-value">${data.establishmentDate}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">识别置信度</div>
                    <div class="info-value">${(data.validationScore * 100).toFixed(1)}%</div>
                </div>
            `;

            licenseValidation.className = `validation-status ${data.isValid ? 'valid' : 'invalid'}`;
            licenseValidation.innerHTML = data.isValid ?
                '✅ 营业执照验证通过' :
                '❌ 营业执照验证失败';
        }

        // 显示身份证识别结果
        function displayIdResult(data) {
            const idResult = document.getElementById('idResult');
            const idInfo = document.getElementById('idInfo');
            const idValidation = document.getElementById('idValidation');

            idResult.style.display = 'block';

            idInfo.innerHTML = `
                <div class="info-item">
                    <div class="info-label">姓名</div>
                    <div class="info-value">${data.name}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">身份证号</div>
                    <div class="info-value">${data.idNumber.replace(/(\d{6})\d{8}(\d{4})/, '$1********$2')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">地址</div>
                    <div class="info-value">${data.address}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">签发日期</div>
                    <div class="info-value">${data.issueDate}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">识别置信度</div>
                    <div class="info-value">${(data.validationScore * 100).toFixed(1)}%</div>
                </div>
            `;

            idValidation.className = `validation-status ${data.isValid ? 'valid' : 'invalid'}`;
            idValidation.innerHTML = data.isValid ?
                '✅ 身份证验证通过' :
                '❌ 身份证验证失败';
        }

        // 检查提交条件
        function checkSubmitConditions() {
            const submitBtn = document.getElementById('submitBtn');

            if (licenseData && idData && licenseData.isValid && idData.isValid) {
                // 验证法定代表人姓名是否匹配
                if (licenseData.legalRepresentative === idData.name) {
                    submitBtn.disabled = false;
                    showStatus('✅ 所有验证通过，可以提交！', 'success');
                } else {
                    submitBtn.disabled = true;
                    showStatus('❌ 法定代表人姓名与身份证姓名不匹配', 'error');
                }
            } else {
                submitBtn.disabled = true;
                if (licenseData && idData) {
                    showStatus('❌ 文件验证失败，请重新上传', 'error');
                }
            }
        }

        // 处理提交
        function handleSubmit() {
            if (!licenseData || !idData || !licenseData.isValid || !idData.isValid) {
                showStatus('请确保所有文件已上传并验证通过', 'error');
                return;
            }

            if (licenseData.legalRepresentative !== idData.name) {
                showStatus('法定代表人姓名与身份证姓名不匹配', 'error');
                return;
            }

            const submitBtn = document.getElementById('submitBtn');
            submitBtn.innerHTML = '<div class="loading"></div>正在创建档案...';
            submitBtn.disabled = true;

            // 模拟文件处理
            setTimeout(() => {
                const folderName = `${idData.name}-${licenseData.unifiedSocialCreditCode}`;

                // 创建文件包并下载（模拟文件系统操作）
                createFilePackage(folderName);

                submitBtn.innerHTML = '提交并创建档案';
                submitBtn.disabled = false;
                showStatus(`✅ 档案创建成功！文件夹名称：${folderName}`, 'success');
            }, 3000);
        }

        // 创建文件包（模拟文件系统操作）
        function createFilePackage(folderName) {
            // 在实际应用中，这里应该调用后端API来创建文件夹并保存文件
            // 这里我们模拟通过创建ZIP文件的方式

            const fileInfo = {
                folderName: folderName,
                files: [
                    {
                        name: '营业执照.jpg',
                        type: uploadedFiles.license?.type || 'image/jpeg',
                        size: uploadedFiles.license?.size || 0
                    },
                    {
                        name: '法定代表人身份证.jpg',
                        type: uploadedFiles.id?.type || 'image/jpeg',
                        size: uploadedFiles.id?.size || 0
                    }
                ],
                metadata: {
                    companyName: licenseData.companyName,
                    legalRepresentative: licenseData.legalRepresentative,
                    unifiedSocialCreditCode: licenseData.unifiedSocialCreditCode,
                    idNumber: idData.idNumber,
                    createTime: new Date().toISOString()
                }
            };

            // 创建信息文件并下载
            const blob = new Blob([JSON.stringify(fileInfo, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${folderName}-档案信息.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            console.log('文件包创建完成:', fileInfo);
        }

        // 显示状态消息
        function showStatus(message, type) {
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.textContent = message;
            statusMessage.className = `status-message ${type}`;
            statusMessage.style.display = 'block';

            setTimeout(() => {
                statusMessage.style.display = 'none';
            }, 5000);
        }

        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            setupFileUpload('licenseInput', 'licenseCard', 'licenseProgress', 'licensePreview', 'license');
            setupFileUpload('idInput', 'idCard', 'idProgress', 'idPreview', 'id');
        });
