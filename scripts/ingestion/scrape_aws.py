"""Main entry point for AWS documentation scraping."""
import sys
from pathlib import Path

# Add project root to path for direct script execution
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chakravyuh.core.config import get_config
from chakravyuh.core.logging import logger
from chakravyuh.connectors.aws_scraper import AWSSiteScraper


def main():
    """Main scraping function."""
    try:
        cfg = get_config()

        # AWS Scraper
        if cfg.aws_docs.services:
            # Convert ServiceConfig objects to dicts for scraper
            services_list = [
                {"name": svc.name, "url": svc.url}
                for svc in cfg.aws_docs.services
            ]
            scraper = AWSSiteScraper(
                base_dir=cfg.aws_docs.base_dir,
                start_urls=services_list,
                max_workers=cfg.aws_docs.max_workers,
            )
            scraper.run()
        else:
            logger.warning("No AWS documentation services configured")

    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
