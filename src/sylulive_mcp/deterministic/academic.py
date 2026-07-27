"""学业快照的可复核本地计算。"""

from __future__ import annotations

from typing import Any

from ..schemas.academic import AcademicSnapshot, CourseRecord

_FAILED_TEXT_GRADES = frozenset({"f", "fail", "failed", "不及格", "挂科"})


def _is_failed(course: CourseRecord) -> bool:
    """按显式通过状态优先、成绩次之的规则识别挂科。"""

    if course.passed is not None:
        return not course.passed
    if course.grade is None:
        return False
    if isinstance(course.grade, (int, float)):
        return course.grade < 60
    grade = course.grade.strip().lower()
    if grade in _FAILED_TEXT_GRADES:
        return True
    try:
        return float(grade) < 60
    except ValueError:
        return False


def _grade_unknown(course: CourseRecord) -> bool:
    """判断是否既没有显式通过状态也没有成绩。"""

    return course.passed is None and course.grade is None


def analyze_academic_snapshot(snapshot: AcademicSnapshot) -> dict[str, Any]:
    """计算学分、挂科、二课和数据完整度，不依赖任何模型推断。"""

    failed_courses = [course for course in snapshot.courses if _is_failed(course)]
    failed_required_credits = sum(
        course.credits or 0 for course in failed_courses if course.is_required
    )
    failed_credits = sum(course.credits or 0 for course in failed_courses)
    unknown_grade_courses = [course for course in snapshot.courses if _grade_unknown(course)]
    missing_credit_courses = [
        course for course in snapshot.courses if course.credits is None or course.credits <= 0
    ]
    complete_fields = 0
    total_fields = len(snapshot.courses) * 3
    for course in snapshot.courses:
        complete_fields += int(bool(course.course_name.strip()))
        complete_fields += int(course.credits is not None and course.credits > 0)
        complete_fields += int(not _grade_unknown(course))
    completeness = 100.0 if total_fields == 0 else round(complete_fields / total_fields * 100, 2)

    return {
        "failed_course_count": len(failed_courses),
        "failed_credits": round(failed_credits, 2),
        "failed_required_credits": round(failed_required_credits, 2),
        "earned_credits": round(snapshot.earned_credits, 2),
        "required_credits": round(snapshot.required_credits, 2),
        "credit_gap": round(max(snapshot.required_credits - snapshot.earned_credits, 0), 2),
        "erke_gap": round(max(snapshot.erke_required - snapshot.erke_earned, 0), 2),
        "unknown_grade_course_count": len(unknown_grade_courses),
        "missing_credit_course_count": len(missing_credit_courses),
        "data_completeness_percent": completeness,
        "failed_courses": [course.course_name for course in failed_courses],
        "gpa": snapshot.gpa,
    }
