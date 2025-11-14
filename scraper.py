import requests
from bs4 import BeautifulSoup
import csv
import argparse
import logging
from utils import load_config, ensure_dir_for_file

# 配置日志记录，设置日志级别为 INFO，输出格式为 "[日志级别]: 消息"
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def fetch(url, headers=None, timeout=10):
    """
    发送 HTTP GET 请求，获取网页内容。
    
    参数:
        url (str): 目标网页的 URL。
        headers (dict): 请求头（可选）。
        timeout (int): 请求超时时间，单位为秒（默认 10 秒）。
    
    返回:
        str: 网页的 HTML 内容（成功时）。
        None: 请求失败时返回 None。
    """
    try:
        # 使用 requests 发送 GET 请求
        resp = requests.get(url, headers=headers, timeout=timeout)
        # 检查响应状态码是否为 2xx，若非 2xx 则抛出异常
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        # 捕获异常并记录错误日志
        logging.error("请求失败: %s", e)
        return None

def parse_items(html, selector):
    """
    解析 HTML 内容，提取符合 CSS 选择器的元素。
    
    参数:
        html (str): HTML 文档字符串。
        selector (str): CSS 选择器，用于定位目标元素。
    
    返回:
        list[dict]: 提取的内容列表，每项为字典，包含 "text" 和 "href"。
    """
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(html, "html.parser")
    # 根据 CSS 选择器查找匹配的元素
    nodes = soup.select(selector)
    items = []
    # 遍历匹配的元素，提取文本和链接
    for n in nodes:
        text = n.get_text(strip=True)  # 提取元素的文本内容
        href = n.get("href") if n.has_attr("href") else None  # 提取 href 属性（若存在）
        items.append({"text": text, "href": href})
    return items

def save_csv(items, output_path):
    """
    将提取的内容保存到 CSV 文件。
    
    参数:
        items (list[dict]): 提取的内容列表。
        output_path (str): CSV 文件的保存路径。
    """
    if not items:
        # 如果没有内容，记录日志并跳过保存
        logging.info("未找到任何项，跳过保存。")
        return
    # 确保输出目录存在
    ensure_dir_for_file(output_path)
    # 定义 CSV 文件的列名
    keys = ["text", "href"]
    # 打开 CSV 文件并写入数据
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()  # 写入表头
        for it in items:
            writer.writerow({k: it.get(k, "") for k in keys})  # 写入每一行数据
    logging.info("已保存 %d 条结果到 %s", len(items), output_path)

def main():
    """
    主函数，负责解析配置、调用爬虫逻辑并保存结果。
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="简单爬虫练习")
    # 添加命令行参数
    parser.add_argument("--config", default="config.yaml", help="配置文件路径（YAML）")
    parser.add_argument("--url", help="要抓取的 URL（覆盖配置）")
    parser.add_argument("--selector", help="CSS 选择器（覆盖配置）")
    parser.add_argument("--output", help="输出 CSV 路径（覆盖配置）")
    # 解析命令行参数
    args = parser.parse_args()

    # 加载配置文件
    cfg = load_config(args.config)
    # 获取 URL、选择器和输出路径（优先使用命令行参数）
    url = args.url or cfg.get("url")
    selector = args.selector or cfg.get("selector")
    output = args.output or cfg.get("output", "output/results.csv")
    # 获取请求头和超时时间
    headers = cfg.get("headers", {})
    timeout = cfg.get("timeout", 10)

    # 检查是否提供了 URL 和选择器
    if not url or not selector:
        logging.error("缺少 url 或 selector，请在 config.yaml 中设置或通过命令行传入。")
        return

    # 开始抓取网页
    logging.info("开始抓取：%s", url)
    html = fetch(url, headers=headers, timeout=timeout)
    if not html:
        return
    # 解析网页内容
    items = parse_items(html, selector)
    logging.info("解析到 %d 项", len(items))
    # 保存结果到 CSV 文件
    save_csv(items, output)

# 程序入口
if __name__ == "__main__":
    main()
