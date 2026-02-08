"""
美团校园招聘岗位爬虫 - Selenium版本
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
    BASE_URL = "https://zhaopin.meituan.com"
    CAMPUS_URL = f"{BASE_URL}/web/campus"
    DETAIL_URL_TEMPLATE = f"{BASE_URL}/web/position/detail?jobUnionId={{job_id}}&highlightType=campus"
    
    # 爬虫行为配置
    PAGE_LOAD_WAIT = 10  # 页面加载最大等待时间（秒）
    REQUEST_DELAY = (2, 5)  # 请求间隔（秒）
    MAX_RETRIES = 3  # 最大重试次数
    CRAWL_DETAIL = True  # 是否爬取详情页（职位描述等）
    
    # 页数范围配置
    START_PAGE = 1  # 开始页码
    END_PAGE = 49    # 结束页码（包含），总共49页
    
    # 输出配置
    OUTPUT_DIR = Path(__file__).parent / "output" / "meituan"
    LOG_DIR = Path(__file__).parent / "logs" / "meituan"
    
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
class MeituanSeleniumCrawler:
    """美团岗位爬虫 - Selenium版本"""
    
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
    
    def fetch_page(self, page_num: int = 1) -> Optional[str]:
        """
        获取指定页面HTML（使用URL参数）
        
        Args:
            page_num: 页码
            
        Returns:
            页面HTML，失败返回None
        """
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                # 构建URL（美团使用pageNo参数）
                url = f"{Config.CAMPUS_URL}?pageNo={page_num}"
                
                logger.info(f"正在访问: {url} (尝试 {attempt}/{Config.MAX_RETRIES})")
                
                # 访问页面
                self.driver.get(url)
                
                # 等待岗位列表加载完成
                try:
                    WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".position_list_item"))
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
        解析岗位列表页
        
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
        
        # 查找所有岗位卡片 (.position_list_item)
        job_cards = soup.find_all('div', class_='position_list_item')
        logger.info(f"找到 {len(job_cards)} 个岗位卡片")
        
        for idx, card in enumerate(job_cards, 1):
            try:
                job_data = self._parse_single_card(card)
                
                # 去重检查（基于job_union_id）
                job_id = job_data.get('job_union_id')
                if job_id in self.crawled_ids:
                    logger.debug(f"[{idx}] 岗位 {job_id} 已存在，跳过")
                    continue
                
                self.crawled_ids.add(job_id)
                results.append(job_data)
                logger.info(f"[{idx}] ✓ {job_data['title']} ({job_data['location']})")
                
            except Exception as e:
                logger.error(f"[{idx}] ✗ 解析失败: {e}")
                continue
        
        return results
    
    def _parse_single_card(self, card) -> Dict:
        """
        解析单个岗位卡片
        
        Args:
            card: BeautifulSoup标签对象
            
        Returns:
            岗位信息字典
        """
        # 提取job_union_id（用于构建详情页URL）
        job_union_id = card.get('data-jobunionid', 'N/A')
        
        # 标题 (.postion_name .title) 注意是postion不是position
        title_elem = card.find('div', class_='title')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        # 提取split_line_box_item标签（包含地点、类型等）
        split_items = card.find_all('div', class_='split_line_box_item')
        location = split_items[0].get_text(strip=True) if len(split_items) > 0 else 'N/A'
        job_type = split_items[1].get_text(strip=True) if len(split_items) > 1 else 'N/A'
        
        # 构建结构化数据
        return {
            'job_union_id': job_union_id,
            'title': title,
            'location': location,
            'job_type': job_type,
            'crawl_time': datetime.now().isoformat()
        }
    
    def fetch_job_detail(self, job_union_id: str) -> Optional[Dict]:
        """
        爬取岗位详情页（通过新标签页）
        
        Args:
            job_union_id: 岗位唯一ID
            
        Returns:
            详情信息字典，失败返回None
        """
        main_window = None
        try:
            # 记录当前窗口句柄
            main_window = self.driver.current_window_handle
            
            # 构建详情页URL
            detail_url = Config.DETAIL_URL_TEMPLATE.format(job_id=job_union_id)
            
            # 在新标签页打开详情页
            self.driver.execute_script(f"window.open('{detail_url}', '_blank');")
            time.sleep(2)
            
            # 切换到新打开的标签页
            windows = self.driver.window_handles
            if len(windows) > 1:
                # 切换到最新的标签页
                self.driver.switch_to.window(windows[-1])
                
                # 等待详情页加载
                WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "positin_detail_info_item"))
                )
                time.sleep(1)
                
                # 解析详情页
                detail_info = self.parse_job_detail()
                
                # 关闭详情页标签
                self.driver.close()
                
                # 切回主窗口
                self.driver.switch_to.window(main_window)
                
                return detail_info
            else:
                logger.warning("未检测到新标签页打开")
                return None
            
        except Exception as e:
            logger.error(f"获取详情页失败: {e}")
            # 确保切回主窗口
            try:
                if main_window:
                    self.driver.switch_to.window(main_window)
            except:
                pass
            return None
    
    def parse_job_detail(self) -> Dict:
        """
        解析岗位详情页（从当前driver页面）
        
        Returns:
            包含详细信息的字典
        """
        detail_info = {
            'job_responsibilities': 'N/A',
            'job_requirements': 'N/A',
            'preferred_qualifications': 'N/A',
            'job_highlights': 'N/A'
        }
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 查找所有详情区块 (.positin_detail_info_item)
            detail_items = soup.find_all('div', class_='positin_detail_info_item')
            
            for item in detail_items:
                # 获取区块标题
                title_elem = item.find('div', class_='title')
                if not title_elem:
                    continue
                
                title_text = title_elem.get_text(strip=True)
                
                # 获取title之后的内容（兄弟元素）
                content_elem = title_elem.find_next_sibling('div')
                if not content_elem:
                    continue
                
                content = content_elem.get_text(strip=True)
                
                # 根据标题匹配对应字段
                if '岗位职责' in title_text:
                    detail_info['job_responsibilities'] = content
                    logger.debug(f"✓ 提取岗位职责: {len(content)} 字符")
                
                elif '岗位基本要求' in title_text:
                    detail_info['job_requirements'] = content
                    logger.debug(f"✓ 提取岗位要求: {len(content)} 字符")
                
                elif '具备以下条件优先' in title_text:
                    detail_info['preferred_qualifications'] = content
                    logger.debug(f"✓ 提取加分项: {len(content)} 字符")
                
                elif '岗位亮点' in title_text:
                    detail_info['job_highlights'] = content
                    logger.debug(f"✓ 提取岗位亮点: {len(content)} 字符")
                        
        except Exception as e:
            logger.error(f"解析详情页失败: {e}")
        
        return detail_info
    
    def crawl_all_pages(self, start_page: int = 1, end_page: int = 2) -> List[Dict]:
        """
        爬取多页岗位数据（使用URL参数翻页）
        
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
            
            for page in range(start_page, end_page + 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"开始爬取第 {page} 页")
                logger.info(f"{'='*60}")
                
                # 获取页面
                html = self.fetch_page(page)
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
                    self._crawl_details_for_page(jobs)
                
                all_jobs.extend(jobs)
                logger.info(f"第 {page} 页解析完成，获得 {len(jobs)} 个岗位")
                
                # 检查是否达到结束页码
                if page >= end_page:
                    logger.info(f"已达到结束页码 {end_page}，停止爬取")
                    break
                
                # 页面之间延时
                delay = random.uniform(*Config.REQUEST_DELAY)
                logger.info(f"等待 {delay:.2f} 秒后继续爬取下一页...\n")
                time.sleep(delay)
            
        finally:
            # 确保浏览器关闭
            self.close()
        
        return all_jobs
    
    def _crawl_details_for_page(self, jobs: List[Dict]):
        """
        爬取一页的所有岗位详情
        
        Args:
            jobs: 岗位列表
        """
        logger.info(f"\n开始爬取详情页（共 {len(jobs)} 个岗位）...")
        for idx, job in enumerate(jobs, 1):
            try:
                logger.info(f"  [{idx}/{len(jobs)}] 正在获取: {job['title']}")
                detail_info = self.fetch_job_detail(job['job_union_id'])
                
                if detail_info:
                    # 合并详情信息到岗位数据
                    job.update(detail_info)
                    logger.info(f"  [{idx}/{len(jobs)}] ✓ 详情获取成功")
                else:
                    logger.warning(f"  [{idx}/{len(jobs)}] ⚠ 详情获取失败")
                
                # 详情页之间延时
                if idx < len(jobs):
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"  [{idx}/{len(jobs)}] ✗ 详情爬取异常: {e}")
                continue
        logger.info("详情页爬取完成\n")
    
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
        json_file = Config.OUTPUT_DIR / f"meituan_jobs_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON文件已保存: {json_file}")
        
        # 保存为CSV
        csv_file = Config.OUTPUT_DIR / f"meituan_jobs_{timestamp}.csv"
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
        job_types = {}
        
        for job in jobs:
            loc = job.get('location', 'N/A')
            typ = job.get('job_type', 'N/A')
            
            locations[loc] = locations.get(loc, 0) + 1
            job_types[typ] = job_types.get(typ, 0) + 1
        
        logger.info("\n📍 地点分布:")
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {loc}: {count} 个岗位")
        
        logger.info("\n📝 类型分布:")
        for typ, count in sorted(job_types.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {typ}: {count} 个岗位")
        
        # 统计详情页爬取成功率
        if Config.CRAWL_DETAIL:
            detail_success = sum(1 for job in jobs if job.get('job_responsibilities', 'N/A') != 'N/A')
            logger.info(f"\n📊 详情页爬取:")
            logger.info(f"  成功: {detail_success}/{len(jobs)} ({detail_success*100//len(jobs) if len(jobs) > 0 else 0}%)")
    
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
    logger.info("美团校园招聘岗位爬虫启动 (Selenium版本)")
    logger.info("="*60)
    
    try:
        # 创建爬虫实例
        crawler = MeituanSeleniumCrawler(headless=Config.HEADLESS)
        
        logger.info(f"\n配置信息:")
        logger.info(f"  目标URL: {Config.CAMPUS_URL}")
        logger.info(f"  页数范围: {Config.START_PAGE} - {Config.END_PAGE}")
        logger.info(f"  无头模式: {Config.HEADLESS}")
        logger.info(f"  爬取详情: {Config.CRAWL_DETAIL}")
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
