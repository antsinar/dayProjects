import asyncio
import csv
import multiprocessing
import sys
from argparse import Namespace
from importlib import import_module
from types import ModuleType
from typing import Dict, Generator, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse

import httpx
import networkx as nx
from lxml import html

try:
    sys.path.append(str(Path(__file__).parent.parent))
    from project_crawler import crawler
except ModuleNotFoundError as e:
    print(e)
    exit(1)


async def fetch_webpage(
    url: str, client: httpx.AsyncClient
) -> Tuple[str, Optional[str]]:
    """Return url and contents of webpage, if available"""
    if "#" in url:
        return (url, None)
    head_response = await client.head(url)
    if head_response.status_code != 200:
        return (url, None)
    if "text/html" not in head_response.headers["content-type"]:
        return (url, None)
    response = await client.get(url)
    return (url, str(response.content, encoding="utf-8"))


async def fetch_manager(graph: nx.Graph) -> List[str]:
    """Return the contents of all scraped webpages as a List"""
    semaphore = asyncio.Semaphore(20)

    async def semaphore_fetch(node):
        async with semaphore:
            return await fetch_webpage(node, client)

    async with httpx.AsyncClient(
        headers={"User-Agent": "MapMakingCrawler/0.1"},
        timeout=30,
        follow_redirects=True,
    ) as client:
        async with asyncio.TaskGroup() as tg:
            # TODO: Handle Connection Error Exceptions
            tasks = [tg.create_task(semaphore_fetch(node)) for node in graph.nodes]

        return [task.result() for task in tasks]


def parse_webpage(
    contents: Tuple[str, Optional[str]], container_elements: List[str] = []
) -> Dict[str, int]:
    """Returns a dictionary of number of element appears in the document
    Empty elements list means every opening tag is a container
    """
    url, page_contents = contents
    if not page_contents:
        return {url: 1}
    return {url: len(html.fromstring(page_contents).xpath("//*"))}


def main(args: Namespace) -> None:
    footprints_file = (
        f"{str(Path(__file__).parent)}/{urlparse(args.url).netloc}.footprints.csv"
    )
    if (
        Path(footprints_file + crawler.compressor_extensions[args.compressor]).exists()
        and not args.force
    ):
        print("[Info]: Reading compressed footprints file")
        exit(0)
    G: nx.Graph = asyncio.run(crawler.main(args.url, args.compressor, args.force))
    results: List[str] = asyncio.run(fetch_manager(G))
    with multiprocessing.Pool(args.processes) as p:
        page_footprints = p.map(
            parse_webpage, results, chunksize=(len(results) // args.processes)
        )
    print("[Info]: Backing up footprint data")
    with open(footprints_file, "w") as f:
        writer = csv.writer(f)
        writer.writerows(
            sorted(
                [
                    (key, val)
                    for ft in page_footprints
                    for key, val in ft.items()
                    if "#" not in key
                ],
                key=lambda row: row[1],
                reverse=True,
            )
        )
    print(f"[Info]: Compressing footprint file {args.compressor}")
    compressor_module = import_module(args.compressor)
    with open(footprints_file, "rb") as f_in:
        with compressor_module.open(
            footprints_file + crawler.compressor_extensions[args.compressor], "wb"
        ) as f_out:
            f_out.writelines(f_in)
    Path(footprints_file).unlink(missing_ok=True)
