from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    initialize_database,
    get_all_sessions,
    add_session,
    update_session,
    delete_session,
    get_all_tasks,
    add_task,
    update_task,
    delete_task,
    get_subject_analytics,
    get_daily_analytics,
)
from backend.models import (
    StudySessionCreate,
    StudySessionUpdate,
    TaskCreate,
    TaskUpdate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Smart Study Planner API",
    description=(
        "Advanced API for study sessions, tasks, "
        "progress analytics, and study recommendations."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Smart Study Planner API is running",
        "version": "2.0.0",
        "docs": "/docs",
    }


# ---------------- STUDY SESSIONS ----------------

@app.get("/api/sessions")
def list_sessions():
    return get_all_sessions()


@app.post("/api/sessions", status_code=201)
def create_session(session: StudySessionCreate):
    subject = session.subject.strip()

    if not subject:
        raise HTTPException(
            status_code=422,
            detail="Subject cannot be empty.",
        )

    return add_session(
        subject,
        session.minutes,
        session.date.isoformat(),
    )


@app.put("/api/sessions/{session_id}")
def edit_session(
    session_id: int,
    session: StudySessionUpdate,
):
    subject = session.subject.strip()

    if not subject:
        raise HTTPException(
            status_code=422,
            detail="Subject cannot be empty.",
        )

    updated = update_session(
        session_id,
        subject,
        session.minutes,
        session.date.isoformat(),
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Study session not found.",
        )

    return updated


@app.delete("/api/sessions/{session_id}")
def remove_session(session_id: int):
    if not delete_session(session_id):
        raise HTTPException(
            status_code=404,
            detail="Study session not found.",
        )

    return {"message": "Study session deleted successfully."}


# ---------------- DASHBOARD ----------------

@app.get("/api/dashboard")
def dashboard_summary(
    on_date: date = Query(
        default_factory=date.today,
        alias="date",
    ),
):
    sessions = get_all_sessions()

    today_sessions = [
        session for session in sessions
        if session["date"] == on_date.isoformat()
    ]

    return {
        "date": on_date.isoformat(),
        "today_minutes": sum(
            session["minutes"] for session in today_sessions
        ),
        "today_sessions": len(today_sessions),
        "total_minutes": sum(
            session["minutes"] for session in sessions
        ),
        "total_sessions": len(sessions),
        "active_days": len({
            session["date"] for session in sessions
        }),
    }


# ---------------- CALENDAR ----------------

@app.get("/api/calendar")
def calendar_summary(
    month: str = Query(
        description="Calendar month in YYYY-MM format",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
):
    try:
        year, month_number = map(int, month.split("-"))
        start = date(year, month_number, 1)

        if month_number == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month_number + 1, 1) - timedelta(days=1)

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Month must use YYYY-MM format.",
        )

    return get_daily_analytics(
        start.isoformat(),
        end.isoformat(),
    )


# ---------------- TASKS ----------------

@app.get("/api/tasks")
def list_tasks():
    return get_all_tasks()


@app.post("/api/tasks", status_code=201)
def create_task(task: TaskCreate):
    title = task.title.strip()
    subject = task.subject.strip()

    if not title or not subject:
        raise HTTPException(
            status_code=422,
            detail="Task title and subject cannot be empty.",
        )

    return add_task(
        title,
        subject,
        task.due_date.isoformat(),
        task.priority,
    )


@app.patch("/api/tasks/{task_id}")
def edit_task(task_id: int, task: TaskUpdate):
    changes = task.dict(exclude_unset=True)

    if "title" in changes and changes["title"] is not None:
        changes["title"] = changes["title"].strip()
        if not changes["title"]:
            raise HTTPException(
                status_code=422,
                detail="Task title cannot be empty.",
            )

    if "subject" in changes and changes["subject"] is not None:
        changes["subject"] = changes["subject"].strip()
        if not changes["subject"]:
            raise HTTPException(
                status_code=422,
                detail="Subject cannot be empty.",
            )

    if "due_date" in changes and changes["due_date"] is not None:
        changes["due_date"] = changes["due_date"].isoformat()

    updated = update_task(task_id, changes)

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    return updated


@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    if not delete_task(task_id):
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    return {"message": "Task deleted successfully."}


# ---------------- ANALYTICS ----------------

@app.get("/api/analytics/subjects")
def subject_analytics():
    return get_subject_analytics()


@app.get("/api/analytics/daily")
def daily_analytics(
    days: int = Query(default=7, ge=1, le=365),
):
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    daily_rows = get_daily_analytics(
        start_date.isoformat(),
        end_date.isoformat(),
    )

    # Include dates with zero study minutes.
    by_date = {
        row["date"]: row
        for row in daily_rows
    }

    result = []
    for offset in range(days):
        current_date = start_date + timedelta(days=offset)
        day_string = current_date.isoformat()

        result.append(
            by_date.get(
                day_string,
                {
                    "date": day_string,
                    "total_minutes": 0,
                    "total_sessions": 0,
                },
            )
        )

    return result


# ---------------- STUDY RECOMMENDATIONS ----------------

@app.get("/api/recommendations")
def study_recommendations():
    today = date.today()
    sessions = get_all_sessions()
    tasks = get_all_tasks()
    subjects = get_subject_analytics()

    recent_start = today - timedelta(days=6)

    recent_sessions = [
        session for session in sessions
        if recent_start.isoformat()
        <= session["date"]
        <= today.isoformat()
    ]

    recent_minutes = sum(
        session["minutes"] for session in recent_sessions
    )

    incomplete_tasks = [
        task for task in tasks
        if not task["completed"]
    ]

    overdue_tasks = [
        task for task in incomplete_tasks
        if task["due_date"] < today.isoformat()
    ]

    due_today_tasks = [
        task for task in incomplete_tasks
        if task["due_date"] == today.isoformat()
    ]

    recommendations = []

    if overdue_tasks:
        recommendations.append({
            "type": "priority",
            "message": (
                f"You have {len(overdue_tasks)} overdue task(s). "
                "Consider completing these first."
            ),
        })

    if due_today_tasks:
        recommendations.append({
            "type": "deadline",
            "message": (
                f"{len(due_today_tasks)} task(s) are due today. "
                "Prioritize them in your study plan."
            ),
        })

    if recent_minutes < 300:
        recommendations.append({
            "type": "consistency",
            "message": (
                "You have studied less than 5 hours in the last "
                "7 days. Try scheduling a short daily study session."
            ),
        })
    else:
        recommendations.append({
            "type": "progress",
            "message": (
                f"Good progress: you studied "
                f"{recent_minutes // 60} hour(s) and "
                f"{recent_minutes % 60} minute(s) in the last 7 days."
            ),
        })

    if subjects:
        least_studied = min(
            subjects,
            key=lambda item: item["total_minutes"],
        )

        recommendations.append({
            "type": "subject",
            "message": (
                f"Consider reviewing {least_studied['subject']}; "
                "it has your lowest recorded total study time."
            ),
            "subject": least_studied["subject"],
        })
    else:
        recommendations.append({
            "type": "subject",
            "message": (
                "Add your first study session to get "
                "subject-based recommendations."
            ),
        })

    return {
        "generated_for": today.isoformat(),
        "recent_7_day_minutes": recent_minutes,
        "incomplete_tasks": len(incomplete_tasks),
        "overdue_tasks": len(overdue_tasks),
        "recommendations": recommendations,
    }