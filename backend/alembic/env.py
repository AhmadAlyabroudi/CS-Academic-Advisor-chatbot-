import os
import sys
from logging.config import fileConfig
from os.path import abspath, dirname

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, dirname(dirname(abspath(__file__))))
load_dotenv()

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override the URL from the environment variable.
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL must be set (PostgreSQL connection string)")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import ALL models so autogenerate can detect every table ──────────────────
from app.core.database import Base  # noqa: E402
from app.models.student import Student  # noqa: E402, F401
from app.models.cs_faculty_info import CsFacultyInfo  # noqa: E402, F401
from app.models.course import Course  # noqa: E402, F401
from app.models.student_roadmap import StudentRoadmap  # noqa: E402, F401
from app.models.student_verification import StudentVerification  # noqa: E402, F401
from app.models.enrollment import Enrollment  # noqa: E402, F401
from app.models.study_rooms import OfficialRooms, PrivateStudyRooms, RoomMembers  # noqa: E402, F401
from app.models.chatbot_history import ChatbotHistory  # noqa: E402, F401

target_metadata = Base.metadata


# ── Migration runners ─────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
