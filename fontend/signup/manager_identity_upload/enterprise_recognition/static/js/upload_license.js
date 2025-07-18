const fileInput = document.getElementById('licenseFile');
const preview = document.getElementById('preview');
const uploadBtn = document.getElementById('uploadBtn');
const resultDiv = document.getElementById('result');

// 预览图片
fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            preview.src = event.target.result;
            preview.style.display = 'block';
            uploadBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }
});

// 拖放功能
const uploadContainer = document.querySelector('.upload-container');
uploadContainer.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = '#007bff';
});

uploadContainer.addEventListener('dragleave', () => {
    uploadContainer.style.borderColor = '#ccc';
});

uploadContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = '#ccc';

    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        const event = new Event('change');
        fileInput.dispatchEvent(event);
    }
});

// 上传处理
uploadBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    uploadBtn.disabled = true;
    uploadBtn.textContent = '处理中...';
    resultDiv.style.display = 'none';

    const formData = new FormData();
    formData.append('license', file);

    try {
        const response = await fetch('/upload-license', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            resultDiv.className = 'success';
            resultDiv.innerHTML = `
                       <h3>处理成功</h3>
                       <p>统一社会信用代码: ${data.data.eid}</p>
                       <p>企业名称: ${data.data.name}</p>
                   `;
        } else {
            resultDiv.className = 'error';
            resultDiv.innerHTML = `
                       <h3>处理失败</h3>
                       <p>${data.message}</p>
                   `;
        }
    } catch (error) {
        resultDiv.className = 'error';
        resultDiv.innerHTML = `
                   <h3>请求失败</h3>
                   <p>${error.message}</p>
               `;
    } finally {
        resultDiv.style.display = 'block';
        uploadBtn.disabled = false;
        uploadBtn.textContent = '上传并验证';
    }
});
