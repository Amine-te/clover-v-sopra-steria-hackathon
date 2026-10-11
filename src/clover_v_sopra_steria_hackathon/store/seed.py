"""Console entry `clover-seed`: write 30 days of fictional demo observations to GAMEDAY_BUCKET.

Import has no side effects; the work runs only when `main()` is called (the script entry point).
"""

from __future__ import annotations

from ..config import get_settings
from .generator import generate, seed_store
from .service import TimelineStore


def main() -> None:
    """Generate fictional demo data and seed it into the configured bucket."""
    settings = get_settings()
    store = TimelineStore(settings)
    data = generate()
    keys = seed_store(store, data)
    print(f"Seeded {len(keys)} fictional observation(s) into bucket '{settings.gameday_bucket}'.")
    print(f"Subject: {data.observations[0].subject_id if data.observations else '(none)'}")


if __name__ == "__main__":
    main()
