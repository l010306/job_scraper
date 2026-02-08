# job_scraper
A unified Selenium crawling suite for automating campus job data collection. Includes three specialized scrapers with support for detailed extraction, filtering, deduplication, and comprehensive error management.

# 校园招聘岗位爬虫项目

这是一个综合性的校园招聘岗位爬虫项目，支持爬取**字节跳动**、**美团**和**腾讯**三家公司的校园招聘岗位信息。

## 📋 项目简介

本项目包含三个独立但统一管理的Selenium爬虫，能够自动化抓取各公司的校园招聘岗位信息，包括岗位列表和详情页数据，支持多页爬取、筛选条件、数据去重和完整的错误处理。

### 🎯 核心功能

- ✅ **全自动爬take**: 自动访问、解析、保存数据
- ✅ **详情页抓取**: 提取完整的职位描述、职位要求、团队介绍等信息
- ✅ **多页爬取**: 支持指定页码范围批量爬取
- ✅ **智能筛选**: 支持按地点、类别、项目等条件筛选（字节、腾讯）
- ✅ **数据去重**: 防止重复抓取同一岗位
- ✅ **断点重试**: 网络失败自动重试机制
- ✅ **双格式导出**: 同时保存为CSV和JSON格式
- ✅ **详细日志**: 完整记录爬取过程和错误信息

## 🏗️ 项目结构

```
Job/
├── README.md                    # 本文档
├── requirements.txt             # 依赖列表
├── bytedance_scraper.py        # 字节跳动爬虫
├── meituan_scraper.py          # 美团爬虫
├── tencent_scraper.py          # 腾讯爬虫
├── output/                      # 数据输出目录
│   ├── bytedance/              # 字节跳动数据
│   ├── meituan/                # 美团数据
│   └── tencent/                # 腾讯数据
└── logs/                        # 日志目录
    ├── bytedance/              # 字节跳动日志
    ├── meituan/                # 美团日志
    └── tencent/                # 腾讯日志
```

## 🚀 快速开始

### 1. 环境准备

**系统要求**：
- Python 3.7+
- Chrome 浏览器（最新版本）
- 稳定的网络连接

### 2. 安装依赖

```bash
cd "/Users/lidachuan/Desktop/Web Scraper/Job"
pip install -r requirements.txt
```

依赖包括：
- `selenium>=4.0.0` - 浏览器自动化框架
- `webdriver-manager>=4.0.0` - 自动管理ChromeDriver（无需手动配置）
- `beautifulsoup4>=4.12.0` - HTML解析
- `lxml>=4.9.0` - 高性能HTML解析器

### 3. 运行爬虫

#### 方法一：运行单个爬虫

```bash
# 爬取字节跳动岗位
python3 bytedance_scraper.py

# 爬取美团岗位
python3 meituan_scraper.py

# 爬取腾讯岗位
python3 tencent_scraper.py
```

#### 方法二：批量运行（可选）

```bash
# 依次运行所有爬虫
python3 bytedance_scraper.py && python3 meituan_scraper.py && python3 tencent_scraper.py
```

## ⚙️ 配置说明

每个爬虫文件都包含一个`Config`类，可以根据需求调整配置。

### 字节跳动爬虫配置

编辑`bytedance_scraper.py`（第26-65行）：

```python
class Config:
    # 页数范围
    START_PAGE = 1    # 开始页码
    END_PAGE = 3      # 结束页码
    
    # 筛选配置（留空表示不筛选）
    FILTER_LOCATION = ""             # 工作地点
    FILTER_CATEGORY = ""             # 职位类别
    FILTER_PROJECT = ""              # 招聘项目
    
    # 爬虫行为
    CRAWL_DETAIL = True              # 是否爬取详情页
    HEADLESS = True                  # 是否无头模式
```

**常用筛选参数**：
- **地点**: `CT_11`=北京, `CT_136`=上海, `CT_243`=深圳
- **招聘项目**: `7194661126919358757`=ByteIntern, `7194661644654577981`=日常实习
- 可以组合多个项目：`"7194661644654577981,7194661126919358757"`

### 美团爬虫配置

编辑`meituan_scraper.py`（第26-47行）：

```python
class Config:
    # 页数范围
    START_PAGE = 1    # 开始页码
    END_PAGE = 10     # 结束页码（总共49页）
    
    # 爬虫行为
    CRAWL_DETAIL = True              # 是否爬取详情页
    HEADLESS = True                  # 是否无头模式
```

### 腾讯爬虫配置

编辑`tencent_scraper.py`（第26-58行）：

```python
class Config:
    # 页数范围
    START_PAGE = 1    # 开始页码
    END_PAGE = 5      # 结束页码
    
    # 筛选配置
    FILTER_QUERY = "p_2,p_104"       # p_2=应届实习, p_104=技术类
    
    # 爬虫行为
    CRAWL_DETAIL = True              # 是否爬取详情页
    HEADLESS = True                  # 是否无头模式
```

**常用筛选参数**：
- `p_2`=应届实习, `p_3`=日常实习
- `p_104`=技术类, `p_105`=产品类, `p_106`=设计类

## 📁 输出数据格式

### 字节跳动数据字段

| 字段 | 说明 | 示例 |
|------|------|------|
| title | 岗位标题 | "后端开发工程师" |
| system_id | 系统ID | "7589123456789012345" |
| business_id | 业务ID | "1234567" |
| location | 工作地点 | "北京" |
| type | 岗位类型 | "全职" / "实习" |
| category | 岗位类别 | "研发-后端" |
| program | 招聘项目 | "ByteIntern" |
| url | 详情页URL | "https://jobs.bytedance.com/..." |
| job_description | 职位描述 | "负责..." |
| job_requirements | 职位要求 | "本科及以上..." |
| team_intro | 团队介绍 | "我们是..." |
| crawl_time | 爬取时间 | "2026-02-08T15:30:00" |

### 美团数据字段

| 字段 | 说明 | 示例 |
|------|------|------|
| job_union_id | 岗位ID | "4171572797" |
| title | 岗位标题 | "即时零售生态市场实习生" |
| location | 工作地点 | "北京市" |
| job_type | 岗位类型 | "日常实习" |
| job_responsibilities | 岗位职责 | "1. 负责..." |
| job_requirements | 岗位要求 | "1. 本科及以上..." |
| preferred_qualifications | 加分项 | "有相关经验优先" |
| job_highlights | 岗位亮点 | "团队氛围好" |
| crawl_time | 爬取时间 | "2026-02-08T15:30:00" |

### 腾讯数据字段

| 字段 | 说明 | 示例 |
|------|------|------|
| title | 岗位标题 | "技术研究-高性能计算方向" |
| category | 职位类别 | "技术" |
| job_type | 实习类型 | "应届实习" |
| department | 事业群 | "TEG 技术工程事业群" |
| location | 工作地点 | "深圳总部 北京" |
| job_description | 岗位描述 | "包含GPU、网络..." |
| job_requirements | 岗位要求 | "1、扎实的..." |
| bonus_notes | 加分项 | "有相关项目经验者优先" |
| interview_cities | 面试城市 | "远程面试" |
| crawl_time | 爬取时间 | "2026-02-08T15:30:00" |

### 输出文件

运行后会在对应的`output/`子目录下生成：
- `{company}_jobs_YYYYMMDD_HHMMSS.json` - JSON格式数据
- `{company}_jobs_YYYYMMDD_HHMMSS.csv` - CSV格式数据（可用Excel打开）

## 🔍 三个爬虫对比

| 特性 | 字节跳动 | 美团 | 腾讯 |
|------|---------|------|------|
| **翻页方式** | URL参数 ✅ | URL参数 ✅ | AJAX按钮 ⚠️ |
| **详情页访问** | 直接URL | 新标签页 | 新标签页 |
| **筛选功能** | ⭐⭐⭐ (地点/类别/项目) | ❌ 不支持 | ⭐⭐ (query参数) |
| **实现难度** | ★☆☆☆☆ | ★★☆☆☆ | ★★★☆☆ |
| **稳定性** | ★★★★★ | ★★★★★ | ★★★★☆ |
| **爬取速度** | 快 | 中 | 较慢（AJAX翻页） |

**建议**：
- **字节跳动**: 使用筛选功能可以大大提高效率
- **美团**: URL翻页最稳定，适合大批量爬取
- **腾讯**: AJAX翻页需要更多等待时间

## ⚠️ 注意事项

### 1. 爬取速度控制

程序已内置了合理的延时设置：
- 页面之间：随机2-5秒
- 详情页之间：随机1-3秒
- **建议保持默认设置**，避免触发反爬机制

### 2. 详情页爬取时间

详情页会显著增加爬取时间：
- 关闭详情页：`CRAWL_DETAIL = False` （只获取列表信息，速度快）  
- 开启详情页：`CRAWL_DETAIL = True` （获取完整信息，速度慢）

**时间估算**：
- 字节跳动：3页 × 15岗位 ≈ 约2-3分钟（含详情页）
- 美团：3页 × 20岗位 ≈ 约2.5-3分钟（含详情页）
- 腾讯：3页 × 10岗位 ≈ 约3-4分钟（含详情页，AJAX翻页较慢）

### 3. 无头模式

- `HEADLESS = True`：后台运行，看不到浏览器（推荐生产环境）
- `HEADLESS = False`：可见浏览器窗口（推荐调试）

### 4. 网络要求

- 需要稳定的网络连接
- 如果网络不稳定，可以增加`PAGE_LOAD_WAIT`时间（默认10秒）
- 程序已内置重试机制（最多3次）

## 🛠️ 常见问题

### Q1: ChromeDriver下载失败？

**原因**: 网络问题

**解决方案**:
```bash
# 方案1: 更新Chrome浏览器到最新版
# 方案2: 配置代理
export https_proxy=http://127.0.0.1:7890
```

### Q2: 页面加载超时？

**错误**: `TimeoutException`

**解决方案**:
```python
# 增加等待时间（修改对应爬虫文件）
PAGE_LOAD_WAIT = 20  # 改为20秒
```

### Q3: 找不到岗位卡片元素？

**错误**: `NoSuchElementException`

**原因**: 网站改版，CSS选择器失效

**解决方案**:
1. 设置`HEADLESS = False`观察浏览器
2. 打开对应网站，按F12查看元素
3. 更新代码中的CSS选择器

### Q4: 数据为空？

**可能原因**:
- 筛选条件过严（字节跳动、腾讯）
- 页码超出范围
- 网络问题

**解决方案**:
```python
# 放宽筛选条件（字节跳动）
FILTER_LOCATION = ""    # 不限地点
FILTER_CATEGORY = ""    # 不限类别
FILTER_PROJECT = ""     # 不限项目

# 放宽筛选条件（腾讯）
FILTER_QUERY = ""       # 不筛选
```

## 💡 使用技巧

### 技巧1: 快速浏览所有岗位

```python
# 关闭详情页爬取，只看列表
CRAWL_DETAIL = False
START_PAGE = 1
END_PAGE = 10
```

### 技巧2: 只爬特定地点（字节跳动）

```python
# 只爬北京的岗位
FILTER_LOCATION = "CT_11"
```

### 技巧3: 数据分析

```python
import pandas as pd

# 读取CSV数据
df = pd.read_csv('output/bytedance/bytedance_jobs_*.csv')

# 按地点统计
print(df['location'].value_counts())

# 筛选特定岗位
backend = df[df['category'].str.contains('后端', na=False)]
print(f"后端岗位: {len(backend)} 个")
```

## 📝 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.7+ | 编程语言 |
| Selenium | ≥4.0.0 | 浏览器自动化 |
| webdriver-manager | ≥4.0.0 | 自动管理ChromeDriver |
| Beautiful Soup4 | ≥4.12.0 | HTML解析 |
| lxml | ≥4.9.0 | 高性能HTML解析器 |

## 🔒 法律声明

- ⚠️ 本项目仅供**学习研究**使用
- ⚠️ 请遵守各网站的robots.txt和服务条款
- ⚠️ **不要用于商业目的**
- ⚠️ 控制请求频率，避免给服务器造成压力
- ⚠️ 抓取的数据不应公开传播或用于侵犯隐私

## 📞 使用帮助

如遇到问题:
1. 查看`logs/`目录下的日志文件
2. 检查网络连接和Chrome版本
3. 尝试关闭无头模式观察浏览器行为
4. 检查配置参数是否正确

## 🎯 适用场景

- 📊 **求职准备**: 了解各公司招聘岗位和要求
- 🔍 **市场调研**: 研究互联网行业岗位需求趋势
- 📈 **趋势分析**: 跟踪招聘岗位数量和类型变化
- 🎓 **数据分析**: 练习数据抓取和分析技能
- 💼 **简历优化**: 了解岗位要求，针对性调整简历

---

**Happy Job Hunting! 🚀💼**
