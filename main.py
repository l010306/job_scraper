"""
Unified Entry Point for Job Scrapers
Allows running specific scrapers or all of them.
"""

import argparse
import sys
from bytedance_scraper import ByteDanceScraper
from meituan_scraper import MeituanScraper
from tencent_scraper import TencentScraper

def run_scraper(name: str):
    """Runs a specific scraper based on its name."""
    scrapers = {
        "bytedance": ByteDanceScraper,
        "meituan": MeituanScraper,
        "tencent": TencentScraper
    }
    
    if name not in scrapers:
        print(f"Error: Scraper '{name}' not found. Available: {', '.join(scrapers.keys())}")
        return
    
    print(f"\n{'='*60}")
    print(f"Starting {name.capitalize()} Scraper...")
    print(f"{'='*60}")
    
    scraper = scrapers[name]()
    try:
        scraper.crawl()
    except Exception as e:
        print(f"Error running {name} scraper: {e}")

def main():
    parser = argparse.ArgumentParser(description="Unified Job Scrapper Suite")
    parser.add_argument(
        "scraper", 
        nargs="?", 
        choices=["bytedance", "meituan", "tencent", "all"],
        default="all",
        help="Specify which scraper to run (default: all)"
    )
    
    args = parser.parse_args()
    
    if args.scraper == "all":
        for s in ["bytedance", "meituan", "tencent"]:
            run_scraper(s)
    else:
        run_scraper(args.scraper)

if __name__ == "__main__":
    main()
