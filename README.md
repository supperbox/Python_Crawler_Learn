# Python 爬虫练习

简要说明：

- 使用 requests + BeautifulSoup 实现基础抓取与解析。
- 配置在 config.yaml 中，可通过命令行参数覆盖。
- 输出为 CSV 文件。

快速开始：

1. 创建并激活虚拟环境（可选）。
2. 安装依赖：
   pip install -r requirements.txt
3. 运行示例：
   python scraper.py
   或指定 URL/selector：
   python scraper.py --url "https://example.com" --selector "a"

文件说明：

- config.yaml：默认配置
- scraper.py：主脚本
- utils.py：工具函数
