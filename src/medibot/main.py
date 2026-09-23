import logging
import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from medibot.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from medibot.config import Settings, get_settings
from medibot.models import (
    ROLE_COLLECTIONS,
    ChatRequest,
    ChatResponse,
    CollectionResponse,
    LoginRequest,
    LoginResponse,
    Role,
    TokenData,
)
from medibot.rag import answer_question

logger = logging.getLogger(__name__)
app = FastAPI(title="MediBot API", version="0.1.0")
security = HTTPBearer(auto_error=False)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def demo_users(settings: Settings) -> dict[str, tuple[str, Role]]:
    password = hash_password(settings.demo_password)
    return {
        "dr.mehta": (password, Role.DOCTOR),
        "nurse.priya": (password, Role.NURSE),
        "billing.ravi": (password, Role.BILLING_EXECUTIVE),
        "tech.anand": (password, Role.TECHNICIAN),
        "admin.sys": (password, Role.ADMIN),
    }


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> TokenData:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials, get_settings())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    user = demo_users(settings).get(request.username)
    if user is None or not verify_password(request.password, user[0]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    return LoginResponse(
        access_token=create_access_token(request.username, user[1], settings),
        role=user[1],
    )


@app.get("/collections/{role}", response_model=CollectionResponse)
def collections(role: Role) -> CollectionResponse:
    return CollectionResponse(role=role, collections=ROLE_COLLECTIONS[role])


@app.post("/chat")
def chat(
    request: ChatRequest, user: Annotated[TokenData, Depends(get_current_user)]
) -> ChatResponse:
    try:
        return answer_question(request.question, user, get_settings())
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(error)
        ) from error
    except RuntimeError as error:
        logger.exception("MediBot dependencies are not ready for chat")
        detail = str(error)
        if "GROQ_API_KEY" in detail:
            message = "Document answers require GROQ_API_KEY in the backend .env file."
        elif "Qdrant collection" in detail:
            message = detail
        else:
            message = "MediBot is not ready to answer this question."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        ) from None
