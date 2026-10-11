"""M1 — database engine/session configuration is valid (no connection needed)."""

from sqlalchemy.orm import Session

from clover_v_sopra_steria_hackathon.db.base import Base
from clover_v_sopra_steria_hackathon.db.session import SessionLocal, engine, get_db


def test_engine_url_uses_psycopg_driver():
    assert engine.url.drivername == "postgresql+psycopg"


def test_session_factory_is_bound():
    session: Session = SessionLocal()
    try:
        assert session.bind is engine
    finally:
        session.close()


def test_get_db_yields_and_closes_session():
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    gen.close()


def test_declarative_base_has_metadata():
    assert Base.metadata is not None
