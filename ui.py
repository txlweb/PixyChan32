import sys
import json
import requests
from io import BytesIO
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QInputDialog,
    QDialog, QSlider
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt

SERVER = 'http://127.0.0.1:8099'
WIDTH, HEIGHT = 240, 320


def convert_rgb565_to_image(data: bytes) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = []
    for i in range(0, len(data), 2):
        value = (data[i] << 8) | data[i + 1]
        r = (value >> 11) & 0x1F
        g = (value >> 5) & 0x3F
        b = value & 0x1F
        r = (r << 3) | (r >> 2)
        g = (g << 2) | (g >> 4)
        b = (b << 3) | (b >> 2)
        pixels.append((r, g, b))
    img.putdata(pixels)
    return img


class ClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎥 BIN 文件客户端")
        self.resize(900, 600)
        self.all_items = []
        self.frames = []
        self.fps = 10

        layout = QHBoxLayout(self)

        # Left side: list and controls
        left_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 搜索")
        self.search_bar.textChanged.connect(self.search_list)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_bar)
        left_layout.addLayout(search_layout)

        self.listWidget = QListWidget()
        self.listWidget.itemDoubleClicked.connect(self.play_selected_bin)
        left_layout.addWidget(self.listWidget)

        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_download = QPushButton("⬇ 下载")
        self.btn_upload = QPushButton("⬆ 上传")
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addWidget(self.btn_upload)
        left_layout.addLayout(btn_layout)

        layout.addLayout(left_layout, 2)

        # Right side: preview and fps control
        right_layout = QVBoxLayout()
        self.label = QLabel("GIF 预览")
        self.label.setFixedSize(WIDTH, HEIGHT)
        right_layout.addWidget(self.label)

        fps_layout = QVBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setRange(1, 17)
        self.fps_slider.setValue(self.fps)
        self.fps_slider.valueChanged.connect(self.set_fps)
        self.fps_value_label = QLabel(f"当前 FPS: {self.fps}")
        fps_layout.addWidget(self.fps_slider)
        fps_layout.addWidget(self.fps_value_label)
        right_layout.addLayout(fps_layout)

        layout.addLayout(right_layout, 1)

        self.btn_refresh.clicked.connect(self.load_list)
        self.btn_download.clicked.connect(self.download_selected)
        self.btn_upload.clicked.connect(self.upload_bin)

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.frame_idx = 0

        self.load_list()

    def set_fps(self, val):
        self.fps = val
        self.fps_value_label.setText(f"当前 FPS: {self.fps}")
        if self.timer.isActive():
            self.timer.start(1000 // self.fps)

    def load_list(self):
        self.listWidget.clear()
        try:
            res = requests.get(f'{SERVER}/list')
            if res.status_code == 200:
                self.all_items = res.json().get('d', [])
                self.update_display_list(self.all_items)
            else:
                raise Exception("获取列表失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def update_display_list(self, items):
        self.listWidget.clear()
        for item in items:
            # Set "建议FPS" and default to 15 if no FPS is provided
            suggested_fps = item.get('fp', 15)
            desc = f"{item['n']} | 动图: {item['pn']} | 作者: {item['by']} | 简介: {item['in']} | 建议FPS: {suggested_fps}"
            self.listWidget.addItem(desc)

    def search_list(self):
        keyword = self.search_bar.text().lower()
        if not keyword:
            self.update_display_list(self.all_items)
            return
        filtered = [item for item in self.all_items if
                    keyword in item['n'].lower() or
                    keyword in item['pn'].lower() or
                    keyword in item['by'].lower() or
                    keyword in item['in'].lower()]
        self.update_display_list(filtered)

    def download_selected(self):
        item = self.listWidget.currentItem()
        if item:
            filename = item.text().split(' | ')[0]
            try:
                res = requests.get(f'{SERVER}/download/{filename}')
                if res.status_code == 200:
                    path, _ = QFileDialog.getSaveFileName(self, "保存文件", filename)
                    if path:
                        with open(path, 'wb') as f:
                            f.write(res.content)
                        QMessageBox.information(self, "成功", "下载完成")
                else:
                    QMessageBox.warning(self, "错误", "下载失败")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def upload_bin(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择BIN文件", "", "BIN Files (*.bin)")
        if filepath:
            filename = filepath.split('/')[-1]
            pn, ok1 = QInputDialog.getText(self, "动图名", "请输入动图名:")
            if not ok1 or not pn: return
            by, ok2 = QInputDialog.getText(self, "作者", "请输入作者:")
            if not ok2 or not by: return
            info, ok3 = QInputDialog.getText(self, "简介", "请输入简介:")
            if not ok3 or not info: return
            fp, ok4 = QInputDialog.getInt(self, "FPS", "请输入 FPS:", value=self.fps, min=1, max=60)
            if not ok4: return
            ini = {"pn": pn, "by": by, "in": info, "fp": fp}
            try:
                with open(filepath, 'rb') as f:
                    res = requests.post(f'{SERVER}/upload',
                                        files={'file': (filename, f)},
                                        data={'ini': json.dumps(ini)})
                if res.status_code == 200 and res.json().get('r') == 'ok':
                    QMessageBox.information(self, "成功", "上传成功")
                    self.load_list()
                else:
                    QMessageBox.warning(self, "失败", "上传失败")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def play_selected_bin(self, item):
        filename = item.text().split(' | ')[0]
        try:
            res = requests.get(f'{SERVER}/download/{filename}')
            if res.status_code == 200:
                raw_data = res.content
                frame_size = WIDTH * HEIGHT * 2
                self.frames = []
                for i in range(0, len(raw_data), frame_size):
                    chunk = raw_data[i:i + frame_size]
                    if len(chunk) == frame_size:
                        img = convert_rgb565_to_image(chunk)
                        self.frames.append(img)
                self.frame_idx = 0
                if self.frames:
                    self.timer.start(1000 // self.fps)
                else:
                    QMessageBox.warning(self, "错误", "未检测到有效帧")
            else:
                QMessageBox.warning(self, "错误", "下载失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def next_frame(self):
        if not self.frames:
            return
        img = self.frames[self.frame_idx]
        # Resize the image to fit the window size
        qimg = QImage(img.tobytes(), WIDTH, HEIGHT, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qimg).scaled(self.label.size(), Qt.KeepAspectRatio))
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ClientApp()
    window.show()
    sys.exit(app.exec_())
