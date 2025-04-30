# server.py
from flask import Flask, request, jsonify, send_from_directory
import os
import json
import configparser

app = Flask(__name__)
DIST_DIR = './dists'

@app.route('/list', methods=['GET'])
def list_bins():
    data = []
    for fname in os.listdir(DIST_DIR):
        if fname.endswith('.bin'):
            name = os.path.splitext(fname)[0]
            ini_path = os.path.join(DIST_DIR, f'{name}.ini')
            info = {
                "n": fname,   # 文件名
                "pn": "",     # 动图名称
                "by": "",     # 作者
                "in": "",     # 简介
                "fp": ""      # 帧率
            }
            if os.path.exists(ini_path):
                config = configparser.ConfigParser()
                config.read(ini_path, encoding='utf-8')
                if 'info' in config:
                    info.update({
                        "pn": config['info'].get('pn', ''),
                        "by": config['info'].get('by', ''),
                        "in": config['info'].get('in', ''),
                        "fp": config['info'].get('fp', '')
                    })
            data.append(info)
    return jsonify({"r": "ok", "d": data})


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DIST_DIR, filename, as_attachment=True)


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    ini_data = request.form.get('ini')
    if file and file.filename.endswith('.bin'):
        filepath = os.path.join(DIST_DIR, file.filename)
        file.save(filepath)

        if ini_data:
            try:
                ini_json = json.loads(ini_data)
                name = os.path.splitext(file.filename)[0]
                ini_path = os.path.join(DIST_DIR, f'{name}.ini')
                config = configparser.ConfigParser()
                config['info'] = {
                    "pn": ini_json.get('pn', ''),
                    "by": ini_json.get('by', ''),
                    "in": ini_json.get('in', ''),
                    "fp": str(ini_json.get('fp', ''))
                }
                with open(ini_path, 'w', encoding='utf-8') as f:
                    config.write(f)
            except Exception as e:
                return jsonify({"r": "error", "msg": str(e)}), 400

        return jsonify({"r": "ok"})

    return jsonify({"r": "error", "msg": "Invalid file"}), 400


if __name__ == '__main__':
    os.makedirs(DIST_DIR, exist_ok=True)
    app.run(host='127.0.0.1', port=8099)
