from contextlib import contextmanager

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine(url: str = "sqlite:///data/itselectric.db"):
    # check_same_thread is a SQLite-only pysqlite arg; Postgres drivers reject it.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return _create_engine(url, connect_args=connect_args)


@contextmanager
def get_session(engine):
    factory = sessionmaker(bind=engine)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
