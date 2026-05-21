# -*- coding: utf-8 -*-
"""
unisyue.com 产品彩页爬取脚本
==============================

功能：
1. 遍历紫光恒越 (https://www.unisyue.com) "创新产品" 与 "通用产品" 下的所有分类
2. 进入每个产品详情页 (例如 /Autonomous_Controllable/11/UNISS5800HIG/2443.html)
3. 下载 "相关资料" → "产品彩页" 中的 PDF 文件

使用方法：
    pip install requests beautifulsoup4
    python unisyue_scraper.py

PDF 会保存到当前目录的 downloads/ 文件夹下，按分类自动建子目录。
"""

import os
import re
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.unisyue.com"
OUTPUT_DIR = Path(__file__).parent / "downloads"

# 需要遍历的分类入口页（创新产品 + 通用产品）
CATEGORY_ENTRIES = [
    # 创新产品
    "/Autonomous_Controllable/11/default.html",  # 交换机
    # "/Autonomous_Controllable/12/default.html",  # 路由器
    # "/Autonomous_Controllable/13/default.html",  # 安全
    # "/Autonomous_Controllable/14/default.html",  # 计算存储
    # "/Autonomous_Controllable/15/default.html",  # 大模型一体机
    # 通用产品（如不需要可注释掉）
    # "/Commercial_Product/default.html",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

REQUEST_DELAY = 0.8           # 请求之间的间隔（秒），礼貌爬取
TIMEOUT = 30
session = requests.Session()
session.headers.update(HEADERS)


def fetch(url: str) -> str | None:
    """抓取页面 HTML，失败返回 None。"""
    try:
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        # 站点为 UTF-8
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        print(f"[WARN] 抓取失败 {url}: {e}")
        return None


def absolute(url: str) -> str:
    """把相对链接转换为绝对链接。"""
    return urllib.parse.urljoin(BASE_URL, url)


def safe_filename(name: str) -> str:
    """去掉 Windows 文件名非法字符。"""
    return re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", name).strip().strip(".") or "file"


def find_product_pages(category_url: str) -> set[str]:
    """从分类列表页（含可能的分页）收集所有产品详情页 URL。"""
    found: set[str] = set()
    to_visit = [category_url]
    visited = set()

    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)
        html = fetch(url)
        time.sleep(REQUEST_DELAY)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            full = absolute(href)
            if not full.startswith(BASE_URL):
                continue

            # 产品详情页：以数字.html 结尾，且不是 default.html
            # 形如 /Autonomous_Controllable/11/UNISS5800HIG/2443.html
            # 或   /Commercial_Product/.../1234.html
            if re.search(r"/(Autonomous_Controllable|Commercial_Product)/.+/\d+\.html$", full):
                found.add(full)
            # 分页 / 同分类下的其他列表页
            elif full.endswith("default.html") and full not in visited:
                to_visit.append(full)
    return found


# 只抓取 "产品彩页" 这一节，其它如 "光模块手册"、"用户手册" 等不下载
TARGET_SECTION = "产品彩页"
# 节标题可能用的 HTML 标签（h1~h6 全部覆盖，足够稳健）
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def find_pdf_links(product_url: str) -> list[tuple[str, str]]:
    """
    只返回 "产品彩页" 章节下的 PDF 链接 [(pdf_url, 显示文本)]。

    页面结构示例：
        <h4>产品彩页</h4>
        <a href="...pdf">UNIS S12600-CR-G…</a>
        <h4>光模块手册</h4>     ← 到这里就停
        <a href="...pdf">…</a>
    """
    html = fetch(product_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    # 1) 找到文字为 "产品彩页" 的标题节点
    heading = None
    for tag in soup.find_all(HEADING_TAGS):
        if TARGET_SECTION in tag.get_text(strip=True):
            heading = tag
            break
    if heading is None:
        return []

    # 2) 顺着 DOM 往后走，遇到下一个标题就停；中间所有 .pdf 链接收下来
    pdfs: list[tuple[str, str]] = []
    for node in heading.find_all_next():
        if node.name in HEADING_TAGS:
            break  # 进入下一节，停止
        if node.name == "a" and node.has_attr("href"):
            href = node["href"].strip()
            if href.lower().endswith(".pdf"):
                text = node.get_text(strip=True) or Path(href).stem
                pdfs.append((absolute(href), text))
    return pdfs


def download_pdf(pdf_url: str, save_path: Path) -> bool:
    if save_path.exists():
        print(f"[SKIP] 已存在: {save_path.name}")
        return True
    try:
        with session.get(pdf_url, timeout=TIMEOUT, stream=True) as r:
            r.raise_for_status()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"[OK]   下载完成: {save_path}")
        return True
    except requests.RequestException as e:
        print(f"[FAIL] 下载失败 {pdf_url}: {e}")
        if save_path.exists():
            save_path.unlink(missing_ok=True)
        return False


def category_dir(product_url: str) -> Path:
    """根据产品 URL 推断分类子目录，便于归档。"""
    # 例 /Autonomous_Controllable/11/UNISS5800HIG/2443.html -> Autonomous_Controllable/11
    parts = urllib.parse.urlparse(product_url).path.strip("/").split("/")
    if len(parts) >= 2:
        return OUTPUT_DIR / parts[0] / parts[1]
    return OUTPUT_DIR


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    all_products: set[str] = set()

    print("=" * 60)
    print("步骤 1: 收集产品详情页 URL")
    print("=" * 60)
    for entry in CATEGORY_ENTRIES:
        cat_url = absolute(entry)
        print(f"\n>> 扫描分类: {cat_url}")
        products = find_product_pages(cat_url)
        print(f"   找到 {len(products)} 个产品页")
        all_products.update(products)

    print(f"\n合计 {len(all_products)} 个产品详情页\n")

    print("=" * 60)
    print("步骤 2: 提取并下载 PDF 彩页")
    print("=" * 60)
    total_pdf = 0
    for i, product_url in enumerate(sorted(all_products), 1):
        print(f"\n[{i}/{len(all_products)}] {product_url}")
        pdfs = find_pdf_links(product_url)
        time.sleep(REQUEST_DELAY)
        if not pdfs:
            print("   (无 PDF)")
            continue
        out_dir = category_dir(product_url)
        for pdf_url, text in pdfs:
            # 文件名：优先用链接文本，回退用 URL 最后一段
            base = safe_filename(text)
            if not base.lower().endswith(".pdf"):
                base += ".pdf"
            save_path = out_dir / base
            if download_pdf(pdf_url, save_path):
                total_pdf += 1
            time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"完成！共下载/确认 {total_pdf} 个 PDF，保存到: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
