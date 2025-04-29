import os
import time
import struct
import requests
from PIL import Image, ImageSequence

# 通用参数
DEFAULT_GIF_PATH = "test.gif"
DEFAULT_BIN_PATH = "animation.bin"
DEFAULT_UPLOAD_URL_GIF = "http://192.168.1.1/uploada"

DEFAULT_IMAGE_PATH = "test.jpg"
DEFAULT_IMAGE_BIN_PATH = "img.bin"
DEFAULT_UPLOAD_URL_IMAGE = "http://192.168.1.1/upload"

WIDTH = 240
HEIGHT = 320

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
    with open(bin_path, "wb") as f:
        for i, frame in enumerate(ImageSequence.Iterator(im)):
            print(f"Processing frame {i}")
            rgb565 = convert_frame_to_rgb565_gif(frame)
            f.write(rgb565)

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

# 对外接口1：上传静态图片
def upload_image(image_path=DEFAULT_IMAGE_PATH, upload_url=DEFAULT_UPLOAD_URL_IMAGE):
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
def upload_gif(gif_path=DEFAULT_GIF_PATH, upload_url=DEFAULT_UPLOAD_URL_GIF):
    print("Converting GIF to .bin...")
    gif_to_bin(gif_path, DEFAULT_BIN_PATH)

    print("Uploading GIF...")
    upload_bin_file_gif(DEFAULT_BIN_PATH, upload_url)

# 命令行用户界面
def main_menu():
    print("==============================")
    print("请选择要执行的操作：")
    print("1. 上传静态图片")
    print("2. 上传动图（GIF）")
    print("0. 退出")
    print("==============================")

    choice = input("请输入你的选择（0/1/2）：").strip()

    if choice == "1":
        image_path = input(f"请输入图片路径 (默认 {DEFAULT_IMAGE_PATH}，直接回车使用默认)：").strip()
        if not image_path:
            image_path = DEFAULT_IMAGE_PATH
        upload_image(image_path)
    elif choice == "2":
        gif_path = input(f"请输入GIF路径 (默认 {DEFAULT_GIF_PATH}，直接回车使用默认)：").strip()
        if not gif_path:
            gif_path = DEFAULT_GIF_PATH
        upload_gif(gif_path)
    elif choice == "0":
        print("已退出。")
    else:
        print("无效输入，请重新运行程序。")

if __name__ == "__main__":
    main_menu()
