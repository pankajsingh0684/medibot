from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    BILLING_EXECUTIVE = "billing_executive"
    TECHNICIAN = "technician"
    ADMIN = "admin"


class Collection(StrEnum):
    GENERAL = "general"
    CLINICAL = "clinical"
    NURSING = "nursing"
    BILLING = "billing"
    EQUIPMENT = "equipment"


ROLE_COLLECTIONS: dict[Role, list[Collection]] = {
    Role.DOCTOR: [Collection.CLINICAL, Collection.GENERAL],
    Role.NURSE: [Collection.NURSING, Collection.GENERAL],
    Role.BILLING_EXECUTIVE: [Collection.BILLING, Collection.GENERAL],
    Role.TECHNICIAN: [Collection.EQUIPMENT, Collection.GENERAL],
    Role.ADMIN: list(Collection),
}

COLLECTION_ACCESS_ROLES: dict[Collection, list[Role]] = {
    collection: [
        role
        for role, collections in ROLE_COLLECTIONS.items()
        if collection in collections
    ]
    for collection in Collection
}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class CollectionResponse(BaseModel):
    role: Role
    collections: list[Collection]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    source_document: str
    section_title: str
    collection: Collection
    headings: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)


class TokenData(BaseModel):
    username: str
    role: Role
