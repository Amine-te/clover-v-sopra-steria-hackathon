"""Local demo utilities, disabled outside explicit demo/development environments."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...db.session import get_db
from ...models import JournalEntry
from ...services.demo_service import MARIE_ID, demo_period, reset_demo

router = APIRouter(prefix="/demo")


def require_demo() -> None:
    settings = get_settings()
    if settings.app_env not in {"development", "demo", "test"} or not settings.demo_reset_enabled:
        raise HTTPException(status_code=404, detail="Mode démonstration indisponible.")


class ResetRequest(BaseModel):
    confirmed: bool = False


@router.get("/status", dependencies=[Depends(require_demo)])
def demo_status(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    settings = get_settings()
    start, end = demo_period()
    return {
        "database": "ok", "reset_enabled": True,
        "period_start": start, "period_end": end,
        "seed_entry_count": db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.recipient_id == MARIE_ID,
            func.date(JournalEntry.occurred_at).between(start, end),
        )),
        "providers": {name: getattr(settings, f"{name}_provider") for name in (
            "llm", "stt", "ser", "wearable", "object_storage", "messaging",
        )},
    }


@router.post("/reset", dependencies=[Depends(require_demo)])
def reset(payload: ResetRequest, db: Session = Depends(get_db)):
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail="Confirmez la réinitialisation de la démo.")
    counts = reset_demo(db)
    db.commit()
    return {"status": "ok", "counts": counts}
