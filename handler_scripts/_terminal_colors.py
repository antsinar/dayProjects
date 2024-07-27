from enum import StrEnum


class TerminalColors(StrEnum):
    SUCCESS = "\033[92m"
    FAILURE = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"
