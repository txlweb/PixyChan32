import io
import os
import tempfile
import time
import struct
import requests
from PIL import Image, ImageSequence
import subprocess

# 通用参数
DEFAULT_GIF_PATH = "test.gif"
DEFAULT_BIN_PATH = "animation.bin"
# DEFAULT_UPLOAD_URL_GIF = "http://192.168.1.1/uploada"

DEFAULT_IMAGE_PATH = "test.jpg"
DEFAULT_IMAGE_BIN_PATH = "img.bin"
# DEFAULT_UPLOAD_URL_IMAGE = "http://192.168.1.1/upload"

WIDTH = 240
HEIGHT = 320
MAX_GIF_FRAMES = 96  # Maximum frames allowed for GIF upload


# gif相关，注意RGB565高8位在前
def convert_frame_to_rgb565_gif(frame: Image.Image) -> bytes:
    frame = frame.convert("RGB").resize((WIDTH, HEIGHT))
    data = frame.getdata()
    rgb565_bytes = bytearray()
    for r, g, b in data:
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        rgb565_bytes.append((rgb565 >> 8) & 0xFF)
        rgb565_bytes.append(rgb565 & 0xFF)
    return bytes(rgb565_bytes)


def gif_to_bin(gif_path, bin_path):
    im = Image.open(gif_path)
    frame_count = 0
    with open(bin_path, "wb") as f:
        for i, frame in enumerate(ImageSequence.Iterator(im)):
            if frame_count >= MAX_GIF_FRAMES:
                print(f"Exceeded maximum frame count of {MAX_GIF_FRAMES}. Stopping.")
                break
            print(f"Processing frame {i}")
            rgb565 = convert_frame_to_rgb565_gif(frame)
            f.write(rgb565)
            frame_count += 1


def upload_bin_file_gif(bin_path, url):
    CHUNK_SIZE = 4096
    total_size = os.path.getsize(bin_path)
    uploaded_size = 0
    with open(bin_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            try:
                r = requests.post(url, data=chunk)
                if r.status_code != 200:
                    print("Upload failed:", r.status_code, r.text)
                    break
            except Exception as e:
                print("Upload error:", e)
                break
            uploaded_size += len(chunk)
            progress = (uploaded_size / total_size) * 100
            print(f"Progress: {progress:.2f}% ({uploaded_size}/{total_size} bytes)")
            time.sleep(0.01)
    print("Upload complete.")


# 普通图片相关，注意RGB565低8位在前
def convert_frame_to_rgb565_image(frame: Image.Image) -> bytes:
    frame = frame.convert("RGB").resize((WIDTH, HEIGHT))
    data = frame.getdata()
    rgb565_bytes = bytearray()
    for r, g, b in data:
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        rgb565_bytes.append(rgb565 & 0xFF)
        rgb565_bytes.append((rgb565 >> 8) & 0xFF)
    return bytes(rgb565_bytes)


def upload_bin_file_image(bin_path, url):
    CHUNK_SIZE = 2048
    total_size = os.path.getsize(bin_path)
    uploaded_size = 0
    with open(bin_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            try:
                r = requests.post(url, data=chunk)
                if r.status_code != 200:
                    print("Upload failed:", r.status_code, r.text)
                    break
            except Exception as e:
                print("Upload error:", e)
                break
            uploaded_size += len(chunk)
            progress = (uploaded_size / total_size) * 100
            print(f"Progress: {progress:.2f}% ({uploaded_size}/{total_size} bytes)")
            time.sleep(0.01)
    print("Upload complete.")


def mp4_to_bin(mp4_path, bin_path):
    print(f"Converting MP4 {mp4_path} to .bin...")

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        frame_count = 0

        # 使用 ffmpeg 提取视频帧到临时目录
        command = f"ffmpeg -i {mp4_path} -vf \"fps=10,scale={WIDTH}:{HEIGHT}\" {temp_dir}\\frame_%04d.ppm"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate()  # 等待ffmpeg完成帧提取

        # 获取临时目录中的所有帧文件
        frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.ppm')])

        with open(bin_path, "wb") as f:
            for frame_file in frame_files:
                # 跳过超过最大帧数的帧
                if frame_count >= MAX_GIF_FRAMES:
                    print(f"Exceeded maximum frame count of {MAX_GIF_FRAMES}. Stopping.")
                    break

                frame_path = os.path.join(temp_dir, frame_file)
                print(f"Processing {frame_path}...")

                # 使用 PIL 打开 PPM 图像文件并转换为 RGB565
                im = Image.open(frame_path)
                rgb565_bytes = convert_frame_to_rgb565_gif(im)
                f.write(rgb565_bytes)

                frame_count += 1

    print(f"Conversion complete. {frame_count} frames processed.")


# 对外接口1：上传静态图片
def upload_image(image_path=DEFAULT_IMAGE_PATH, upload_url=""):
    print("Converting image to .bin...")
    im = Image.open(image_path)
    with open(DEFAULT_IMAGE_BIN_PATH, "wb") as f:
        rgb565 = convert_frame_to_rgb565_image(im)
        f.write(rgb565)

    print("Notifying server...")
    try:
        r = requests.get("http://192.168.1.1/", data="a")  # 保持原样
        if r.status_code != 200:
            print("Notification failed:", r.status_code, r.text)
    except Exception as e:
        print("Notification error:", e)

    print("Uploading image...")
    upload_bin_file_image(DEFAULT_IMAGE_BIN_PATH, upload_url)


# 对外接口2：上传动图
def upload_gif(gif_path=DEFAULT_GIF_PATH, upload_url=""):
    print("Converting GIF to .bin...")
    gif_to_bin(gif_path, DEFAULT_BIN_PATH)

    print("Uploading GIF...")
    upload_bin_file_gif(DEFAULT_BIN_PATH, upload_url)


# 对外接口3：上传MP4
def upload_mp4(mp4_path, upload_url):
    print("Converting MP4 to .bin...")
    mp4_to_bin(mp4_path, DEFAULT_BIN_PATH)

    print("Uploading MP4...")
    upload_bin_file_gif(DEFAULT_BIN_PATH, upload_url)


dip = "192.168.1.1"  # 默认设备IP

def select_mode():
    global dip
    print("======= 模式选择 =======")
    print("1. 主模式（设备IP设为192.168.1.1）")
    print("2. 从模式（请输入设备IP）")
    print("========================")
    mode = input("请输入模式选择（1/2）：").strip()
    if mode == "1":
        dip = "192.168.1.1"
    elif mode == "2":
        dip = input("请输入设备IP地址：").strip()
    else:
        print("无效输入，默认设置为主模式。")
        dip = "192.168.1.1"
def configure_slave_wifi():
    ssid = input("请输入需要连接的WiFi SSID：").strip()
    password = input("请输入WiFi密码：").strip()
    url = f"http://{dip}/setwifi?ssid={ssid}&password={password}"
    try:
        response = requests.get(url)
        if response.ok:
            print("WiFi配置成功，如wifi无法连接，会在尝试5次后自动恢复主模式。")
        else:
            print(f"配置失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"请求失败：{e}")

def main_menu():
    while True:
        print("\n========= 主菜单 =========")
        print("当前设备ip：" + dip)
        print("请选择要执行的操作：")
        print("1. 上传静态图片")
        print("2. 上传动图（GIF） MAX SIZE: 96 FRAMES")
        print("3. 上传动图（BIN） MAX SIZE: 14,745,604 字节/14MB")
        print("4. 上传MP4（转换为BIN） MAX SIZE: 14,745,604 字节/14MB")
        print("5. 配置设备WiFi连接 ")
        print("0. 退出")
        print("==========================")

        choice = input("请输入你的选择（0-5）：").strip()

        if choice == "1":
            image_path = input("请输入图片路径：").strip()
            upload_image(image_path,f"http://{dip}/upload")
        elif choice == "2":
            gif_path = input("请输入GIF路径：").strip()
            upload_gif(gif_path,f"http://{dip}/uploada")
        elif choice == "3":
            bin_path = input("请输入BIN路径：").strip()
            upload_bin_file_image(bin_path, f"http://{dip}/uploada")
        elif choice == "4":
            mp4_path = input("请输入MP4路径：").strip()
            upload_mp4(mp4_path,f"http://{dip}/uploada")
        elif choice == "5":
            configure_slave_wifi()
        elif choice == "0":
            print("已退出。")
            break
        else:
            print("无效输入，请重新选择。")

# 程序入口
if __name__ == "__main__":
    select_mode()
    main_menu()


if __name__ == "__main__":
    main_menu()
