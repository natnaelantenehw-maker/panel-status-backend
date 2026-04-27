from pydantic import BaseModel, EmailStr

class AccessRequestCreate(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class VerifyCodeResponse(BaseModel):
    success: bool
    email: str
    activatedAt: int
    expiresAt: int
    message: str