from contextlib import contextmanager

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine(url: str = "sqlite:///data/itselectric.db"):
    return _create_engine(url, connect_args={"check_same_thread": False})


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
