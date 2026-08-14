from pydantic import BaseModel, EmailStr


class AdminOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str


class AdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
