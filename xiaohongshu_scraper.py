import os
import time
import yaml
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import pickle

# 读取配置文件
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 全局变量
URL = config["url"]  # 小红书主页URL
OUTPUT_DIR = config["output_dir"]  # 图片保存目录
CSV_FILE = config["output"]  # CSV文件路径
SCROLL_TIMES = config["scroll_times"]  # 滚动次数
WAIT_TIME = config["wait_time"]  # 每次滚动后的等待时间
SEARCH_KEYWORD = config.get("search_keyword", "氛围感图片")  # 搜索关键词
COOKIE_FILE = config.get("cookie_file", "cookies.pkl")  # Cookie保存文件
REQUIRED_COUNT = config.get("required_images", 200)  # 需要下载的图片数量（默认200）

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

def setup_driver():
    """
    配置并启动 Chrome WebDriver
    - 设置浏览器选项（如窗口大小、禁用检测等）
    - 使用用户数据目录加载已登录的会话
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={config['headers']['User-Agent']}")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 隐藏 WebDriver 特征（兼容不同环境）
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
    except Exception as e:
        print(f"CDP命令未支持或执行失败，已跳过反检测注入: {e}")
    
    driver.maximize_window()
    return driver

def save_cookies(driver, filepath=COOKIE_FILE):
    """
    保存登录后的 Cookie 到文件
    - 参数: driver (WebDriver实例), filepath (保存路径)
    """
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        print(f"Cookie已保存到: {filepath}")
    except Exception as e:
        print(f"保存Cookie失败: {e}")

def load_cookies(driver, filepath=COOKIE_FILE):
    """
    从文件加载 Cookie 并添加到浏览器
    - 参数: driver (WebDriver实例), filepath (Cookie文件路径)
    - 返回: 是否成功加载
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
            print(f"Cookie已加载: {filepath}")
            return True
        else:
            print("Cookie文件不存在，需要手动登录")
            return False
    except Exception as e:
        print(f"加载Cookie失败: {e}")
        return False

def wait_for_login(driver, timeout=300):
    """
    等待用户手动登录
    - 参数: driver (WebDriver实例), timeout (超时时间，秒)
    - 返回: 是否成功登录
    """
    print(f"\n请在 {timeout} 秒内完成登录...")
    start_time = time.time()
    try:
        # 等待登录框消失或用户信息元素出现
        WebDriverWait(driver, timeout).until(
            lambda d: not d.find_elements(By.CSS_SELECTOR, ".login-container")
        )
        print("\n检测到登录成功！")
        save_cookies(driver)
        return True
    except Exception as e:
        print("\n登录超时或未检测到登录成功")
        return False

def scroll_page(driver, times):
    """
    模拟用户滚动页面，加载更多内容
    - 参数: driver (WebDriver实例), times (滚动次数)
    """
    last_img_count = 0
    stable_count = 0
    for i in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"第 {i+1} 次滚动到底部")
        time.sleep(WAIT_TIME)
        
        # 检查图片数量变化
        current_img_count = len(driver.find_elements(By.TAG_NAME, "img"))
        print(f"  当前页面img标签数量: {current_img_count}")
        if current_img_count > last_img_count:
            last_img_count = current_img_count
            stable_count = 0
        else:
            stable_count += 1
            if stable_count >= 2:
                print("  图片数量已稳定，停止滚动")
                break
        # 模拟向上滚动
        scroll_position = driver.execute_script("return window.pageYOffset;")
        driver.execute_script(f"window.scrollTo(0, {scroll_position - 500});")
        time.sleep(1)
    print("滚动结束，等待图片资源完全加载...")
    time.sleep(5)

def extract_images(driver):
    """
    提取页面中的所有图片链接
    - 参数: driver (WebDriver实例)
    - 返回: 图片链接列表
    """
    img_urls = set()
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("\n开始分析页面结构...")
        
        # 提取小红书笔记封面图
        note_covers = driver.find_elements(By.CSS_SELECTOR, ".cover.ld.mask img, .note-item img, [class*='cover'] img")
        print(f"  找到笔记封面图: {len(note_covers)} 个")
        for img in note_covers:
            for attr in ["src", "data-src", "lazy-src", "data-lazy"]:
                src = img.get_attribute(attr)
                if src and "http" in src and "avatar" not in src.lower():
                    if "imageView2" in src:
                        src = src.split("?imageView2")[0]
                    img_urls.add(src)
                    break
        
        # 提取背景图
        bg_elements = driver.find_elements(By.CSS_SELECTOR, "[style*='background-image']")
        print(f"  找到背景图元素: {len(bg_elements)} 个")
        import re
        for elem in bg_elements:
            style = elem.get_attribute("style")
            if style:
                matches = re.findall(r'url\(["\']?(https?://[^")]+?\.(jpg|jpeg|png|webp)[^")]*)["\']?\)', style)
                for match in matches:
                    url = match[0] if isinstance(match, tuple) else match
                    if "avatar" not in url.lower():
                        img_urls.add(url)
        
        print(f"\n找到 {len(img_urls)} 张有效图片")
    except Exception as e:
        print(f"提取图片时出错: {e}")
    return list(img_urls)

def download_image(img_url, index, max_retries=3):
    """
    下载图片到本地
    - 参数: img_url (图片链接), index (图片序号), max_retries (最大重试次数)
    """
    for retry in range(max_retries):
        try:
            headers = {
                'User-Agent': config['headers']['User-Agent'],
                'Referer': 'https://www.xiaohongshu.com/'
            }
            response = requests.get(img_url, headers=headers, timeout=15)
            if response.status_code == 200:
                ext = img_url.split(".")[-1].split("?")[0]
                if ext not in ["jpg", "jpeg", "png", "webp"]:
                    ext = "jpg"
                filename = f"xhs_{SEARCH_KEYWORD}_{index}.{ext}"
                filepath = os.path.join(OUTPUT_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"下载成功: {filename}")
                return filepath
        except Exception as e:
            print(f"下载失败 (尝试 {retry+1}/{max_retries}): {e}")
            if retry < max_retries - 1:
                time.sleep(2)
    return None

def save_to_csv(data):
    """
    保存图片信息到 CSV 文件
    - 参数: data (图片数据列表)
    """
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["序号", "图片链接", "保存路径", "关键词"])
        writer.writerows(data)
    print(f"CSV 文件已保存: {CSV_FILE}")

def search_keyword(driver, keyword):
    """
    在小红书中搜索关键词
    - 参数: driver (WebDriver实例), keyword (搜索关键词)
    - 返回: 是否搜索成功
    """
    try:
        print(f"开始搜索关键词: {keyword}")
        wait = WebDriverWait(driver, 15)
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
        driver.get(search_url)
        time.sleep(5)
        if "search_result" in driver.current_url:
            print("通过URL搜索成功")
            return True
        print("搜索方式均失败")
        return False
    except Exception as e:
        print(f"搜索失败: {e}")
        return False

# URL 规范化，移除查询参数，便于去重
def normalize_url(url: str) -> str:
    """
    规范化图片链接
    - 参数: url (图片链接)
    - 返回: 规范化后的链接
    """
    try:
        return url.split("?")[0] if url else url
    except Exception:
        return url

def main():
    """
    主函数：从本地 HTML 文件提取图片
    """
    print("="*50)
    print("小红书图片爬虫启动（本地模式）")
    print(f"搜索关键词: {SEARCH_KEYWORD}")
    print(f"目标下载数量: {REQUIRED_COUNT}")
    print("="*50)
    
    driver = setup_driver()
    try:
        driver.get("https://www.xiaohongshu.com")
        time.sleep(3)
        cookie_loaded = load_cookies(driver)
        if not cookie_loaded:
            if not wait_for_login(driver):
                print("未检测到登录，继续执行...")
        
        if search_keyword(driver, SEARCH_KEYWORD):
            print("搜索成功，等待内容加载...")
            time.sleep(5)
        else:
            print("搜索失败，尝试访问首页内容...")
            driver.get(URL)
            time.sleep(3)
        
        # 按需下载循环：滚动 -> 提取 -> 去重 -> 下载（直到达到 REQUIRED_COUNT）
        print("\n开始按需抓取图片...")
        csv_data = []
        downloaded = 0
        seen_normalized = set()  # 规范化后的URL集合，用于全局去重
        stagnation_rounds = 0     # 连续无新增下载的轮数（防止死循环）
        MAX_STAGNATION_ROUNDS = 8

        while downloaded < REQUIRED_COUNT and stagnation_rounds < MAX_STAGNATION_ROUNDS:
            # 每轮滚动一小步，触发懒加载
            scroll_page(driver, 1)
            # 提取页面当前所有图片
            all_urls = extract_images(driver)

            # 过滤出新出现的候选URL（按规范化URL去重）
            candidates = []
            for u in all_urls:
                nu = normalize_url(u)
                if nu and nu not in seen_normalized:
                    seen_normalized.add(nu)
                    candidates.append(u)

            print(f"本轮候选新图: {len(candidates)} 张")
            gained = 0

            # 下载本轮候选，直到达到 REQUIRED_COUNT
            for u in candidates:
                if downloaded >= REQUIRED_COUNT:
                    break
                filepath = download_image(u, downloaded + 1)
                if filepath:
                    downloaded += 1
                    gained += 1
                    csv_data.append([downloaded, u, filepath, SEARCH_KEYWORD])

            print(f"已下载: {downloaded}/{REQUIRED_COUNT}")

            if gained == 0:
                stagnation_rounds += 1
                print(f"本轮无新增下载，连续无增量轮数: {stagnation_rounds}/{MAX_STAGNATION_ROUNDS}")
                # 适当等待再尝试下一轮
                time.sleep(2)
            else:
                stagnation_rounds = 0

        if downloaded < REQUIRED_COUNT:
            print(f"未达到目标数量，已下载 {downloaded}/{REQUIRED_COUNT}。可能原因：内容不足/反爬限制/网络波动。")

        if csv_data:
            save_to_csv(csv_data)
        print("\n任务完成！")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
    finally:
        driver.quit()
        print("浏览器已关闭")

if __name__ == "__main__":
    main()