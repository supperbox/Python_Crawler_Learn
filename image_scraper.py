import os
import requests
from bs4 import BeautifulSoup

# 目标网页地址
URL = "https://example.com"  # 替换为目标地址
OUTPUT_DIR = "f:\\Python_Crawler_Learn\\images"
CSV_FILE = "f:\\Python_Crawler_Learn\\output\\results.csv"

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_image(img_url, save_path):
    try:
        response = requests.get(img_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded: {img_url}")
            return True
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")
    return False

def scrape_images(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    img_tags = soup.find_all("img")
    with open(CSV_FILE, "a") as csv_file:
        for img in img_tags:
            img_url = img.get("src")
            if not img_url:
                continue
            if not img_url.startswith("http"):
                img_url = url + img_url  # 处理相对路径
            img_name = os.path.basename(img_url)
            save_path = os.path.join(OUTPUT_DIR, img_name)
            if download_image(img_url, save_path):
                csv_file.write(f"{img_url},{save_path}\n")

if __name__ == "__main__":
    scrape_images(URL)
