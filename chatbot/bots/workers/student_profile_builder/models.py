from typing import List, Any

from pydantic import BaseModel, Field


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



class StudentProfileSchema(BaseModel):
    topics_of_interest: str = Field('', description="The specific aspects or themes in neural control of human movement that the student is interested in, May include scientific areas (e.g. biomechanics, neuroscience, clinical practice, vision and oculomotor control, etc.), specific research questions (e.g. how does the brain control movement, how does the brain learn, how does the brain adapt, etc.), specific techniques (e.g. motion capture, computer vision, computational modeling, machine learning, etc.), specific applications (e.g. stroke rehabilitation, prosthetics, etc.), types of movement (sports, dance, etc).")
    programming_experience: str = Field('', description="The level of programming experience the student has (specifically Python). This can include specific languages or tools they are familiar with, projects they've worked on, etc. ")
    research_experience: str = Field('', description="Any research projects or experiences the student has participated in. Detailing the nature of the projects, their role, and the skills they've acquired through these experiences.")
    current_skillset: str = Field('', description="A description of the skills the student currently possesses. Can include both technical skills like programming or data analysis, and soft skills like collaboration or project management.")
    desired_skillset: str = Field('', description="The skills the student hopes to acquire or improve upon throughout the course. This will help tailor the course and the project to the learning objectives of the student.")
    personal_interests: str = Field('', description="Interests outside of the academic context. This can help identify unique perspectives or potential cross-disciplinary connections that could be brought into the course.")
    project_ideas: str = Field('', description="Any project ideas the student might already have for the course. This can help to seed the collaborative brainstorming process and align projects with students' interests.")