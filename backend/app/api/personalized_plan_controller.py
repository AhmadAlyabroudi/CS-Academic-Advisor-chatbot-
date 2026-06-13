"""
Personalized Road Map Generator
================================
Auto-generates an optimal semester-by-semester graduation plan based on:
  - Student's completed / currently-enrolled courses
  - Prerequisite chains (DAG)
  - JUST regulations: 18 hrs Fall/Spring, 9 hrs Summer, 132 total
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

from app.core.database import get_db
from app.models.student_roadmap import StudentRoadmap
from app.models.course import Course
from app.models.student import Student

router = APIRouter(prefix="/personalized-plan", tags=["Personalized Plan"])

# ── Constants (JUST Regulations) ────────────────────────────────────────────
MAX_CREDITS_REGULAR = 18   # Fall / Spring
MAX_CREDITS_SUMMER  = 9    # Summer
TOTAL_GRADUATION    = 132
CREDIT_GATE_90      = 90   # CS391, CS491 require >= 90 completed hours

# Semester ordering within an academic year
SEMESTER_ORDER = ["Fall", "Spring", "Summer"]


# ── Helpers ─────────────────────────────────────────────────────────────────
def _normalize(code: str) -> str:
    """Normalize a course code for comparison: strip, collapse spaces, upper."""
    return code.strip().replace(" ", "").upper()


def _parse_prerequisites(prereq_str: str) -> Tuple[List[str], bool]:
    """
    Parse a prerequisite string.
    Returns (list_of_course_codes, requires_90_credits).
    """
    if not prereq_str or prereq_str.strip().lower() in ("none", "none "):
        return [], False

    requires_90 = False
    codes: List[str] = []

    if "PASS 90 Credit" in prereq_str:
        requires_90 = True
        # Some entries are *only* "PASS 90 Credit", others combine with courses
        remaining = prereq_str.replace("PASS 90 Credit", "").strip("& ").strip()
        if remaining:
            codes = [_normalize(c) for c in remaining.split("&") if c.strip()]
    else:
        codes = [_normalize(c) for c in prereq_str.split("&") if c.strip()]

    return codes, requires_90


def _build_dag(courses: List[Course]) -> Dict[str, List[str]]:
    """
    Build adjacency list:  prereq → [courses that depend on it]
    """
    graph: Dict[str, List[str]] = defaultdict(list)
    for c in courses:
        prereq_codes, _ = _parse_prerequisites(c.prerequisites)
        for p in prereq_codes:
            graph[p].append(_normalize(c.code))
    return graph


def _compute_critical_path(
    courses_map: Dict[str, Course],
    dag: Dict[str, List[str]],
) -> Dict[str, int]:
    """
    For each course compute the length of the longest dependency chain that
    *starts from it*.  Courses with longer chains should be scheduled first
    because delaying them delays the entire graduation.
    """
    memo: Dict[str, int] = {}

    def dfs(code: str) -> int:
        if code in memo:
            return memo[code]
        children = dag.get(code, [])
        if not children:
            memo[code] = 0
            return 0
        best = max(dfs(ch) for ch in children)
        memo[code] = best + 1
        return memo[code]

    for code in courses_map:
        dfs(_normalize(code))

    return memo


def _priority_key(
    code: str,
    courses_map: Dict[str, Course],
    critical: Dict[str, int],
) -> Tuple:
    """
    Sorting key — lower = higher priority.
    1. Longer critical path first  (negate for descending)
    2. Earlier suggested year
    3. Earlier semester  (Fall < Spring < Summer)
    4. Compulsory before elective
    """
    c = courses_map.get(code)
    cp = critical.get(_normalize(code), 0)
    sem_idx = SEMESTER_ORDER.index(c.suggested_semester) if c and c.suggested_semester in SEMESTER_ORDER else 1
    is_elective = 1 if c and c.plan_type and "Elective" in c.plan_type else 0
    year = c.suggested_year if c else 4
    return (-cp, year, sem_idx, is_elective, code)


# ── Main endpoint ───────────────────────────────────────────────────────────
@router.get("/{student_id}/generate")
def generate_personalized_plan(student_id: str, db: Session = Depends(get_db)):
    """
    Generate an optimal semester-by-semester graduation plan for the student.
    """
    # ── 1. Validate student ──────────────────────────────────────────────────
    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # ── 2. Gather data ───────────────────────────────────────────────────────
    all_courses = db.query(Course).all()
    courses_map: Dict[str, Course] = {_normalize(c.code): c for c in all_courses}

    roadmap_items = db.query(StudentRoadmap).filter(
        StudentRoadmap.student_id == student_id
    ).all()

    # Sets of normalized codes
    completed_set: Set[str] = set()
    enrolled_set: Set[str] = set()
    completed_credits = 0

    for item in roadmap_items:
        nc = _normalize(item.course_code)
        status = (item.status or "").lower()
        if status == "completed":
            completed_set.add(nc)
            c_info = courses_map.get(nc)
            if c_info:
                completed_credits += int(c_info.credit_hours or 0)
        elif status == "currently enrolled":
            enrolled_set.add(nc)

    # Credits for currently enrolled (will be completed after current semester)
    enrolled_credits = 0
    for nc in enrolled_set:
        c_info = courses_map.get(nc)
        if c_info:
            enrolled_credits += int(c_info.credit_hours or 0)

    # ── 3. Determine remaining courses ───────────────────────────────────────
    # All courses in the catalog that the student hasn't completed and isn't
    # currently enrolled in.
    remaining_codes: List[str] = []
    for nc, c in courses_map.items():
        if nc not in completed_set and nc not in enrolled_set:
            remaining_codes.append(nc)

    if not remaining_codes:
        return {
            "student_id": student_id,
            "completed_credits": completed_credits,
            "enrolled_credits": enrolled_credits,
            "remaining_credits": 0,
            "plan": [],
            "total_semesters": 0,
            "message": "Congratulations! You have completed all courses."
        }

    # ── 4. Build DAG & critical paths ────────────────────────────────────────
    dag = _build_dag(all_courses)
    critical = _compute_critical_path(courses_map, dag)

    # ── 5. Determine starting semester ───────────────────────────────────────
    # We assume "currently enrolled" courses finish at the end of the current
    # semester.  The plan starts from the *next* semester.
    # We'll use today's date to guess the current semester, but a simple
    # heuristic is fine — the student can see the labels.
    import datetime
    now = datetime.datetime.now()
    month = now.month

    if month >= 9 or month <= 1:
        current_sem = "Fall"
    elif month >= 2 and month <= 5:
        current_sem = "Spring"
    else:
        current_sem = "Summer"

    # Academic year: if Fall → year = calendar year, else year = calendar year - 1
    if current_sem == "Fall":
        academic_year_start = now.year
    elif current_sem == "Spring":
        academic_year_start = now.year - 1
    else:
        academic_year_start = now.year - 1

    # Next semester after current
    current_idx = SEMESTER_ORDER.index(current_sem)
    next_idx = current_idx + 1
    if next_idx >= len(SEMESTER_ORDER):
        next_idx = 0
        academic_year_start += 1

    # ── 6. Greedy semester-by-semester scheduling ────────────────────────────
    plan_semesters: List[dict] = []
    scheduled_set: Set[str] = set(completed_set)
    # Assume enrolled courses will be done after current semester
    post_current_credits = completed_credits + enrolled_credits
    post_current_completed = completed_set | enrolled_set
    scheduled_set = set(post_current_completed)

    sem_pointer = next_idx
    year_pointer = academic_year_start

    remaining_to_schedule = set(remaining_codes)
    max_iterations = 20  # Safety: max 20 semesters

    for _ in range(max_iterations):
        if not remaining_to_schedule:
            break

        sem_name = SEMESTER_ORDER[sem_pointer]
        max_credits = MAX_CREDITS_SUMMER if sem_name == "Summer" else MAX_CREDITS_REGULAR

        # Determine which courses can be taken this semester
        eligible: List[str] = []
        for code in remaining_to_schedule:
            c = courses_map.get(code)
            if not c:
                continue

            prereq_codes, needs_90 = _parse_prerequisites(c.prerequisites)

            # Check prerequisite courses
            prereqs_met = all(p in scheduled_set for p in prereq_codes)
            if not prereqs_met:
                continue

            # Check 90-credit gate
            if needs_90 and post_current_credits < CREDIT_GATE_90:
                continue

            eligible.append(code)

        if not eligible:
            # No eligible courses this semester — but there are still remaining
            # courses. This can happen if we need more credits to unlock 90-gate.
            # Advance to next semester.
            # But if we're stuck forever, break.
            sem_pointer += 1
            if sem_pointer >= len(SEMESTER_ORDER):
                sem_pointer = 0
                year_pointer += 1
            continue

        # Sort by priority
        eligible.sort(key=lambda c: _priority_key(c, courses_map, critical))

        # Fill semester up to max credits
        semester_courses: List[dict] = []
        semester_credits = 0

        for code in eligible:
            c = courses_map.get(code)
            if not c:
                continue
            ch = int(c.credit_hours or 0)

            # Special: 0-credit courses (like BT401L) don't consume credit slots
            if ch > 0 and semester_credits + ch > max_credits:
                continue

            semester_courses.append({
                "course_code": c.code,
                "course_name": c.name,
                "credit_hours": ch,
                "prerequisites": c.prerequisites or "None",
                "plan_type": c.plan_type or "",
            })
            semester_credits += ch
            scheduled_set.add(code)
            remaining_to_schedule.discard(code)

        if semester_courses:
            # Build label
            if sem_name == "Fall":
                label = f"Fall {year_pointer}/{year_pointer + 1}"
            elif sem_name == "Spring":
                label = f"Spring {year_pointer}/{year_pointer + 1}"
            else:
                label = f"Summer {year_pointer + 1}"

            plan_semesters.append({
                "semester_label": label,
                "semester_type": sem_name,
                "courses": semester_courses,
                "total_hours": semester_credits,
            })

            # Update cumulative credits for 90-gate checks
            post_current_credits += semester_credits

        # Advance to next semester
        sem_pointer += 1
        if sem_pointer >= len(SEMESTER_ORDER):
            sem_pointer = 0
            year_pointer += 1

    # ── 7. Build response ────────────────────────────────────────────────────
    total_remaining = sum(
        int(courses_map[c].credit_hours or 0)
        for c in remaining_codes
        if c in courses_map
    )

    return {
        "student_id": student_id,
        "completed_credits": completed_credits,
        "enrolled_credits": enrolled_credits,
        "remaining_credits": total_remaining,
        "total_semesters": len(plan_semesters),
        "plan": plan_semesters,
    }
