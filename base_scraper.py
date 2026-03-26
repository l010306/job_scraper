"""
Base Scraper - Centered logic for all job scrapers
Handles Selenium initialization, logging, and data persistence.
"""

import json
import csv
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class BaseScraper:
    """Base class for all job scrapers."""
    
    def __init__(self, company_name: str, headless: bool = True):
        self.company_name = company_name
        self.headless = headless
        self.driver = None
        self.crawled_ids = set()
        
        # Setup paths
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / "output" / company_name
        self.log_dir = self.base_dir / "logs" / company_name
        
        # Setup directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configures logging for the scraper."""
        log_file = self.log_dir / f"crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logger = logging.getLogger(self.company_name)
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(formatter)
            
            sh = logging.StreamHandler()
            sh.setFormatter(formatter)
            
            logger.addHandler(fh)
            logger.addHandler(sh)
            
        return logger

    def init_driver(self):
        """Initializes the Chrome WebDriver."""
        try:
            self.logger.info(f"Initializing Chrome driver for {self.company_name}...")
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
                self.logger.info("Running in headless mode.")
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(5)
            
            self.logger.info("✓ Chrome driver initialized successfully.")
        except Exception as e:
            self.logger.error(f"✗ Failed to initialize Chrome driver: {e}")
            raise

    def save_results(self, jobs: List[Dict]):
        """Saves scraped data to JSON and CSV formats."""
        if not jobs:
            self.logger.warning("No data to save.")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        json_path = self.output_dir / f"{self.company_name}_jobs_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        self.logger.info(f"✓ JSON saved: {json_path}")
        
        # Save CSV
        csv_path = self.output_dir / f"{self.company_name}_jobs_{timestamp}.csv"
        keys = jobs[0].keys()
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(jobs)
        self.logger.info(f"✓ CSV saved: {csv_path}")
        
        self.logger.info(f"Total jobs collected: {len(jobs)}")

    def close(self):
        """Closes the browser."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("✓ Browser closed.")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")

    def random_delay(self, min_sec: float, max_sec: float):
        """Utility to wait for a random amount of time."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
