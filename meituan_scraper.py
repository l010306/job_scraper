"""
Meituan Job Scraper
Supports dynamic loading, error handling, and detail scraping.
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
    """Meituan specific configuration."""
    BASE_URL = "https://zhaopin.meituan.com"
    CAMPUS_URL = f"{BASE_URL}/web/campus"
    DETAIL_URL_TEMPLATE = f"{BASE_URL}/web/position/detail?jobUnionId={{job_id}}&highlightType=campus"
    
    # Crawler behavior
    PAGE_LOAD_WAIT = 10
    REQUEST_DELAY = (2, 5)
    MAX_RETRIES = 3
    CRAWL_DETAIL = True
    
    # Page range
    START_PAGE = 1
    END_PAGE = 49
    
    HEADLESS = True

class MeituanScraper(BaseScraper):
    """Meituan specific scraper."""
    
    def __init__(self, headless: bool = Config.HEADLESS):
        super().__init__("meituan", headless)
        
    def fetch_page_html(self, page_num: int) -> Optional[str]:
        """Fetches page HTML with pageNo parameter."""
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                url = f"{Config.CAMPUS_URL}?pageNo={page_num}"
                self.logger.info(f"Accessing: {url} (Attempt {attempt}/{Config.MAX_RETRIES})")
                
                self.driver.get(url)
                
                try:
                    WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".position_list_item"))
                    )
                except TimeoutException:
                    self.logger.warning("⚠ Wait timed out, trying to parse anyway.")
                
                time.sleep(2)
                return self.driver.page_source
                
            except WebDriverException as e:
                self.logger.error(f"✗ Page load failed: {e}")
                if attempt < Config.MAX_RETRIES:
                    self.random_delay(Config.REQUEST_DELAY[0], Config.REQUEST_DELAY[1])
        return None

    def parse_job_list(self, html: str) -> List[Dict]:
        """Parses job list from HTML."""
        if not html: return []
        soup = BeautifulSoup(html, 'html.parser')
        job_cards = soup.find_all('div', class_='position_list_item')
        results = []
        
        for card in job_cards:
            try:
                job_data = self._parse_single_card(card)
                job_id = job_data.get('job_union_id')
                if job_id in self.crawled_ids: continue
                self.crawled_ids.add(job_id)
                results.append(job_data)
            except Exception as e:
                self.logger.error(f"✗ Failed to parse card: {e}")
        return results

    def _parse_single_card(self, card) -> Dict:
        """Parses a single job card."""
        job_union_id = card.get('data-jobunionid', 'N/A')
        title_elem = card.find('div', class_='title')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        split_items = card.find_all('div', class_='split_line_box_item')
        location = split_items[0].get_text(strip=True) if len(split_items) > 0 else 'N/A'
        job_type = split_items[1].get_text(strip=True) if len(split_items) > 1 else 'N/A'
        
        return {
            'job_union_id': job_union_id,
            'title': title,
            'location': location,
            'job_type': job_type,
            'crawl_time': datetime.now().isoformat()
        }

    def fetch_job_detail(self, job_union_id: str) -> Optional[Dict]:
        """Fetches job details in a new tab."""
        main_window = self.driver.current_window_handle
        try:
            detail_url = Config.DETAIL_URL_TEMPLATE.format(job_id=job_union_id)
            self.driver.execute_script(f"window.open('{detail_url}', '_blank');")
            time.sleep(2)
            
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[-1])
                WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "positin_detail_info_item"))
                )
                time.sleep(1)
                detail_info = self._parse_detail_page()
                self.driver.close()
                self.driver.switch_to.window(main_window)
                return detail_info
            return None
        except Exception as e:
            self.logger.error(f"Failed to fetch detail for {job_union_id}: {e}")
            try: self.driver.switch_to.window(main_window)
            except: pass
            return None

    def _parse_detail_page(self) -> Dict:
        """Parses the detail page content."""
        detail_info = {
            'job_responsibilities': 'N/A',
            'job_requirements': 'N/A',
            'preferred_qualifications': 'N/A',
            'job_highlights': 'N/A'
        }
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        items = soup.find_all('div', class_='positin_detail_info_item')
        for item in items:
            title_elem = item.find('div', class_='title')
            if not title_elem: continue
            title = title_elem.get_text(strip=True)
            content_elem = title_elem.find_next_sibling('div')
            if not content_elem: continue
            content = content_elem.get_text(strip=True)
            
            if '岗位职责' in title: detail_info['job_responsibilities'] = content
            elif '岗位基本要求' in title: detail_info['job_requirements'] = content
            elif '具备以下条件优先' in title: detail_info['preferred_qualifications'] = content
            elif '岗位亮点' in title: detail_info['job_highlights'] = content
        return detail_info

    def crawl(self):
        """Main crawl logic."""
        all_jobs = []
        try:
            self.init_driver()
            for page in range(Config.START_PAGE, Config.END_PAGE + 1):
                self.logger.info(f"--- Page {page} ---")
                html = self.fetch_page_html(page)
                if not html: break
                
                jobs = self.parse_job_list(html)
                if not jobs: break
                
                if Config.CRAWL_DETAIL:
                    for job in jobs:
                        self.logger.info(f"Fetching detail for: {job['title']}")
                        detail = self.fetch_job_detail(job['job_union_id'])
                        if detail: job.update(detail)
                        self.random_delay(1, 3)
                
                all_jobs.extend(jobs)
                self.random_delay(Config.REQUEST_DELAY[0], Config.REQUEST_DELAY[1])
        finally:
            self.close()
        
        self.save_results(all_jobs)
        return all_jobs

def main():
    scraper = MeituanScraper()
    scraper.crawl()

if __name__ == "__main__":
    main()
