"""
Tencent Job Scraper
Supports dynamic loading, AJAX pagination, and detail scraping.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import List, Dict, Optional
from base_scraper import BaseScraper

# ========== Config ==========
class Config:
    """Tencent specific configuration."""
    BASE_URL = "https://join.qq.com"
    CAMPUS_URL = f"{BASE_URL}/post.html"
    
    # Crawler behavior
    PAGE_LOAD_WAIT = 10
    REQUEST_DELAY = (2, 5)
    MAX_RETRIES = 3
    CRAWL_DETAIL = True
    
    # Page range
    START_PAGE = 1
    END_PAGE = 5
    
    # Filters
    FILTER_QUERY = "p_2,p_104"  # p_2=应届, p_104=技术类
    
    HEADLESS = True

class TencentScraper(BaseScraper):
    """Tencent specific scraper."""
    
    def __init__(self, headless: bool = Config.HEADLESS):
        super().__init__("tencent", headless)
        
    def fetch_first_page(self, query: Optional[str] = None) -> Optional[str]:
        """Fetches the first page of jobs."""
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                url = f"{Config.CAMPUS_URL}?query={query}" if query else Config.CAMPUS_URL
                self.logger.info(f"Accessing: {url} (Attempt {attempt}/{Config.MAX_RETRIES})")
                self.driver.get(url)
                
                try:
                    WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.post_box"))
                    )
                except TimeoutException:
                    self.logger.warning("⚠ Wait timed out, trying to parse anyway.")
                
                time.sleep(2)
                return self.driver.page_source
            except WebDriverException as e:
                self.logger.error(f"✗ First page load failed: {e}")
                if attempt < Config.MAX_RETRIES:
                    self.random_delay(Config.REQUEST_DELAY[0], Config.REQUEST_DELAY[1])
        return None

    def parse_job_list(self, html: str) -> List[Dict]:
        """Parses job list from HTML."""
        if not html: return []
        soup = BeautifulSoup(html, 'html.parser')
        job_cards = soup.find_all('li', class_='post_box')
        results = []
        
        for card in job_cards:
            try:
                job_data = self._parse_single_card(card)
                job_id = f"{job_data['title']}_{job_data['location']}"
                if job_id in self.crawled_ids: continue
                self.crawled_ids.add(job_id)
                results.append(job_data)
            except Exception as e:
                self.logger.error(f"✗ Failed to parse card: {e}")
        return results

    def _parse_single_card(self, card) -> Dict:
        """Parses a single job card."""
        title_elem = card.find('div', class_='post_title')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        tags = []
        tag_box = card.find('div', class_='post_tag_box')
        if tag_box:
            tag_elems = tag_box.find_all('div', class_='post_tag')
            for tag_elem in tag_elems:
                tag_text = tag_elem.get_text(strip=True).replace('｜', '').strip()
                if tag_text: tags.append(tag_text)
        
        category = tags[0] if len(tags) > 0 else 'N/A'
        job_type = tags[1] if len(tags) > 1 else 'N/A'
        department = tags[2] if len(tags) > 2 else 'N/A'
        
        location = 'N/A'
        site_box = card.find('div', class_='site_box')
        if site_box:
            site_elem = site_box.find('div', class_='site')
            location = site_elem.get_text(strip=True) if site_elem else 'N/A'
        
        return {
            'title': title,
            'category': category,
            'job_type': job_type,
            'department': department,
            'location': location,
            'crawl_time': datetime.now().isoformat()
        }

    def fetch_job_detail(self, job_title: str) -> Optional[Dict]:
        """Fetches job details by clicking on the job title."""
        main_window = self.driver.current_window_handle
        try:
            job_element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@class='post_title' and text()='{job_title}']"))
            )
            job_element.click()
            time.sleep(2)
            
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[-1])
                WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "subtitle"))
                )
                time.sleep(1)
                detail_info = self._parse_detail_page()
                self.driver.close()
                self.driver.switch_to.window(main_window)
                return detail_info
            return None
        except Exception as e:
            self.logger.error(f"Failed to fetch detail for {job_title}: {e}")
            try: self.driver.switch_to.window(main_window)
            except: pass
            return None

    def _parse_detail_page(self) -> Dict:
        """Parses the detail page content."""
        detail_info = {
            'job_description': 'N/A', 'job_requirements': 'N/A',
            'bonus_notes': 'N/A', 'interview_cities': 'N/A', 'department': 'N/A'
        }
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        subtitles = soup.find_all('div', class_='subtitle')
        for subtitle in subtitles:
            title_text = subtitle.get_text(strip=True)
            content_elem = subtitle.find_next_sibling('div')
            if not content_elem: continue
            content = content_elem.get_text(strip=True)
            
            if '岗位描述' in title_text: detail_info['job_description'] = content
            elif '岗位要求' in title_text: detail_info['job_requirements'] = content
            elif '加分项或注意事项' in title_text: detail_info['bonus_notes'] = content
            elif '参加面试的城市' in title_text: detail_info['interview_cities'] = content
            elif '招聘部门' in title_text: detail_info['department'] = content
        return detail_info

    def next_page(self) -> bool:
        """Clicks the next page button using AJAX."""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            next_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-next"))
            )
            if "disabled" in next_button.get_attribute("class"): return False
            self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
            return True
        except: return False

    def crawl(self):
        """Main crawl logic."""
        all_jobs = []
        try:
            self.init_driver()
            html = self.fetch_first_page(Config.FILTER_QUERY)
            if not html: return []
            
            for page in range(Config.START_PAGE, Config.END_PAGE + 1):
                self.logger.info(f"--- Page {page} ---")
                if page > Config.START_PAGE:
                    if not self.next_page(): break
                    html = self.driver.page_source
                
                jobs = self.parse_job_list(html)
                if not jobs: break
                
                if Config.CRAWL_DETAIL:
                    for job in jobs:
                        self.logger.info(f"Fetching detail for: {job['title']}")
                        detail = self.fetch_job_detail(job['title'])
                        if detail: job.update(detail)
                        self.random_delay(1, 3)
                
                all_jobs.extend(jobs)
                self.random_delay(Config.REQUEST_DELAY[0], Config.REQUEST_DELAY[1])
        finally:
            self.close()
        
        self.save_results(all_jobs)
        return all_jobs

def main():
    scraper = TencentScraper()
    scraper.crawl()

if __name__ == "__main__":
    main()
