from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, model_validator, constr

class SourceType(str, Enum):
    NOTE = "note"
    URL = "url"

class IngestRequest(BaseModel):
    source_type: SourceType = Field(description="The type of the source being ingested ('note' or 'url').")
    content: Optional[str] = Field(None, description="The plain text content if the source_type is 'note'.")
    url: Optional[HttpUrl] = Field(None, description="The valid URL if the source_type is 'url'.")
    title: Optional[str] = Field(None, description="An optional title for the document.")

    @model_validator(mode='after')
    def validate_content_and_url(self) -> 'IngestRequest':
        # Trim title if present
        if self.title is not None:
            self.title = self.title.strip()
            
        if self.source_type == SourceType.NOTE:
            if self.url is not None:
                raise ValueError("URL must not be provided when source_type is 'note'.")
            if self.content is None or not self.content.strip():
                raise ValueError("Content must be provided and non-empty when source_type is 'note'.")
            self.content = self.content.strip()
            
        elif self.source_type == SourceType.URL:
            if self.content is not None:
                raise ValueError("Content must not be provided when source_type is 'url'.")
            if self.url is None:
                raise ValueError("URL must be provided when source_type is 'url'.")
                
        return self

class IngestResponse(BaseModel):
    id: str = Field(description="The unique identifier of the newly ingested document.")
    source_type: SourceType = Field(description="The type of the ingested document.")
    title: Optional[str] = Field(None, description="The title of the document, if available.")
    url: Optional[str] = Field(None, description="The source URL, if applicable.")
    created_at: datetime = Field(description="The timestamp when the document was ingested.")
    chunk_count: Optional[int] = Field(None, description="The number of text chunks generated, if available.")

class ItemResponse(BaseModel):
    id: str = Field(description="The unique identifier of the document.")
    source_type: SourceType = Field(description="The type of the document.")
    title: Optional[str] = Field(None, description="The title of the document.")
    source: Optional[str] = Field(None, description="The source URL or identifier of the document.")
    created_at: datetime = Field(description="The timestamp when the document was ingested.")

class QueryRequest(BaseModel):
    question: constr(strip_whitespace=True, min_length=1, max_length=1000) = Field(
        description="The question to ask the AI."
    )

class SourceSnippet(BaseModel):
    document_id: str = Field(description="The unique identifier of the source document.")
    source_type: SourceType = Field(description="The type of the source document.")
    title: Optional[str] = Field(None, description="The title of the document.")
    url: Optional[str] = Field(None, description="The source URL, if applicable.")
    content: str = Field(description="The text snippet or chunk that was used to generate the answer.")
    relevance_score: Optional[float] = Field(None, description="The relevance score of the chunk.")

class QueryResponse(BaseModel):
    answer: str = Field(description="The AI-generated answer to the question.")
    sources: List[SourceSnippet] = Field(description="The sources used to generate the answer.")
