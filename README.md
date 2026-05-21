# Web_scraping

紫光恒越（[unisyue.com](https://www.unisyue.com)）产品**彩页 PDF** 批量下载脚本。

遍历"创新产品"与"通用产品"下所有分类的产品详情页，定位每页 `产品彩页` 章节，下载其中的 PDF 文件，按分类归档。

## 功能

- 自动发现全部产品详情页（DFS + 去重）
- 只抓 `产品彩页` 章节，不会把"光模块手册""用户手册"等一锅端
- 按分类自动建子目录归档
- 已下载的 PDF 自动跳过，中断后可续传
- 请求间隔可配置，礼貌爬取

## 环境要求

- Python 3.10+
- 依赖：`requests`、`beautifulsoup4`

## 安装与运行

```bash
git clone https://github.com/oliveranderson1089-crypto/Web_scraping.git
cd Web_scraping

# 建议使用虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install requests beautifulsoup4
python unisyue_scraper.py
```

下载完成后，PDF 会保存到 `downloads/` 目录，按分类组织：

```
downloads/
├── Autonomous_Controllable/    创新产品
│   ├── 11/   交换机
│   ├── 12/   路由器
│   ├── 13/   安全
│   ├── 14/   计算存储
│   └── 15/   大模型一体机
└── Commercial_Product/         通用产品
    ├── 21/ … 28/
```

## 自定义

打开 `unisyue_scraper.py`，顶部有几个可调参数：

| 变量 | 作用 |
|---|---|
| `CATEGORY_ENTRIES` | 要扫描的分类入口 URL 列表，注释掉不想要的 |
| `TARGET_SECTION` | 要抓哪个章节，默认 `"产品彩页"`；改成 `"用户手册"` 就抓手册 |
| `REQUEST_DELAY` | 请求间隔秒数，默认 0.8，太快可能被限流 |
| `OUTPUT_DIR` | 输出目录，默认脚本同级的 `downloads/` |

## Windows 终端中文乱码

如果 PowerShell 里看到 `���� 1: �ռ�...` 这种乱码（文件名本身没事），运行前执行：

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

## 实现说明

- HTTP 抓取：`requests.Session`，附带浏览器 `User-Agent`
- HTML 解析：`BeautifulSoup`
- 章节定位：找到文本为 `产品彩页` 的 `<h1>~<h6>` 标题元素，沿 DOM 收集后续 PDF 链接，遇到下一个标题即停
- 并发：单线程顺序抓取，靠 `REQUEST_DELAY` 控制频率（避免触发反爬）

## 合规与免责

- 仅用于个人学习与资料整理
- 请遵守目标站点的 `robots.txt` 与服务条款
- 控制请求频率，不要给对方服务器造成压力
- 下载内容版权归紫光恒越所有，请勿用于商业用途
