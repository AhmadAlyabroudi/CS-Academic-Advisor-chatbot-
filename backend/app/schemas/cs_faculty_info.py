from pydantic import BaseModel

class FacultySchema(BaseModel):
    name: str
    email: str
    office_location: str
    office_hours: str
    title: str | None = None

    class Config:
        from_attributes = True