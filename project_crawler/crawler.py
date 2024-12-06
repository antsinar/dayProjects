import asyncio
from contextlib import asynccontextmanager
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import AsyncGenerator, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import networkx as nx
from httpx import AsyncClient, RequestError
from lxml import html


class Compressor(StrEnum):
    GZIP = "gzip"
    LZMA = "lzma"


compressor_extensions = {Compressor.GZIP.value: ".gz", Compressor.LZMA.value: ".xz"}


class Crawler:
    def __init__(
        self, client: AsyncClient, delay: float = 0.01, limit: int = 1000
    ) -> None:
        self.delay = delay
        self.limit = limit
        self.client: AsyncClient = client
        self.roboparser: RobotFileParser = None

    async def parse_robotsfile(self) -> None:
        """Create a parser instance to check against while crawling"""
        roboparser = RobotFileParser()
        rbfile = await self.client.get("/robots.txt")
        roboparser.parse(rbfile.text.split("\n"))
        self.roboparser = roboparser

    async def check_robots_compliant(self, url: str) -> bool:
        return self.roboparser.can_fetch("*", url)

    async def build_graph(self, start_url: str, max_depth: int = 5):
        G = nx.Graph()
        visited = set()

        async def crawl(
            url: str,
            depth: int,
            client: AsyncClient,
            robot_parser: RobotFileParser,
            delay: float = 0.0,
        ):
            if depth > max_depth or url in visited:
                return

            if "#" in urlparse(url).path:
                return

            visited.add(url)
            G.add_node(url)

            try:
                response = await client.get(url)
                if response.status_code != 200:
                    print(
                        "[Info]: Page Inaccessible",
                        urlparse(url).path,
                        response.status_code,
                    )
                    return
                if "text/html" not in response.headers["Content-Type"]:
                    print(
                        "[Info]: Page not html",
                        urlparse(url).path,
                        response.headers["Content-Type"],
                    )
                    return
                if not robot_parser.can_fetch("*", url):
                    print(
                        "[Info]: Could not scrape due to robots.txt rules",
                        urlparse(url).path,
                    )
                    return

                tree = html.fromstring(response.text)

                for href in tree.xpath("//a/@href"):
                    full_url = urljoin(url, href)

                    if urlparse(full_url).netloc == urlparse(start_url).netloc:
                        G.add_edge(url, full_url)
                        await asyncio.sleep(delay)
                        await crawl(full_url, depth + 1, client, robot_parser)

            except RequestError:
                print(f"[Error]: ", urlparse(url).path)

        await crawl(start_url, 0, self.client, self.roboparser, self.delay)
        return G

    async def compress_graph(
        self,
        graph: nx.Graph,
        file_name: str,
        compressor_module: ModuleType,
        extension: str,
    ) -> None:
        file_name = str(Path(__file__).parent) + "/" + file_name + ".graphml"
        nx.write_graphml(graph, file_name, prettyprint=True)
        with open(file_name, "rb") as f_in:
            with compressor_module.open(file_name + extension, "wb") as f_out:
                f_out.writelines(f_in)
        Path(file_name).unlink()


@asynccontextmanager
async def generate_client(
    base_url: Optional[str] = "",
) -> AsyncGenerator[AsyncClient, None]:
    """Provide a client for the crawler"""
    headers = {"User-Agent": "MapMakingCrawler/0.1"}
    client = AsyncClient(base_url=base_url, headers=headers, follow_redirects=True)
    try:
        yield client
    except RequestError as e:
        print(e)
    finally:
        await client.aclose()


async def main(
    url: str, compressor: Compressor = Compressor.LZMA, force: bool = False
) -> nx.Graph:
    compressor_module = import_module(compressor.value)

    compressed_file = (
        f"{str(Path(__file__).parent)}/{urlparse(url).netloc}.graphml"
        + compressor_extensions[compressor]
    )
    if Path(compressed_file).exists() and force == False:
        print(f"[Info]: Reading compressed graph ({compressor}) for url")
        with compressor_module.open(compressed_file, "rb") as f:
            return nx.read_graphml(f)

    async with generate_client(url) as client:
        crawler = Crawler(client=client, delay=0.01)
        await crawler.parse_robotsfile()
        print("[Info]: Crawling Website")
        graph: nx.Graph = await crawler.build_graph(url)
        print("[Info]: Compressing Graph")
        await crawler.compress_graph(
            graph,
            urlparse(url).netloc,
            compressor_module,
            compressor_extensions[compressor],
        )
        return graph
