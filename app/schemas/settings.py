from pydantic import BaseModel, Field


class PromptUpdate(BaseModel):
    prompt: str = Field(min_length=1)
