import os
import tempfile


def _default_sqlite_url() -> str:
    """Keep the local SQLite file OUTSIDE the project folder.

    If the project lives inside OneDrive / Dropbox, the sync client locks or re-touches the .db file while the
    backend is writing to it, which makes requests fail ("Cannot reach the server"). A folder in the user's home
    directory is never synced.
    """
    base = os.path.join(os.path.expanduser("~"), ".edunexus")
    try:
        os.makedirs(base, exist_ok=True)
    except OSError:
        base = tempfile.gettempdir()
    return "sqlite:///" + os.path.join(base, "edunexus.db").replace("\\", "/")


DATABASE_URL = os.getenv("DATABASE_URL") or _default_sqlite_url()
if DATABASE_URL.startswith("postgres://"):  # some hosts still give the old scheme
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
CORS_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
