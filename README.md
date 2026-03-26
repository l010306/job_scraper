# job_scraper
A unified Selenium crawling suite for automating campus job data collection. Includes three specialized scrapers with support for detailed extraction, filtering, deduplication, and comprehensive error management.

# 校园招聘岗位爬虫项目

这是一个综合性的校园招聘岗位爬虫项目，支持爬取**字节跳动**、**美团**和**腾讯**三家公司的校园招聘岗位信息。

## 📋 项目简介

本项目包含三个独立但统一管理的 Selenium 爬虫，能够自动化抓取各公司的校园招聘岗位信息，包括岗位列表和详情页数据，支持多页爬取、筛选条件、数据去重和完整的错误处理。

### 🎯 核心功能

- ✅ **全自动爬取**: 自动访问、解析、保存数据
- ✅ **详情页抓取**: 提取完整的职位描述、职位要求、团队介绍等信息
- ✅ **多页爬取**: 支持指定页码范围批量爬取
- ✅ **智能筛选**: 支持按地点、类别、项目等条件筛选（字节、腾讯）
- ✅ **数据去重**: 防止重复抓取同一岗位
- ✅ **断点重试**: 网络失败自动重试机制
- ✅ **双格式导出**: 同时保存为 CSV 和 JSON 格式
- ✅ **详细日志**: 完整记录爬取过程和错误信息

## 🏗️ 项目结构

```
Job/
├── README.md                    # 本文档
├── requirements.txt             # 依赖列表
├── base_scraper.py             # 爬虫基础类 (通用逻辑)
├── bytedance_scraper.py        # 字节跳动爬虫
├── meituan_scraper.py          # 美团爬虫
├── tencent_scraper.py          # 腾讯爬虫
├── main.py                     # 统一运行入口
├── output/                      # 数据输出目录
└── logs/                        # 日志目录
```

## 🚀 快速开始

### 1. 环境准备

**系统要求**：
- Python 3.7+
- Chrome 浏览器（最新版本）
- 稳定的网络连接

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行爬虫

推荐使用 `main.py` 启用统一入口：

```bash
# 查看帮助
python3 main.py --help

# 运行所有爬虫
python3 main.py all

# 运行特定爬虫
python3 main.py bytedance
python3 main.py meituan
python3 main.py tencent
```

## ⚙️ 配置说明

每个爬虫文件都包含一个 `Config` 类，可以根据需求调整配置。

### 字节跳动爬虫配置

编辑 `bytedance_scraper.py`：
- `START_PAGE` / `END_PAGE`: 页码范围
- `FILTER_LOCATION`: 地点筛选
- `FILTER_CATEGORY`: 类别筛选
- `CRAWL_DETAIL`: 是否获取详情

### 美团爬虫配置

编辑 `meituan_scraper.py`：
- `START_PAGE` / `END_PAGE`: 页码范围
- `CRAWL_DETAIL`: 是否获取详情

### 腾讯爬虫配置

编辑 `tencent_scraper.py`：
- `START_PAGE` / `END_PAGE`: 页码范围
- `FILTER_QUERY`: 筛选参数
- `CRAWL_DETAIL`: 是否获取详情

## 📁 输出数据格式

运行后会在对应的 `output/` 子目录下生成以公司命名的 JSON 和 CSV 文件。

## 🔒 法律声明

- ⚠️ 本项目仅供**学习研究**使用
- ⚠️ 请遵守各网站的 robots.txt 和服务条款
- ⚠️ **不要用于商业目的**
- ⚠️ 控制请求频率，避免给服务器造成压力

---

**Happy Job Hunting! 🚀💼**
