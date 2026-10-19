from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class StudySessionCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    minutes: int = Field(gt=0, le=1440)
    date: date


class StudySessionUpdate(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    minutes: int = Field(gt=0, le=1440)
    date: date


class StudySessionResponse(BaseModel):
    id: int
    subject: str
    minutes: int
    date: date
    created_at: str


class DashboardSummary(BaseModel):
    today_minutes: int
    total_minutes: int
    total_sessions: int
    active_days: int


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    subject: str = Field(min_length=1, max_length=100)
    due_date: date
    priority: Literal["Low", "Medium", "High"] = "Medium"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    subject: str | None = Field(default=None, min_length=1, max_length=100)
    due_date: date | None = None
    priority: Literal["Low", "Medium", "High"] | None = None
    completed: bool | None = None