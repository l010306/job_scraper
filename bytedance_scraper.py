"""
字节跳动校园招聘岗位爬虫 - Selenium版本
支持JavaScript动态加载，完整的错误处理和数据持久化
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import csv
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# ========== 配置区域 ==========
class Config:
    """爬虫配置"""
    BASE_URL = "https://jobs.bytedance.com"
    CAMPUS_URL = f"{BASE_URL}/campus/position"
    
    # 爬虫行为配置
    PAGE_LOAD_WAIT = 10  # 页面加载最大等待时间（秒）
    REQUEST_DELAY = (2, 5)  # 请求间隔（秒）
    MAX_RETRIES = 3  # 最大重试次数
    CRAWL_DETAIL = True  # 是否爬取详情页（职位要求等）
    
    # 页数范围配置
    START_PAGE = 31  # 开始页码
    END_PAGE = 45    # 结束页码（包含）
    
    # 筛选配置（留空表示不筛选）
    FILTER_LOCATION = ""     # 工作地点，例如: "CT_11" (北京), "CT_136" (上海), "CT_243" (深圳)
    FILTER_CATEGORY = "6704215864629004552"     # 职位类别，例如: "6704215882479962371" (研发-后端)，一次只能选一个
    FILTER_PROJECT = "7194661644654577981,7194661126919358757"      # 招聘项目，例如: "7194661126919358757" (ByteIntern)
    # 支持多个项目，用逗号分隔："7194661644654577981,7194661126919358757" (日常实习+ByteIntern)
     
    # 常用筛选选项参考（注释）
    # 地点: CT_11=北京, CT_136=上海, CT_243=深圳, CT_114=杭州, CT_234=成都, CT_265=广州
    # 类别: 需要通过浏览器查看具体ID（点击筛选后查看URL中的category参数）
    # 招聘项目(实习):
    #   - ByteIntern: "7194661126919358757"
    #   - 日常实习: "7194661644654577981"
    #   - 筋斗云人才计划实习专项: "7468181472685164808"
    #   - 2026校园实习: "7481474995534301447"
    #   - 所有实习(选择父类别): "7481474995534301447,7468181472685164808,7194661644654577981,7194661126919358757"
    # 招聘项目(正式):
    #   - 2026届校园招聘: "7525009396952582407"
    #   - 所有正式: "7525009396952582407,7503447747358361864,7493737120754911496"
    
    # 输出配置
    OUTPUT_DIR = Path(__file__).parent / "output" / "bytedance"
    LOG_DIR = Path(__file__).parent / "logs" / "bytedance"
    
    # 浏览器配置
    HEADLESS = True  # 是否无头模式（True=看不到浏览器，False=可见）


# ========== 日志配置 ==========
def setup_logging():
    """配置日志系统"""
    Config.LOG_DIR.mkdir(exist_ok=True)
    
    log_file = Config.LOG_DIR / f"crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


# ========== Selenium爬虫类 ==========
class ByteDanceSeleniumCrawler:
    """字节跳动岗位爬虫 - Selenium版本"""
    
    def __init__(self, headless: bool = Config.HEADLESS):
        """
        初始化爬虫
        
        Args:
            headless: 是否使用无头模式
        """
        self.driver = None
        self.headless = headless
        self.crawled_ids = set()
        
    def _init_driver(self):
        """初始化Chrome浏览器驱动"""
        try:
            logger.info("正在初始化Chrome浏览器驱动...")
            
            chrome_options = Options()
            
            # 无头模式配置
            if self.headless:
                chrome_options.add_argument('--headless')
                logger.info("使用无头模式（后台运行）")
            
            # 其他优化配置
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 自动下载并安装ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置隐式等待
            self.driver.implicitly_wait(5)
            
            logger.info("✓ Chrome浏览器驱动初始化成功")
            
        except Exception as e:
            logger.error(f"✗ Chrome浏览器驱动初始化失败: {e}")
            raise
    
    def fetch_page(self, url: str, page_num: int = 1, filters: Optional[Dict] = None) -> Optional[str]:
        """
        获取页面HTML
        
        Args:
            url: 目标URL
            page_num: 页码
            filters: 筛选条件字典
            
        Returns:
            页面HTML，失败返回None
        """
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                # 构建 URL 参数
                params = []
                
                # 添加页码（使用current参数）
                params.append(f"current={page_num}")
                
                # 添加筛选条件
                if filters:
                    if filters.get('location'):
                        params.append(f"location={filters['location']}")
                    if filters.get('category'):
                        params.append(f"category={filters['category']}")
                    if filters.get('project'):
                        params.append(f"project={filters['project']}")
                
                # 构建完整URL
                if params:
                    full_url = f"{url}?{'&'.join(params)}"
                else:
                    full_url = url
                
                logger.info(f"正在访问: {full_url} (尝试 {attempt}/{Config.MAX_RETRIES})")
                
                # 访问页面
                self.driver.get(full_url)
                
                # 等待岗位列表加载完成
                try:
                    WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-id]"))
                    )
                    logger.info("✓ 页面加载完成，岗位列表已出现")
                except TimeoutException:
                    logger.warning("⚠ 等待超时，但继续尝试解析页面")
                
                # 额外等待，确保所有内容加载
                time.sleep(2)
                
                # 获取页面HTML
                html = self.driver.page_source
                logger.info(f"✓ 获取页面HTML成功 (大小: {len(html)} bytes)")
                
                return html
                
            except WebDriverException as e:
                logger.error(f"✗ 页面加载失败: {e} (尝试 {attempt}/{Config.MAX_RETRIES})")
                
                if attempt < Config.MAX_RETRIES:
                    wait_time = random.uniform(*Config.REQUEST_DELAY) * attempt
                    logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                    time.sleep(wait_time)
        
        logger.error("✗ 页面获取失败，已达最大重试次数")
        return None
    
    def parse_job_list(self, html_content: str) -> List[Dict]:
        """
        解析岗位列表页（复用原逻辑，增强错误处理）
        
        Args:
            html_content: HTML内容
            
        Returns:
            岗位信息列表
        """
        if not html_content:
            logger.warning("HTML内容为空，跳过解析")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # 查找所有岗位卡片
        job_cards = soup.find_all('a', attrs={'data-id': True})
        logger.info(f"找到 {len(job_cards)} 个岗位卡片")
        
        for idx, card in enumerate(job_cards, 1):
            try:
                job_data = self._parse_single_card(card)
                
                # 去重检查
                if job_data['system_id'] in self.crawled_ids:
                    logger.debug(f"[{idx}] 岗位 {job_data['system_id']} 已存在，跳过")
                    continue
                
                self.crawled_ids.add(job_data['system_id'])
                results.append(job_data)
                logger.info(f"[{idx}] ✓ {job_data['title']} ({job_data['location']}) - ID: {job_data['business_id']}")
                
            except Exception as e:
                logger.error(f"[{idx}] ✗ 解析失败: {e}")
                continue
        
        return results
    
    def _parse_single_card(self, card) -> Dict:
        """
        解析单个岗位卡片（增强版）
        
        Args:
            card: BeautifulSoup标签对象
            
        Returns:
            岗位信息字典
        """
        # 基础信息
        system_id = card.get('data-id', 'N/A')
        href = card.get('href', '')
        detail_url = f"{Config.BASE_URL}{href}" if href else 'N/A'
        
        # 标题
        title_elem = card.find('span', class_='positionItem-title-text')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        # 元数据区域
        metadata = []
        subtitle_div = card.find('div', class_='positionItem-subTitle')
        if subtitle_div:
            # 获取所有span（排除分隔符）
            spans = subtitle_div.find_all('span', recursive=False)
            for span in spans:
                text = span.get_text(strip=True)
                if text and not span.get('class', [''])[0].endswith('Devider'):
                    metadata.append(text)
        
        # 提取business_id
        business_id = 'N/A'
        for item in metadata:
            if '职位 ID' in item or '职位ID' in item:
                business_id = item.replace('职位 ID：', '').replace('职位ID：', '').strip()
                break
        
        # 构建结构化数据（移除description，因为详情页有job_description）
        return {
            'title': title,
            'system_id': system_id,
            'business_id': business_id,
            'location': metadata[0] if len(metadata) > 0 else 'N/A',
            'type': metadata[1] if len(metadata) > 1 else 'N/A',
            'category': metadata[2] if len(metadata) > 2 else 'N/A',
            'program': metadata[3] if len(metadata) > 3 else 'N/A',
            'url': detail_url,
            'crawl_time': datetime.now().isoformat()
        }
    
    def fetch_job_detail(self, detail_url: str) -> Optional[Dict]:
        """
        爬取岗位详情页
        
        Args:
            detail_url: 详情页URL
            
        Returns:
            详情信息字典，失败返回None
        """
        try:
            # 访问详情页
            self.driver.get(detail_url)
            
            # 等待页面加载
            try:
                WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "block-title"))
                )
            except TimeoutException:
                logger.warning("⚠ 详情页加载超时")
            
            # 额外等待
            time.sleep(1)
            
            # 解析详情页
            return self.parse_job_detail()
            
        except Exception as e:
            logger.error(f"获取详情页失败: {e}")
            return None
    
    def parse_job_detail(self) -> Dict:
        """
        解析岗位详情页（从当前driver页面）
        
        Returns:
            包含详细信息的字典
        """
        detail_info = {
            'job_description': 'N/A',
            'job_requirements': 'N/A',
            'team_intro': 'N/A'
        }
        
        try:
            # 查找所有区块标题
            blocks = self.driver.find_elements(By.CLASS_NAME, "block-title")
            
            for block in blocks:
                try:
                    title = block.text.strip()
                    
                    # 找到对应的内容区块（下一个兄弟元素）
                    content_elem = block.find_element(By.XPATH, "following-sibling::div[@class='block-content']")
                    content = content_elem.text.strip()
                    
                    # 根据标题保存内容
                    if '职位描述' in title:
                        detail_info['job_description'] = content
                        logger.debug(f"✓ 提取职位描述: {len(content)} 字符")
                    elif '职位要求' in title:
                        detail_info['job_requirements'] = content
                        logger.debug(f"✓ 提取职位要求: {len(content)} 字符")
                    elif '团队介绍' in title:
                        detail_info['team_intro'] = content
                        logger.debug(f"✓ 提取团队介绍: {len(content)} 字符")
                        
                except Exception as e:
                    logger.debug(f"解析区块 '{title if 'title' in locals() else 'unknown'}' 失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"解析详情页失败: {e}")
        
        return detail_info
    
    def crawl_all_pages(self, start_page: int = 1, end_page: int = 2) -> List[Dict]:
        """
        爬取多页岗位数据
        
        Args:
            start_page: 开始页码
            end_page: 结束页码（包含）
            
        Returns:
            所有岗位信息列表
        """
        all_jobs = []
        
        try:
            # 初始化浏览器
            self._init_driver()
            
            # 准备筛选条件
            filters = {}
            if Config.FILTER_LOCATION:
                filters['location'] = Config.FILTER_LOCATION
            if Config.FILTER_CATEGORY:
                filters['category'] = Config.FILTER_CATEGORY
            if Config.FILTER_PROJECT:
                filters['project'] = Config.FILTER_PROJECT
            
            # 显示筛选信息
            if filters:
                logger.info(f"\n应用筛选条件: {filters}")
            
            for page in range(start_page, end_page + 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"开始爬取第 {page} 页")
                logger.info(f"{'='*60}")
                
                # 获取页面（传入筛选条件）
                html = self.fetch_page(Config.CAMPUS_URL, page, filters if filters else None)
                if not html:
                    logger.error(f"第 {page} 页获取失败，停止爬取")
                    break
                
                # 解析岗位
                jobs = self.parse_job_list(html)
                
                if not jobs:
                    logger.info(f"第 {page} 页没有找到新岗位，停止爬取")
                    break
                
                # 如果开启了详情页爬取，访问每个岗位的详情页
                if Config.CRAWL_DETAIL:
                    logger.info(f"\n开始爬取详情页（共 {len(jobs)} 个岗位）...")
                    for idx, job in enumerate(jobs, 1):
                        try:
                            logger.info(f"  [{idx}/{len(jobs)}] 正在获取: {job['title']}")
                            detail_info = self.fetch_job_detail(job['url'])
                            
                            if detail_info:
                                # 合并详情信息到岗位数据
                                job.update(detail_info)
                                logger.info(f"  [{idx}/{len(jobs)}] ✓ 详情获取成功")
                            else:
                                logger.warning(f"  [{idx}/{len(jobs)}] ⚠ 详情获取失败")
                            
                            # 详情页之间也要延时
                            if idx < len(jobs):
                                delay = random.uniform(1, 3)
                                time.sleep(delay)
                                
                        except Exception as e:
                            logger.error(f"  [{idx}/{len(jobs)}] ✗ 详情爬取异常: {e}")
                            continue
                    logger.info("详情页爬取完成\n")
                
                all_jobs.extend(jobs)
                logger.info(f"第 {page} 页解析完成，获得 {len(jobs)} 个岗位")
                
                # 检查是否达到结束页码
                if page >= end_page:
                    logger.info(f"已达到结束页码 {end_page}，停止爬取")
                    break
                
                # 如果当前页岗位数量少于10，说明是最后一页
                if len(jobs) < 10:
                    logger.info(f"当前页只有 {len(jobs)} 个岗位，已是最后一页")
                    break
                
                # 延时
                delay = random.uniform(*Config.REQUEST_DELAY)
                logger.info(f"等待 {delay:.2f} 秒后继续...\n")
            
        finally:
            # 确保浏览器关闭
            self.close()
        
        return all_jobs
    
    def save_results(self, jobs: List[Dict]):
        """
        保存爬取结果
        
        Args:
            jobs: 岗位信息列表
        """
        if not jobs:
            logger.warning("没有数据需要保存")
            return
        
        Config.OUTPUT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存为JSON
        json_file = Config.OUTPUT_DIR / f"bytedance_jobs_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON文件已保存: {json_file}")
        
        # 保存为CSV
        csv_file = Config.OUTPUT_DIR / f"bytedance_jobs_{timestamp}.csv"
        if jobs:
            keys = jobs[0].keys()
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(jobs)
            logger.info(f"✓ CSV文件已保存: {csv_file}")
        
        # 统计信息
        logger.info(f"\n{'='*60}")
        logger.info(f"爬取完成！共获得 {len(jobs)} 个岗位")
        logger.info(f"{'='*60}")
        
        # 简单统计
        locations = {}
        types = {}
        for job in jobs:
            loc = job.get('location', 'N/A')
            typ = job.get('type', 'N/A')
            locations[loc] = locations.get(loc, 0) + 1
            types[typ] = types.get(typ, 0) + 1
        
        logger.info("\n📍 地点分布:")
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
            logger.info(f"  {loc}: {count} 个岗位")
        
        logger.info("\n💼 类型分布:")
        for typ, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {typ}: {count} 个岗位")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ 浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")


# ========== 主函数 ==========
def main():
    """主程序入口"""
    logger.info("="*60)
    logger.info("字节跳动校园招聘岗位爬虫启动 (Selenium版本)")
    logger.info("="*60)
    
    try:
        # 创建爬虫实例
        crawler = ByteDanceSeleniumCrawler(headless=Config.HEADLESS)
        
        logger.info(f"\n配置信息:")
        logger.info(f"  目标URL: {Config.CAMPUS_URL}")
        logger.info(f"  页数范围: {Config.START_PAGE} - {Config.END_PAGE}")
        logger.info(f"  无头模式: {Config.HEADLESS}")
        logger.info(f"  爬取详情: {Config.CRAWL_DETAIL}")
        if Config.FILTER_LOCATION or Config.FILTER_CATEGORY or Config.FILTER_PROJECT:
            logger.info(f"  筛选条件:")
            if Config.FILTER_LOCATION:
                logger.info(f"    - 地点: {Config.FILTER_LOCATION}")
            if Config.FILTER_CATEGORY:
                logger.info(f"    - 类别: {Config.FILTER_CATEGORY}")
            if Config.FILTER_PROJECT:
                logger.info(f"    - 项目: {Config.FILTER_PROJECT}")
        logger.info(f"  输出目录: {Config.OUTPUT_DIR}")
        logger.info("")
        
        # 开始爬取（使用页数范围）
        jobs = crawler.crawl_all_pages(start_page=Config.START_PAGE, end_page=Config.END_PAGE)
        
        # 保存结果
        crawler.save_results(jobs)
        
        logger.info("\n✅ 任务完成!")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠ 用户中断爬虫")
    except Exception as e:
        logger.error(f"\n❌ 程序异常: {e}", exc_info=True)


if __name__ == "__main__":
    main()
