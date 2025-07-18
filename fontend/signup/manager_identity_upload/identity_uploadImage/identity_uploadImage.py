# identity_uploadImage.py - 改进版上传处理

from flask import Flask, request, jsonify
import os
import uuid
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'id_image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['id_image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # 生成唯一ID和文件名
    upload_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{upload_id}_original{file_ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file.save(filepath)
        return jsonify({
            'status': 'success',
            'upload_id': upload_id,
            'filename': filename
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)