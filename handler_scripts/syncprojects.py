import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Tuple

from handler_scripts._terminal_colors import TerminalColors


@contextmanager
def conn_manager(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    try:
        yield conn
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"{TerminalColors.FAILURE}[Err] {e}{TerminalColors.END}")
        conn.rollback()
    finally:
        conn.close()


def get_projects_db(conn: sqlite3.Connection) -> List[Tuple[str, int]]:
    """Return project names and active status for each database entry."""
    db_project_names = conn.execute("""SELECT DISTINCT name, active FROM project;""")
    return db_project_names.fetchall()


def cleanup_projects_db(conn: sqlite3.Connection) -> None:
    """Delete all duplicate projects, if any."""
    name_counts = conn.execute(
        """SELECT name, COUNT(name) FROM project GROUP BY name;"""
    )
    for row in name_counts.fetchall():
        if row[1] == 1:
            continue
        conn.execute(
            """DELETE FROM project WHERE name=?;""",
            (row[0],),
        )


def crawl_root_dir(root_dir: Path) -> Generator[str, None, None]:
    """Yield one project directory name at a time."""
    for item in root_dir.iterdir():
        if item.is_file():
            continue
        if item.name.startswith("."):
            continue
        if item.name == "handler_scripts":
            continue
        yield item.name


def save_project_details(project_name: str, conn: sqlite3.Connection) -> None:
    conn.execute(
        """INSERT INTO project VALUES (?, ?, ?)""",
        (project_name, int(datetime.now().timestamp()), True),
    )


def update_non_present_active_status(
    remaining_names: List[str], conn: sqlite3.Connection
) -> None:
    statuses = [
        conn.execute("""SELECT name, active FROM project WHERE name=?;""", (name,))
        for name in remaining_names
    ]
    for status in statuses:
        item = status.fetchone()
        if item[1] == 1:
            conn.execute("""UPDATE project SET active=0 WHERE name=?;""", (item[0],))


def main(**kwargs) -> None:
    root_dir = Path(__file__).parent.parent
    conn = sqlite3.connect(root_dir / "projects.db")
    conn.autocommit = False
    with conn_manager(conn) as conn_obj:
        cleanup_projects_db(conn_obj)
        projects_db = get_projects_db(conn_obj)
        project_names_db = [item[0] for item in projects_db]
        project_active_status = [item[1] for item in projects_db]
        for project_name in crawl_root_dir(root_dir):
            if project_name not in project_names_db:
                save_project_details(project_name, conn)
            else:
                project_db_idx = project_names_db.index(project_name)
                project_names_db.remove(project_name)
                project_active_status.pop(project_db_idx)

        update_non_present_active_status(project_names_db, conn_obj)
