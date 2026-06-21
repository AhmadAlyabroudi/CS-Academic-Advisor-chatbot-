"""
Personalized Graduation Plan Generator (v2)
=============================================
Generates a semester-by-semester graduation plan that **follows the official
JUST CS study plan**.  Key rules:

  ✅ Courses are placed according to suggested_year + suggested_semester
  ✅ Co-requisite (concurrent) courses are always scheduled together
  ✅ Semester-locked courses can only appear in their designated semester
  ✅ Summer is *optional*: only for CS391 (alone) or delayed courses
  ✅ Graduation projects never in summer
  ✅ Max 18 hrs Fall/Spring, 9 hrs Summer, 132 total for graduation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Set, Tuple

from app.core.database import get_db
from app.models.student_roadmap import StudentRoadmap
from app.models.course import Course
from app.models.student import Student

router = APIRouter(prefix="/personalized-plan", tags=["Personalized Plan"])

# ── JUST Regulations ────────────────────────────────────────────────────────
MAX_CREDITS_REGULAR = 18          # Fall / Spring cap
MAX_CREDITS_SUMMER  = 9           # Summer cap
CREDIT_GATE_90      = 90          # CS391, CS491 require ≥ 90 completed hours

SEMESTER_ORDER = ["Fall", "Spring", "Summer"]

# ── Co-requisite pairs — must be registered in the same semester ────────────
CO_REQUISITES: Dict[str, str] = {
    "CS101":  "CS106",       # Intro to Programming  ↔  Lab
    "CS106":  "CS101",
    "SE112":  "SE113",       # Intro to OOP          ↔  Lab
    "SE113":  "SE112",
    "BT401":  "BT401L",     # Computational Biology  ↔  Lab
    "BT401L": "BT401",
}

# ── Semester-locked — can ONLY be offered in this specific semester type ────
SEMESTER_LOCKED: Dict[str, str] = {
    "BT401":  "Fall",        # Computational Biology — Fall only
    "BT401L": "Fall",        # Computational Biology Lab — Fall only
    "CS475":  "Spring",      # Distributed Computer Systems — Spring only
    "CS442":  "Spring",      # Wireless Networks — Spring only
    "CS385":  "Spring",      # Fundamentals of Multimedia — Spring only
}

# ── Special courses ─────────────────────────────────────────────────────────
TRAINING_COURSE = "CS391"                            # Practical Training
GRADUATION_PROJECTS: Set[str] = {"CS491", "CS492"}   # Never in summer


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(code: str) -> str:
    """Normalize a course code: strip spaces, uppercase."""
    return code.strip().replace(" ", "").upper()


def _parse_prerequisites(prereq_str: str) -> Tuple[List[str], bool]:
    """Return (list_of_prerequisite_codes, requires_90_credits)."""
    if not prereq_str or prereq_str.strip().lower() in ("none", "none "):
        return [], False

    requires_90 = False
    codes: List[str] = []

    if "PASS 90 Credit" in prereq_str:
        requires_90 = True
        remaining = prereq_str.replace("PASS 90 Credit", "").strip("& ").strip()
        if remaining:
            codes = [_normalize(c) for c in remaining.split("&") if c.strip()]
    else:
        codes = [_normalize(c) for c in prereq_str.split("&") if c.strip()]

    return codes, requires_90


def _prereqs_met(
    code: str,
    courses_map: Dict[str, Course],
    done: Set[str],
    same_semester: Set[str],
    cumulative_credits: int,
) -> bool:
    """
    Check whether *code*'s prerequisites are satisfied.

    Parameters
    ----------
    done           : courses completed or scheduled in *prior* semesters.
    same_semester  : courses being taken *concurrently* (for co-requisite bypass).
    cumulative_credits : total credits completed so far (for 90-hr gate).
    """
    c = courses_map.get(code)
    if not c:
        return False

    prereq_codes, needs_90 = _parse_prerequisites(c.prerequisites)

    # 90-credit gate
    if needs_90 and cumulative_credits < CREDIT_GATE_90:
        return False

    co_partner = CO_REQUISITES.get(code)
    co_nc = _normalize(co_partner) if co_partner else None

    for p in prereq_codes:
        # External prerequisite not in our catalog (e.g. LG099) → assume satisfied
        if p not in courses_map:
            continue
        # Co-requisite being taken concurrently → OK
        if co_nc and p == co_nc and p in same_semester:
            continue
        # Normal prerequisite: must be completed
        if p not in done:
            return False

    return True


# ═══════════════════════════════════════════════════════════════════════════
#  Main endpoint
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/{student_id}/generate")
def generate_personalized_plan(student_id: str, db: Session = Depends(get_db)):
    """Generate a semester-by-semester graduation plan following the official roadmap."""

    # ── 1. Validate student ─────────────────────────────────────────────────
    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # ── 2. Gather data ──────────────────────────────────────────────────────
    all_courses = db.query(Course).all()
    courses_map: Dict[str, Course] = {_normalize(c.code): c for c in all_courses}

    roadmap_items = db.query(StudentRoadmap).filter(
        StudentRoadmap.student_id == student_id
    ).all()

    completed_set: Set[str] = set()
    enrolled_set:  Set[str] = set()
    completed_credits = 0

    for item in roadmap_items:
        nc = _normalize(item.course_code)
        status = (item.status or "").lower()
        if status == "completed":
            completed_set.add(nc)
            if nc in courses_map:
                completed_credits += int(courses_map[nc].credit_hours or 0)
        elif status == "currently enrolled":
            enrolled_set.add(nc)

    enrolled_credits = sum(
        int(courses_map[nc].credit_hours or 0)
        for nc in enrolled_set if nc in courses_map
    )

    # ── 3. Remaining courses ────────────────────────────────────────────────
    remaining = {
        nc for nc in courses_map
        if nc not in completed_set and nc not in enrolled_set
    }

    if not remaining:
        return {
            "student_id": student_id,
            "completed_credits": completed_credits,
            "enrolled_credits": enrolled_credits,
            "remaining_credits": 0,
            "plan": [],
            "total_semesters": 0,
            "message": "Congratulations! You have completed all courses.",
        }

    # ── 4. Determine starting semester ──────────────────────────────────────
    import datetime
    now = datetime.datetime.now()
    month = now.month

    if month >= 9 or month <= 1:
        current_sem = "Fall"
    elif 2 <= month <= 5:
        current_sem = "Spring"
    else:
        current_sem = "Summer"

    academic_year = now.year if current_sem == "Fall" else now.year - 1

    next_idx = SEMESTER_ORDER.index(current_sem) + 1
    if next_idx >= len(SEMESTER_ORDER):
        next_idx = 0
        academic_year += 1

    # ── 5. Semester-by-semester scheduling ──────────────────────────────────
    plan_semesters: List[dict] = []
    done:          Set[str] = set(completed_set | enrolled_set)
    credits_so_far: int     = completed_credits + enrolled_credits
    to_schedule:   Set[str] = set(remaining)

    sem_ptr  = next_idx
    year_ptr = academic_year

    training_nc      = _normalize(TRAINING_COURSE)
    grad_projects_nc = {_normalize(gp) for gp in GRADUATION_PROJECTS}

    for _ in range(20):                                   # safety cap
        if not to_schedule:
            break

        sem_name = SEMESTER_ORDER[sem_ptr]
        max_cr   = MAX_CREDITS_SUMMER if sem_name == "Summer" else MAX_CREDITS_REGULAR
        is_summer = (sem_name == "Summer")

        # ── 5a. Build candidate list ────────────────────────────────────────
        candidates: List[str] = []

        if is_summer:
            # ── SUMMER RULES ────────────────────────────────────────────────
            # Rule 1: CS391 (training) goes ALONE — no other courses with it
            if training_nc in to_schedule:
                if _prereqs_met(training_nc, courses_map, done, set(), credits_so_far):
                    candidates = [training_nc]

            # Rule 2: if no training, allow delayed courses only
            if not candidates:
                # A course is "delayed" if we've already generated at least one
                # semester of its home type, meaning its official slot has passed.
                already_had_fall = any(
                    s["semester_type"] == "Fall" for s in plan_semesters
                )
                already_had_spring = any(
                    s["semester_type"] == "Spring" for s in plan_semesters
                )

                for nc in to_schedule:
                    if nc == training_nc:
                        continue
                    if nc in grad_projects_nc:                # no grad projects in summer
                        continue
                    locked = SEMESTER_LOCKED.get(nc)
                    if locked:                                # semester-locked → not in summer
                        continue
                    c = courses_map.get(nc)
                    if not c:
                        continue
                    if c.suggested_semester == "Summer":       # CS391 handled above
                        continue
                    # Only truly delayed courses
                    if c.suggested_semester == "Fall" and not already_had_fall:
                        continue
                    if c.suggested_semester == "Spring" and not already_had_spring:
                        continue
                    candidates.append(nc)

            # Nothing eligible for summer → skip it entirely
            if not candidates:
                sem_ptr += 1
                if sem_ptr >= len(SEMESTER_ORDER):
                    sem_ptr = 0
                    year_ptr += 1
                continue

        else:
            # ── FALL / SPRING ───────────────────────────────────────────────
            for nc in to_schedule:
                c = courses_map.get(nc)
                if not c:
                    continue
                # Semester-locked to a different type → skip
                locked = SEMESTER_LOCKED.get(nc)
                if locked and locked != sem_name:
                    continue
                # Summer-only courses (CS391) don't go in Fall/Spring
                if c.suggested_semester == "Summer":
                    continue
                candidates.append(nc)

        # ── 5b. Sort candidates by priority ─────────────────────────────────
        #   1. Home-semester courses first (suggested_semester matches)
        #   2. Earlier suggested_year first (lower year = more urgent)
        #   3. Compulsory before elective
        def _sort_key(nc: str) -> tuple:
            c = courses_map.get(nc)
            if not c:
                return (1, 4, 1, 1, nc)
            is_home = 0 if c.suggested_semester == sem_name else 1
            yr = c.suggested_year or 4
            sem_idx = (
                SEMESTER_ORDER.index(c.suggested_semester)
                if c.suggested_semester in SEMESTER_ORDER else 1
            )
            is_elective = 1 if c.plan_type and "Elective" in c.plan_type else 0
            return (is_home, yr, sem_idx, is_elective, nc)

        candidates.sort(key=_sort_key)

        # ── 5c. Pick courses (respecting co-requisites + credit cap) ───────
        picked:      Set[str]   = set()
        sem_courses: List[dict] = []
        sem_credits              = 0

        for nc in candidates:
            if nc in picked:
                continue

            c = courses_map.get(nc)
            if not c:
                continue
            ch = int(c.credit_hours or 0)

            # Check for a co-requisite partner that also needs scheduling
            co_raw = CO_REQUISITES.get(nc)
            co_nc  = _normalize(co_raw) if co_raw else None
            has_co = (
                co_nc is not None
                and co_nc in to_schedule
                and co_nc not in picked
                and co_nc not in done
            )

            if has_co:
                # ── Schedule the pair together ──────────────────────────────
                co_c  = courses_map.get(co_nc)
                co_ch = int(co_c.credit_hours or 0) if co_c else 0
                pair_total = ch + co_ch

                if pair_total > 0 and sem_credits + pair_total > max_cr:
                    continue

                pair = {nc, co_nc}
                if not _prereqs_met(nc, courses_map, done, pair, credits_so_far):
                    continue
                if co_c and not _prereqs_met(co_nc, courses_map, done, pair, credits_so_far):
                    continue

                sem_courses.append({
                    "course_code":  c.code,
                    "course_name":  c.name,
                    "credit_hours": ch,
                    "prerequisites": c.prerequisites or "None",
                    "plan_type":    c.plan_type or "",
                })
                if co_c:
                    sem_courses.append({
                        "course_code":  co_c.code,
                        "course_name":  co_c.name,
                        "credit_hours": co_ch,
                        "prerequisites": co_c.prerequisites or "None",
                        "plan_type":    co_c.plan_type or "",
                    })
                sem_credits += pair_total
                picked.add(nc)
                picked.add(co_nc)

            else:
                # ── Schedule single course ──────────────────────────────────
                if ch > 0 and sem_credits + ch > max_cr:
                    continue
                if not _prereqs_met(nc, courses_map, done, picked, credits_so_far):
                    continue

                sem_courses.append({
                    "course_code":  c.code,
                    "course_name":  c.name,
                    "credit_hours": ch,
                    "prerequisites": c.prerequisites or "None",
                    "plan_type":    c.plan_type or "",
                })
                sem_credits += ch
                picked.add(nc)

        # ── 5d. Finalize semester ───────────────────────────────────────────
        if sem_courses:
            if sem_name == "Fall":
                label = f"Fall {year_ptr}/{year_ptr + 1}"
            elif sem_name == "Spring":
                label = f"Spring {year_ptr}/{year_ptr + 1}"
            else:
                label = f"Summer {year_ptr + 1}"

            plan_semesters.append({
                "semester_label": label,
                "semester_type":  sem_name,
                "courses":        sem_courses,
                "total_hours":    sem_credits,
            })

            done.update(picked)
            to_schedule -= picked
            credits_so_far += sem_credits

        # Advance to next semester
        sem_ptr += 1
        if sem_ptr >= len(SEMESTER_ORDER):
            sem_ptr = 0
            year_ptr += 1

    # ── 6. Build response ───────────────────────────────────────────────────
    total_remaining = sum(
        int(courses_map[nc].credit_hours or 0)
        for nc in remaining if nc in courses_map
    )

    return {
        "student_id":       student_id,
        "completed_credits": completed_credits,
        "enrolled_credits":  enrolled_credits,
        "remaining_credits": total_remaining,
        "total_semesters":   len(plan_semesters),
        "plan":              plan_semesters,
    }
