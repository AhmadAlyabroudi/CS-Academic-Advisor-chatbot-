"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-05-22

"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cs_faculty_info (no foreign keys — create first) ──────────────────────
    op.create_table(
        "cs_faculty_info",
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("office_location", sa.String(), nullable=True),
        sa.Column("office_hours", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("email"),
    )

    # ── courses ───────────────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("id_reg", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("prerequisites", sa.String(), nullable=True),
        sa.Column("plan_type", sa.String(), nullable=True),
        sa.Column("credit_hours", sa.Integer(), nullable=True),
        sa.Column("suggested_year", sa.Integer(), nullable=True),
        sa.Column("suggested_semester", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("code"),
    )

    # ── students (FK → cs_faculty_info) ──────────────────────────────────────
    op.create_table(
        "students",
        sa.Column("university_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("major", sa.String(), nullable=True),
        sa.Column("current_gpa", sa.Float(), nullable=True),
        sa.Column("academic_standing", sa.String(), nullable=True),
        sa.Column("completed_credits", sa.Integer(), nullable=True),
        sa.Column("remaining_courses", sa.Integer(), nullable=True),
        sa.Column("advisor_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["advisor_id"], ["cs_faculty_info.email"]),
        sa.PrimaryKeyConstraint("university_id"),
    )
    op.create_index("ix_students_email", "students", ["email"], unique=True)

    # ── student_roadmap ───────────────────────────────────────────────────────
    op.create_table(
        "student_roadmap",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("course_code", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("grade", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("semester", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["course_code"], ["courses.code"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.university_id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── student_verification ──────────────────────────────────────────────────
    op.create_table(
        "student_verification",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("university_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_sv_email"),
        sa.UniqueConstraint("university_id", name="uq_sv_uid"),
    )
    op.create_index("ix_student_verification_email", "student_verification", ["email"], unique=True)
    op.create_index("ix_student_verification_university_id", "student_verification", ["university_id"], unique=True)

    # ── official_rooms ────────────────────────────────────────────────────────
    op.create_table(
        "official_rooms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_code", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["course_code"], ["courses.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_official_rooms_id", "official_rooms", ["id"], unique=False)

    # ── private_study_rooms ───────────────────────────────────────────────────
    op.create_table(
        "private_study_rooms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("creator_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["students.university_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_private_study_rooms_id", "private_study_rooms", ["id"], unique=False)

    # ── room_members ──────────────────────────────────────────────────────────
    op.create_table(
        "room_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("room_type", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.university_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_room_members_id", "room_members", ["id"], unique=False)

    # ── chatbot_history ───────────────────────────────────────────────────────
    op.create_table(
        "chatbot_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("message_content", sa.Text(), nullable=False),
        sa.Column("sender_type", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.university_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chatbot_history_id", "chatbot_history", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("chatbot_history")
    op.drop_table("room_members")
    op.drop_table("private_study_rooms")
    op.drop_table("official_rooms")
    op.drop_table("student_verification")
    op.drop_table("student_roadmap")
    op.drop_table("students")
    op.drop_table("courses")
    op.drop_table("cs_faculty_info")
