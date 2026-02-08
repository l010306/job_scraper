"""
腾讯校园招聘岗位爬虫 - Selenium版本
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
    BASE_URL = "https://join.qq.com"
    CAMPUS_URL = f"{BASE_URL}/post.html"
    
    # 爬虫行为配置
    PAGE_LOAD_WAIT = 10  # 页面加载最大等待时间（秒）
    REQUEST_DELAY = (2, 5)  # 请求间隔（秒）
    MAX_RETRIES = 3  # 最大重试次数
    CRAWL_DETAIL = True  # 是否爬取详情页（职位描述等）
    
    # 页数范围配置
    START_PAGE = 1  # 开始页码
    END_PAGE = 5    # 结束页码（包含）
    
    # 筛选配置（留空表示不筛选）
    # 使用URL查询参数格式，例如: "p_2,p_104" (原URL中的query参数)
    FILTER_QUERY = "p_2,p_104"  # p_2=应届, p_104=技术类
    
    # 常用筛选选项参考（注释）
    # p_2 = 应届实习
    # p_3 = 日常实习
    # p_104 = 技术类
    # p_105 = 产品类
    # p_106 = 设计类
    # 可以组合使用，用逗号分隔，例如: "p_2,p_104"
    
    # 输出配置
    OUTPUT_DIR = Path(__file__).parent / "output" / "tencent"
    LOG_DIR = Path(__file__).parent / "logs" / "tencent"
    
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
class TencentSeleniumCrawler:
    """腾讯岗位爬虫 - Selenium版本"""
    
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
    
    def fetch_page(self, query_filter: Optional[str] = None) -> Optional[str]:
        """
        获取第一页HTML（仅用于初始化）
        
        Args:
            query_filter: 筛选条件（query参数）
            
        Returns:
            页面HTML，失败返回None
        """
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                # 构建 URL（只访问第一页）
                if query_filter:
                    full_url = f"{Config.CAMPUS_URL}?query={query_filter}"
                else:
                    full_url = Config.CAMPUS_URL
                
                logger.info(f"正在访问: {full_url} (尝试 {attempt}/{Config.MAX_RETRIES})")
                
                # 访问页面
                self.driver.get(full_url)
                
                # 等待岗位列表加载完成
                try:
                    WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.post_box"))
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
        
        # 查找所有岗位卡片 (li.post_box)
        job_cards = soup.find_all('li', class_='post_box')
        logger.info(f"找到 {len(job_cards)} 个岗位卡片")
        
        for idx, card in enumerate(job_cards, 1):
            try:
                job_data = self._parse_single_card(card)
                
                # 去重检查（基于标题+地点）
                job_id = f"{job_data['title']}_{job_data['location']}"
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
        # 标题 (.post_title)
        title_elem = card.find('div', class_='post_title')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        # 标签信息 (.post_tag_box 下的 .post_tag)
        tags = []
        tag_box = card.find('div', class_='post_tag_box')
        if tag_box:
            tag_elems = tag_box.find_all('div', class_='post_tag')
            for tag_elem in tag_elems:
                tag_text = tag_elem.get_text(strip=True)
                # 移除分隔符
                tag_text = tag_text.replace('｜', '').strip()
                if tag_text:
                    tags.append(tag_text)
        
        # 从标签中提取信息
        category = tags[0] if len(tags) > 0 else 'N/A'  # 职位类别（如：技术）
        job_type = tags[1] if len(tags) > 1 else 'N/A'  # 实习类型（如：应届实习）
        department = tags[2] if len(tags) > 2 else 'N/A'  # 事业群（如：TEG）
        
        # 地点信息 (.site_box 下的 .site)
        location = 'N/A'
        site_box = card.find('div', class_='site_box')
        if site_box:
            site_elem = site_box.find('div', class_='site')
            location = site_elem.get_text(strip=True) if site_elem else 'N/A'
        
        # 构建结构化数据
        return {
            'title': title,
            'category': category,
            'job_type': job_type,
            'department': department,
            'location': location,
            'crawl_time': datetime.now().isoformat()
        }
    
    def fetch_job_detail(self, job_title: str) -> Optional[Dict]:
        """
        爬取岗位详情页（通过点击岗位卡片）
        
        Args:
            job_title: 岗位标题
            
        Returns:
            详情信息字典，失败返回None
        """
        main_window = None
        try:
            # 记录当前窗口句柄
            main_window = self.driver.current_window_handle
            
            # 查找并点击对应的岗位标题
            job_element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@class='post_title' and text()='{job_title}']" ))
            )
            job_element.click()
            
            # 等待新标签页打开
            time.sleep(2)
            
            # 切换到新打开的标签页
            windows = self.driver.window_handles
            if len(windows) > 1:
                # 切换到最新的标签页
                self.driver.switch_to.window(windows[-1])
                
                # 等待详情页加载
                WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "subtitle"))
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
            'job_description': 'N/A',
            'job_requirements': 'N/A',
            'bonus_notes': 'N/A',
            'interview_cities': 'N/A',
            'department': 'N/A'
        }
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 查找所有区块标题 (.subtitle)
            subtitles = soup.find_all('div', class_='subtitle')
            
            for subtitle in subtitles:
                title_text = subtitle.get_text(strip=True)
                
                # 根据标题提取对应内容
                if '岗位描述' in title_text:
                    content_elem = subtitle.find_next_sibling('div', class_='text_box')
                    if content_elem:
                        detail_info['job_description'] = content_elem.get_text(strip=True)
                        logger.debug(f"✓ 提取岗位描述: {len(detail_info['job_description'])} 字符")
                
                elif '岗位要求' in title_text:
                    content_elem = subtitle.find_next_sibling('div', class_='text_box')
                    if content_elem:
                        detail_info['job_requirements'] = content_elem.get_text(strip=True)
                        logger.debug(f"✓ 提取岗位要求: {len(detail_info['job_requirements'])} 字符")
                
                elif '加分项或注意事项' in title_text:
                    content_elem = subtitle.find_next_sibling('div', class_='text_box')
                    if content_elem:
                        detail_info['bonus_notes'] = content_elem.get_text(strip=True)
                        logger.debug(f"✓ 提取加分项: {len(detail_info['bonus_notes'])} 字符")
                
                elif '参加面试的城市' in title_text:
                    # 可能是 .detail_text 或其他 class
                    content_elem = subtitle.find_next_sibling('div')
                    if content_elem:
                        detail_info['interview_cities'] = content_elem.get_text(strip=True)
                        logger.debug(f"✓ 提取面试城市: {detail_info['interview_cities']}")
                
                elif '招聘部门和工作地' in title_text:
                    # 尝试获取下一个兄弟元素
                    content_elem = subtitle.find_next_sibling('div')
                    if content_elem:
                        detail_info['department'] = content_elem.get_text(strip=True)
                        logger.debug(f"✓ 提取招聘部门: {detail_info['department']}")
                        
        except Exception as e:
            logger.error(f"解析详情页失败: {e}")
        
        return detail_info
    
    def crawl_all_pages(self, start_page: int = 1, end_page: int = 2) -> List[Dict]:
        """
        爬取多页岗位数据
        
        注意：腾讯使用AJAX分页，不支持URL参数翻页，必须通过点击按钮实现
        
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
            query_filter = Config.FILTER_QUERY if Config.FILTER_QUERY else None
            
            # 显示筛选信息
            if query_filter:
                logger.info(f"\n应用筛选条件: query={query_filter}")
            
            # 第一页：直接访问
            logger.info(f"\n{'='*60}")
            logger.info(f"开始爬取第 {start_page} 页")
            logger.info(f"{'='*60}")
            
            html = self.fetch_page(query_filter)
            if not html:
                logger.error(f"第 {start_page} 页获取失败，停止爬取")
                return all_jobs
            
            # 解析第一页岗位
            jobs = self.parse_job_list(html)
            if not jobs:
                logger.info(f"第 {start_page} 页没有找到岗位")
                return all_jobs
            
            # 爬取详情页
            if Config.CRAWL_DETAIL:
                self._crawl_details_for_page(jobs)
            
            all_jobs.extend(jobs)
            logger.info(f"第 {start_page} 页解析完成，获得 {len(jobs)} 个岗位")
            
            # 如果只爬一页或已达结束页，直接返回
            if start_page >= end_page:
                logger.info(f"已达到结束页码 {end_page}，停止爬取")
                return all_jobs
            
            # 后续页面：通过点击按钮翻页
            for page in range(start_page + 1, end_page + 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"开始爬取第 {page} 页")
                logger.info(f"{'='*60}")
                
                # 滚动到页面底部，使分页按钮可见
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"滚动页面失败: {e}")
                
                # 检查"下一页"按钮是否存在且可用
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-next"))
                    )
                    
                    # 检查按钮是否被禁用
                    if "disabled" in next_button.get_attribute("class"):
                        logger.info("下一页按钮已禁用，已是最后一页")
                        break
                    
                    # 使用JavaScript点击（更可靠）
                    self.driver.execute_script("arguments[0].click();", next_button)
                    logger.info("✓ 已点击下一页按钮")
                    
                    # 等待AJAX加载完成
                    time.sleep(3)
                    
                    # 等待新内容加载（岗位列表刷新）
                    try:
                        # 等待岗位列表重新出现
                        WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "li.post_box"))
                        )
                        logger.info("✓ 新页面内容加载完成")
                    except TimeoutException:
                        logger.warning("⚠ 等待新内容加载超时")
                    
                    # 额外等待确保内容稳定
                    time.sleep(2)
                    
                except TimeoutException:
                    logger.error("未找到下一页按钮，停止爬取")
                    break
                except Exception as e:
                    logger.error(f"点击下一页按钮失败: {e}")
                    break
                
                # 获取当前页面HTML
                html = self.driver.page_source
                
                # 解析岗位
                jobs = self.parse_job_list(html)
                
                if not jobs:
                    logger.info(f"第 {page} 页没有找到新岗位，停止爬取")
                    break
                
                # 爬取详情页
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
                detail_info = self.fetch_job_detail(job['title'])
                
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
        json_file = Config.OUTPUT_DIR / f"tencent_jobs_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON文件已保存: {json_file}")
        
        # 保存为CSV
        csv_file = Config.OUTPUT_DIR / f"tencent_jobs_{timestamp}.csv"
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
        categories = {}
        job_types = {}
        departments = {}
        
        for job in jobs:
            loc = job.get('location', 'N/A')
            cat = job.get('category', 'N/A')
            typ = job.get('job_type', 'N/A')
            dept = job.get('department', 'N/A')
            
            locations[loc] = locations.get(loc, 0) + 1
            categories[cat] = categories.get(cat, 0) + 1
            job_types[typ] = job_types.get(typ, 0) + 1
            departments[dept] = departments.get(dept, 0) + 1
        
        logger.info("\n📍 地点分布:")
        for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
            logger.info(f"  {loc}: {count} 个岗位")
        
        logger.info("\n💼 类别分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {cat}: {count} 个岗位")
        
        logger.info("\n📝 类型分布:")
        for typ, count in sorted(job_types.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {typ}: {count} 个岗位")
        
        logger.info("\n🏢 事业群分布:")
        for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {dept}: {count} 个岗位")
        
        # 统计详情页爬取成功率
        if Config.CRAWL_DETAIL:
            detail_success = sum(1 for job in jobs if job.get('job_description', 'N/A') != 'N/A')
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
    logger.info("腾讯校园招聘岗位爬虫启动 (Selenium版本)")
    logger.info("="*60)
    
    try:
        # 创建爬虫实例
        crawler = TencentSeleniumCrawler(headless=Config.HEADLESS)
        
        logger.info(f"\n配置信息:")
        logger.info(f"  目标URL: {Config.CAMPUS_URL}")
        logger.info(f"  页数范围: {Config.START_PAGE} - {Config.END_PAGE}")
        logger.info(f"  无头模式: {Config.HEADLESS}")
        logger.info(f"  爬取详情: {Config.CRAWL_DETAIL} (当前版本暂不支持腾讯详情页)")
        if Config.FILTER_QUERY:
            logger.info(f"  筛选条件: query={Config.FILTER_QUERY}")
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
