import asyncio
from argparse import ArgumentParser
import crawler
import networkx as nx
import time


def main() -> None:
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
    args = parser.parse_args()

    G: nx.Graph = asyncio.run(crawler.main(args.url, args.compressor, args.force))
    print("Nodes:", G.number_of_nodes())
    print("Edges: ", G.number_of_edges())


if __name__ == "__main__":
    t_start = time.perf_counter()
    main()
    t_finish = time.perf_counter()
    print("Took:", t_finish - t_start, "seconds.")
