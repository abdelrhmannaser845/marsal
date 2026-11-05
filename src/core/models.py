from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class DispatchChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "wa"
    BOTH = "both"


class DispatchStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StudentGradeRecord(BaseModel):
    """Pydantic model representing a student grade record."""
    student_id: str = Field(..., description="Unique student registration/ID number")
    name: str = Field(..., description="Student full name")
    phone: str = Field(..., description="Standardized recipient phone number (E.164)")
    email: Optional[str] = Field(default=None, description="Student email address")
    course: str = Field(default="General Academic Course", description="Course name and semester")
    
    # Grade breakdown
    midterm: Optional[float] = Field(default=None, description="Midterm score")
    midterm_max: float = Field(default=15.0, description="Midterm maximum possible score")
    lab: Optional[float] = Field(default=None, description="Lab / Practical score")
    lab_max: float = Field(default=37.0, description="Lab maximum possible score")
    oral: Optional[float] = Field(default=None, description="Oral examination score")
    oral_max: float = Field(default=8.0, description="Oral maximum possible score")
    bonus: float = Field(default=0.0, description="Extra bonus points added")
    total: Optional[float] = Field(default=None, description="Total score")
    total_max: float = Field(default=60.0, description="Total maximum possible score")
    
    notes: Optional[str] = Field(default=None, description="Custom instructor remarks")
    extra_fields: Dict[str, Any] = Field(default_factory=dict, description="Additional custom CSV/Excel columns")

    @property
    def formatted_scores(self) -> str:
        """Returns the formatted score string: '12/15, 15/37, 5/8, 32/60.'"""
        m = f"{int(self.midterm) if self.midterm is not None and self.midterm.is_integer() else self.midterm}/{int(self.midterm_max)}" if self.midterm is not None else "-/15"
        l = f"{int(self.lab) if self.lab is not None and self.lab.is_integer() else self.lab}/{int(self.lab_max)}" if self.lab is not None else "-/37"
        o = f"{int(self.oral) if self.oral is not None and self.oral.is_integer() else self.oral}/{int(self.oral_max)}" if self.oral is not None else "-/8"
        t = f"{int(self.total) if self.total is not None and self.total.is_integer() else self.total}/{int(self.total_max)}" if self.total is not None else "-/60"
        return f"{m}, {l}, {o}, {t}"

    @property
    def computed_total(self) -> float:
        """Returns total score, computing sum of components + bonus if not provided directly."""
        if self.total is not None:
            return self.total
        s = 0.0
        if self.midterm is not None:
            s += self.midterm
        if self.lab is not None:
            s += self.lab
        if self.oral is not None:
            s += self.oral
        s += self.bonus
        return round(s, 2)


class DispatchResult(BaseModel):
    """Result of a notification delivery attempt."""
    student_id: str
    recipient: str
    channel: DispatchChannel
    status: DispatchStatus
    message_snippet: str = ""
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
