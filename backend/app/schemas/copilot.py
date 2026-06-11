from datetime import datetime

from pydantic import BaseModel, Field


class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1000)


class CopilotInsightCard(BaseModel):
    title: str
    value: str
    detail: str
    tone: str = "info"


class CopilotMessage(BaseModel):
    id: int
    role: str
    content: str
    cards: list[CopilotInsightCard] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    created_at: datetime


class CopilotChatResponse(BaseModel):
    user_message: CopilotMessage
    assistant_message: CopilotMessage
