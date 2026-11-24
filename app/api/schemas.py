from uuid import UUID
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: UUID | None = None

class EvaluationRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=20)
