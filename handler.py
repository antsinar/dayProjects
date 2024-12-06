import sqlite3
from argparse import ArgumentParser
from enum import StrEnum
from pathlib import Path
from handler_scripts import _exceptions
from handler_scripts._terminal_colors import TerminalColors


class ScriptOptions(StrEnum):
    STARTPROJECT = "start-project"
    INSTALL = "install-project"
    DELETEPROJECT = "delete-project"
    SYNCPROJECTS = "sync-projects"


def print_error(message: str) -> None:
    print(f"{TerminalColors.FAILURE}[Err] {message}{TerminalColors.END}")


def init_database() -> None:
    """Initialize a new database if it does not already exist"""
    conn = sqlite3.connect(Path(__file__).parent / "projects.db")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS project(name TEXT NOT NULL, created_ts INTEGER NOT NULL, active INTEGER NOT NULL);
        """
    )
    conn.commit()
    conn.close()


def main() -> None:
    """Call management command
    IMPORTANT: Must be called from the root directory (here)
    Options:
    - start-project <proj_name>: Start a new project from existing template
    - install-project <proj_name>: Install project dependencies and checks if already installed
    - delete-project <proj_name>: Removes a project from the list of completed projects on root
    - sync-projects: Add all complete and non-complete projects to the list on root
    Options are separate scripts, under the handler_scripts directory and are called via an enum by the user
    """
    parser = ArgumentParser()
    parser.add_argument(
        "command",
        type=str,
        choices=[option.value for option in ScriptOptions],
        help="Which script the handler should execute? View options",
    )
    parser.add_argument("-pn", "--project-name", type=str, required=False)
    args = parser.parse_args()
    init_database()
    for path in Path("handler_scripts/").iterdir():
        if not path.is_file():
            continue
        if args.command.replace("-", "") == path.stem:
            import importlib

            command = importlib.import_module(f"handler_scripts.{path.stem}")
            try:
                command.main(project_name=args.project_name)
            except NotImplementedError:
                print_error("Command not yet implemented")
                exit(1)
            except TypeError as e:
                print_error(e)
            except _exceptions.NoProjectNameError as e:
                print_error(e)
                exit(1)


if __name__ == "__main__":
    main()
