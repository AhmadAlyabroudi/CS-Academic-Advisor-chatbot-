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


def get_semester_index(year: int, semester: str) -> int:
    """Map year (1-4) and semester (Fall/Spring/Summer) to a chronological index (0 to 11)."""
    sem_val = 0
    if semester == "Fall":
        sem_val = 0
    elif semester == "Spring":
        sem_val = 1
    elif semester == "Summer":
        sem_val = 2
    return (year - 1) * 3 + sem_val


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

    # ── 4. Determine starting year and semester ─────────────────────────────
    # Detect the current academic year and semester based on the student's
    # current enrollment. If no enrolled courses exist, estimate from the first incomplete semester.
    student_current_year = 1
    student_current_semester = "Fall"
    has_active_enrollment = False

    if enrolled_set:
        from collections import Counter
        enrolled_years = []
        enrolled_sems = []
        for nc in enrolled_set:
            c_info = courses_map.get(nc)
            if c_info:
                enrolled_years.append(c_info.suggested_year)
                enrolled_sems.append(c_info.suggested_semester)
        if enrolled_years:
            student_current_year = Counter(enrolled_years).most_common(1)[0][0]
            student_current_semester = Counter(enrolled_sems).most_common(1)[0][0]
            has_active_enrollment = True

    if not has_active_enrollment:
        # Find first incomplete semester chronologically
        first_incomplete_idx = 11  # Year 4 Summer max index
        for nc in remaining:
            c_info = courses_map.get(nc)
            if c_info:
                idx = get_semester_index(c_info.suggested_year or 4, c_info.suggested_semester or "Fall")
                if idx < first_incomplete_idx:
                    first_incomplete_idx = idx

        # Decode index back to year and semester
        student_current_year = (first_incomplete_idx // 3) + 1
        sem_val = first_incomplete_idx % 3
        if sem_val == 0:
            student_current_semester = "Fall"
        elif sem_val == 1:
            student_current_semester = "Spring"
        else:
            student_current_semester = "Summer"

    import datetime
    now = datetime.datetime.now()

    # The graduation plan begins in the semester immediately following the current active enrollment.
    # If the student is not currently enrolled, the plan starts in the current estimated semester itself.
    plan_sem = student_current_semester
    plan_year = student_current_year
    academic_year = now.year if plan_sem == "Fall" else now.year - 1

    if has_active_enrollment:
        if plan_sem == "Fall":
            plan_sem = "Spring"
        elif plan_sem == "Spring":
            plan_sem = "Summer"
        elif plan_sem == "Summer":
            plan_sem = "Fall"
            plan_year += 1
            academic_year += 1

    # ── 5. Semester-by-semester scheduling ──────────────────────────────────
    plan_semesters: List[dict] = []
    done:          Set[str] = set(completed_set | enrolled_set)
    credits_so_far: int     = completed_credits + enrolled_credits
    to_schedule:   Set[str] = set(remaining)

    training_nc      = _normalize(TRAINING_COURSE)
    grad_projects_nc = {_normalize(gp) for gp in GRADUATION_PROJECTS}

    for _ in range(20):                                   # safety cap
        if not to_schedule:
            break

        is_summer = (plan_sem == "Summer")
        current_plan_index = get_semester_index(plan_year, plan_sem)

        # Calculate credit limits (max_cr) dynamically
        if not is_summer:
            # Calculate standard credit hours for this semester in the official roadmap
            official_sem_credits = sum(
                int(c.credit_hours or 0)
                for c in courses_map.values()
                if c.suggested_year == plan_year and c.suggested_semester == plan_sem
            )
            if official_sem_credits == 0:
                official_sem_credits = 15

            # Find all unlocked delayed courses for this semester
            unlocked_delayed = []
            for nc in to_schedule:
                c_info = courses_map.get(nc)
                if c_info:
                    c_idx = get_semester_index(c_info.suggested_year or 4, c_info.suggested_semester or "Fall")
                    if c_idx < current_plan_index:
                        if _prereqs_met(nc, courses_map, done, set(), credits_so_far):
                            unlocked_delayed.append(nc)

            if unlocked_delayed:
                # Check if we can defer all delayed courses to summer
                must_schedule_now = False
                total_delayed_credits = 0
                for nc in unlocked_delayed:
                    c_info = courses_map[nc]
                    total_delayed_credits += int(c_info.credit_hours or 0)

                    # 1. Graduation projects and semester-locked courses cannot be deferred to summer
                    if nc in grad_projects_nc or SEMESTER_LOCKED.get(nc):
                        must_schedule_now = True

                    # 2. Final year courses should be finished immediately (don't delay graduation to a summer after Year 4)
                    if plan_year >= 4:
                        must_schedule_now = True

                    # 3. Prerequisites for the immediate next semester cannot wait for summer
                    if plan_sem == "Fall":
                        for other_nc in to_schedule:
                            if other_nc == nc:
                                continue
                            other_c = courses_map.get(other_nc)
                            if other_c:
                                prereqs, _ = _parse_prerequisites(other_c.prerequisites)
                                if nc in prereqs:
                                    other_idx = get_semester_index(other_c.suggested_year or 4, other_c.suggested_semester or "Fall")
                                    if other_idx <= current_plan_index + 1:
                                        must_schedule_now = True
                                        break

                # Upcoming summer capacity is 9 credits (adjusted for Year 3 Training CS391)
                summer_capacity = 9
                if plan_year == 3 and training_nc in to_schedule:
                    summer_capacity -= 3

                if must_schedule_now or total_delayed_credits > summer_capacity:
                    max_cr = MAX_CREDITS_REGULAR
                else:
                    max_cr = official_sem_credits
            else:
                max_cr = official_sem_credits
        else:
            max_cr = MAX_CREDITS_SUMMER

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
                    # Only delayed courses
                    c_idx = get_semester_index(c.suggested_year or 4, c.suggested_semester or "Fall")
                    if c_idx < current_plan_index:
                        candidates.append(nc)

            # Nothing eligible for summer → skip it entirely
            if not candidates:
                if plan_sem == "Fall":
                    plan_sem = "Spring"
                elif plan_sem == "Spring":
                    plan_sem = "Summer"
                elif plan_sem == "Summer":
                    plan_sem = "Fall"
                    plan_year += 1
                    academic_year += 1
                continue

        else:
            # ── FALL / SPRING ───────────────────────────────────────────────
            for nc in to_schedule:
                c = courses_map.get(nc)
                if not c:
                    continue
                # Semester-locked to a different type → skip
                locked = SEMESTER_LOCKED.get(nc)
                if locked and locked != plan_sem:
                    continue
                # Summer-only courses (CS391) don't go in Fall/Spring
                if c.suggested_semester == "Summer":
                    continue
                candidates.append(nc)

        # ── 5b. Sort candidates by priority ─────────────────────────────────
        #   1. Delayed courses first (is_delayed = 0, else 1)
        #   2. Chronological suggested year
        #   3. Chronological suggested semester index
        #   4. Home semester matching
        #   5. Compulsory before elective
        def _sort_key(nc: str) -> tuple:
            c = courses_map.get(nc)
            if not c:
                return (1, 4, 1, 1, 1, nc)
            c_idx = get_semester_index(c.suggested_year or 4, c.suggested_semester or "Fall")
            is_delayed = 0 if c_idx < current_plan_index else 1
            is_home = 0 if c.suggested_semester == plan_sem else 1
            yr = c.suggested_year or 4
            sem_idx = (
                SEMESTER_ORDER.index(c.suggested_semester)
                if c.suggested_semester in SEMESTER_ORDER else 1
            )
            is_elective = 1 if c.plan_type and "Elective" in c.plan_type else 0
            return (is_delayed, yr, sem_idx, is_home, is_elective, nc)

        candidates.sort(key=_sort_key)

        # ── 5c. Pick courses (respecting co-requisites + credit cap) ────────
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
            if plan_sem == "Fall":
                label = f"Fall {academic_year}/{academic_year + 1}"
            elif plan_sem == "Spring":
                label = f"Spring {academic_year}/{academic_year + 1}"
            else:
                label = f"Summer {academic_year + 1}"

            plan_semesters.append({
                "semester_label": label,
                "semester_type":  plan_sem,
                "courses":        sem_courses,
                "total_hours":    sem_credits,
            })

            done.update(picked)
            to_schedule -= picked
            credits_so_far += sem_credits

        # Advance to next semester
        if plan_sem == "Fall":
            plan_sem = "Spring"
        elif plan_sem == "Spring":
            plan_sem = "Summer"
        elif plan_sem == "Summer":
            plan_sem = "Fall"
            plan_year += 1
            academic_year += 1

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
