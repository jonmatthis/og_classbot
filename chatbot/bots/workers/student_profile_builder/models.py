from typing import List, Any

from pydantic import BaseModel


class UpsertPayload(BaseModel):
    ai_question: str
    human_answer: str

    # mongo collection
    collection: Any

    # unique identifier for your model document in mongodb
    query: dict

    # the pydantic model you are storing as a document
    model: BaseModel


class ModelUpdateResponse(BaseModel):
    model: BaseModel
    questions: List[str]


class ModelUpdatePayload(BaseModel):
    ai_question: str
    human_answer: str
    model: BaseModel


class InterviewGuidance(BaseModel):
    questions: List[str]


class StudentInterviewSchema(BaseModel):
    topics_of_interest: str = ''
    programming_experience: str = ''
    research_experience: str = ''
    personal_interests: str = ''
    current_skillset: str = ''
    desired_skillset: str = ''
    hobbies: str = ''
    project_ideas: str = ''
