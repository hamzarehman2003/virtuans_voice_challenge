from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class QARequest(BaseModel):
    question: str = Field(..., min_length=2)
    top_k: Optional[int] = None


class SourceChunk(BaseModel):
    id: str
    similarity: float
    url: Optional[str] = None
    title: Optional[str] = None
    source_file: Optional[str] = None
    chunk_index: Optional[int] = None
    preview: str


class QAResponse(BaseModel):
    question: str
    has_context: bool
    answers: Dict[str, str]
    sources: List[SourceChunk]


class SynthesisRequest(BaseModel):
    text: str
    model: str

