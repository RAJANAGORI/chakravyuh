# main.py
from utils.config_loader import load_config
from connectors.aws_scraper import AWSSiteScraper
# from connectors.confluence_connector import ConfluenceConnector

if __name__ == "__main__":
    cfg = load_config("config.yaml")

    # Confluence still as before (optional)
    # conf_cfg = cfg.get("confluence")
    # if conf_cfg:
    #     confluence = ConfluenceConnector(
    #         base_url=conf_cfg["base_url"],
    #         email=conf_cfg["email"],
    #         api_token=conf_cfg["api_token"]
    #     )
    #     confluence.export_to_json(page_ids=conf_cfg.get("page_ids", []))

    # AWS Scraper
    aws_cfg = cfg.get("aws_docs")
    if aws_cfg:
        base_dir = aws_cfg.get("base_dir", "./aws_docs")
        services = aws_cfg.get("services", [])
        max_workers = aws_cfg.get("max_workers")
        scraper = AWSSiteScraper(base_dir=base_dir, start_urls=services, max_workers=max_workers)
        scraper.run()