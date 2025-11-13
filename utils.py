import os
import yaml

def load_config(path="config.yaml"):
    """读取 YAML 配置，返回 dict（不存在时返回空 dict）。"""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def ensure_dir_for_file(filepath):
    """确保文件所在目录存在。"""
    dirpath = os.path.dirname(os.path.abspath(filepath))
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
