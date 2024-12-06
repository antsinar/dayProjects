import sys
from argparse import ArgumentParser
from pathlib import Path

import scraper

try:
    sys.path.append(str(Path(__file__).parent.parent))
    from project_crawler import crawler
except ModuleNotFoundError as e:
    print(e)
    exit(1)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("url", type=str, help="Provide a url to crawl")
    parser.add_argument(
        "-f", "--force", type=bool, default=False, help="Force new crawling action"
    )
    parser.add_argument(
        "-c",
        "--compressor",
        type=crawler.Compressor,
        choices=[choice.value for choice in crawler.Compressor],
        default=crawler.Compressor.LZMA.value,
    )
    parser.add_argument(
        "-p",
        "--processes",
        type=int,
        required=False,
        default=8,
        help="Number of processes used for content scraping",
    )
    args = parser.parse_args()
    scraper.main(args)
