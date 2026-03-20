import os
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


def _build_engine():
    database_url = settings.database_url
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query)
    host = parsed.hostname or ""

    connect_args = {}
    has_ssl_options = any(
        key in query for key in ["ssl", "ssl_ca", "ssl_cert", "ssl_key", "ssl_verify_cert", "ssl_verify_identity"]
    )

    if "tidbcloud.com" in host and not has_ssl_options:
        ca_path = "/etc/ssl/certs/ca-certificates.crt"
        if os.path.exists(ca_path):
            connect_args["ssl"] = {"ca": ca_path}
        else:
            connect_args["ssl"] = {}

    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
