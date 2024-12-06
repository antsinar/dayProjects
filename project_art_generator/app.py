from argparse import ArgumentParser
import asyncio.futures
from operator import itemgetter
from random import randint
from typing import AsyncGenerator, List, Tuple
import asyncio
import websockets
import orjson
from functools import partial


def init_grid(rows: int, columns: int) -> List[List[int]]:
    return [[0 for _ in range(columns)] for _ in range(rows)]


def generate_positions(
    rows: int, columns: int, num_positions: int
) -> List[Tuple[int, int]]:
    positions = sorted(
        [(randint(0, rows - 1), randint(0, columns - 1)) for _ in range(num_positions)],
        key=itemgetter(0, 1),
    )
    return positions


async def modify_grid(
    grid: List[List[int]], positions: List[Tuple[int, int]]
) -> AsyncGenerator[Tuple[int, List[int]], None]:
    """Yield only the row that is affected by the changes"""
    row_indexes = (p[0] for p in positions)
    for i in range(len(grid)):
        if i not in row_indexes:
            continue
        column_indexes = (p[1] for p in positions if p[0] == i)
        yield i, grid[i]
        for col in set(column_indexes):
            grid[i][col] = 1
            yield i, grid[i]


async def websocket_handler(websocket, rows: int, columns: int, timeout: float):
    modifier = modify_grid(
        init_grid(rows, columns),
        generate_positions(rows, columns, (rows * columns) // 3),
    )
    while True:
        try:
            instance_id, instance = await anext(modifier)
            await websocket.send(
                orjson.dumps(
                    {
                        "instance_id": instance_id,
                        "instance": instance,
                    },
                ).decode("utf-8")
            )
            await asyncio.sleep(timeout)
        except StopAsyncIteration:
            break


async def main():
    parser = ArgumentParser()
    parser.add_argument("width", type=int, default=1280, nargs="?")
    parser.add_argument("height", type=int, default=720, nargs="?")
    parser.add_argument("-c", "--cell-size", type=int, default=10)
    parser.add_argument("-t", "--timeout", type=int, default=10, help="Timeout in ms")
    args = parser.parse_args()

    columns = args.width // args.cell_size
    rows = args.height // args.cell_size

    async with websockets.serve(
        partial(
            websocket_handler, rows=rows, columns=columns, timeout=args.timeout / 1000
        ),
        "",
        8001,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit(0)
