"""
ByteDance Job Scraper
Supports dynamic loading, error handling, and detail scraping.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
from base_scraper import BaseScraper

# ========== Config ==========
class Config:
    """ByteDance specific configuration."""
    BASE_URL = "https://jobs.bytedance.com"
    CAMPUS_URL = f"{BASE_URL}/campus/position"
    
    # Crawler behavior
    PAGE_LOAD_WAIT = 10
    REQUEST_DELAY = (2, 5)
    MAX_RETRIES = 3
    CRAWL_DETAIL = True
    
    # Page range
    START_PAGE = 31
    END_PAGE = 45
    
    # Filters
    FILTER_LOCATION = ""     
    FILTER_CATEGORY = "6704215864629004552"     
    FILTER_PROJECT = "7194661644654577981,7194661126919358757"      
    
    HEADLESS = True

class ByteDanceScraper(BaseScraper):
    """ByteDance specific scraper."""
    
    def __init__(self, headless: bool = Config.HEADLESS):
        super().__init__("bytedance", headless)
        
    def fetch_page_html(self, page_num: int, filters: Optional[Dict] = None) -> Optional[str]:
        """Fetches page HTML with optional filters."""
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                params = [f"current={page_num}"]
                if filters:
                    for k, v in filters.items():
                        if v: params.append(f"{k}={v}")
                
                full_url = f"{Config.CAMPUS_URL}?{'&'.join(params)}"
                self.logger.info(f"Accessing: {full_url} (Attempt {attempt}/{Config.MAX_RETRIES})")
                
                self.driver.get(full_url)
                
                try:
                    WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-id]"))
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
        job_cards = soup.find_all('a', attrs={'data-id': True})
        results = []
        
        for card in job_cards:
            try:
                job_data = self._parse_single_card(card)
                if job_data['system_id'] in self.crawled_ids: continue
                self.crawled_ids.add(job_data['system_id'])
                results.append(job_data)
            except Exception as e:
                self.logger.error(f"✗ Failed to parse card: {e}")
        return results

    def _parse_single_card(self, card) -> Dict:
        """Parses a single job card."""
        system_id = card.get('data-id', 'N/A')
        href = card.get('href', '')
        detail_url = f"{Config.BASE_URL}{href}" if href else 'N/A'
        
        title_elem = card.find('span', class_='positionItem-title-text')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        metadata = []
        subtitle_div = card.find('div', class_='positionItem-subTitle')
        if subtitle_div:
            spans = subtitle_div.find_all('span', recursive=False)
            for span in spans:
                text = span.get_text(strip=True)
                if text and not span.get('class', [''])[0].endswith('Devider'):
                    metadata.append(text)
        
        business_id = 'N/A'
        for item in metadata:
            if '职位ID' in item.replace(' ', ''):
                business_id = item.split('：')[-1].strip()
                break
        
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

    def fetch_job_detail(self, url: str) -> Optional[Dict]:
        """Fetches and parses job details."""
        try:
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, Config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "block-title"))
                )
            except TimeoutException:
                pass
            time.sleep(1)
            
            detail_info = {'job_description': 'N/A', 'job_requirements': 'N/A', 'team_intro': 'N/A'}
            blocks = self.driver.find_elements(By.CLASS_NAME, "block-title")
            for block in blocks:
                try:
                    title = block.text.strip()
                    content = block.find_element(By.XPATH, "following-sibling::div[@class='block-content']").text.strip()
                    if '职位描述' in title: detail_info['job_description'] = content
                    elif '职位要求' in title: detail_info['job_requirements'] = content
                    elif '团队介绍' in title: detail_info['team_intro'] = content
                except: continue
            return detail_info
        except Exception as e:
            self.logger.error(f"Failed to fetch detail: {e}")
            return None

    def crawl(self):
        """Main crawl logic."""
        all_jobs = []
        try:
            self.init_driver()
            filters = {
                'location': Config.FILTER_LOCATION,
                'category': Config.FILTER_CATEGORY,
                'project': Config.FILTER_PROJECT
            }
            
            for page in range(Config.START_PAGE, Config.END_PAGE + 1):
                self.logger.info(f"--- Page {page} ---")
                html = self.fetch_page_html(page, filters)
                if not html: break
                
                jobs = self.parse_job_list(html)
                if not jobs: break
                
                if Config.CRAWL_DETAIL:
                    for job in jobs:
                        self.logger.info(f"Fetching detail for: {job['title']}")
                        detail = self.fetch_job_detail(job['url'])
                        if detail: job.update(detail)
                        self.random_delay(1, 3)
                
                all_jobs.extend(jobs)
                if len(jobs) < 10: break
                self.random_delay(Config.REQUEST_DELAY[0], Config.REQUEST_DELAY[1])
        finally:
            self.close()
        
        self.save_results(all_jobs)
        return all_jobs

def main():
    scraper = ByteDanceScraper()
    scraper.crawl()

if __name__ == "__main__":
    main()
