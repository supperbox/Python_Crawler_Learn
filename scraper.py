import requests
from bs4 import BeautifulSoup
import csv
import argparse
import logging
from utils import load_config, ensure_dir_for_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def fetch(url, headers=None, timeout=10):
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logging.error("请求失败: %s", e)
        return None

def parse_items(html, selector):
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(selector)
    items = []
    for n in nodes:
        text = n.get_text(strip=True)
        href = n.get("href") if n.has_attr("href") else None
        items.append({"text": text, "href": href})
    return items

def save_csv(items, output_path):
    if not items:
        logging.info("未找到任何项，跳过保存。")
        return
    ensure_dir_for_file(output_path)
    keys = ["text", "href"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for it in items:
            writer.writerow({k: it.get(k, "") for k in keys})
    logging.info("已保存 %d 条结果到 %s", len(items), output_path)

def main():
    parser = argparse.ArgumentParser(description="简单爬虫练习")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径（YAML）")
    parser.add_argument("--url", help="要抓取的 URL（覆盖配置）")
    parser.add_argument("--selector", help="CSS 选择器（覆盖配置）")
    parser.add_argument("--output", help="输出 CSV 路径（覆盖配置）")
    args = parser.parse_args()

    cfg = load_config(args.config)
    url = args.url or cfg.get("url")
    selector = args.selector or cfg.get("selector")
    output = args.output or cfg.get("output", "output/results.csv")
    headers = cfg.get("headers", {})
    timeout = cfg.get("timeout", 10)

    if not url or not selector:
        logging.error("缺少 url 或 selector，请在 config.yaml 中设置或通过命令行传入。")
        return

    logging.info("开始抓取：%s", url)
    html = fetch(url, headers=headers, timeout=timeout)
    if not html:
        return
    items = parse_items(html, selector)
    logging.info("解析到 %d 项", len(items))
    save_csv(items, output)

if __name__ == "__main__":
    main()
