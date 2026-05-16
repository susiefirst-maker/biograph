"""Rebuild the Meilisearch `entities` index from Postgres.

Usage:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python scripts/build_search_index.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.search import reindex_all_sync, reset_index


def main() -> None:
    reset_index()
    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        counts = reindex_all_sync(session)

    print("=== Meilisearch entities index rebuilt ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
