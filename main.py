from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from database import Base, engine, SessionLocal
from models import AccessRequest
from schemas import AccessRequestCreate, VerifyCodeRequest, VerifyCodeResponse
from email_service import send_admin_request_email, send_user_code_email

app = FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_code() -> str:
    return str(random.randint(100000, 999999))

@app.post("/request-access")
async def request_access(payload: AccessRequestCreate, db: Session = Depends(get_db)):
    existing = db.query(AccessRequest).filter(
        AccessRequest.email == payload.email,
        AccessRequest.is_used == False,
        AccessRequest.request_status.in_(["pending", "approved"])
    ).first()

    if existing:
        return {"message": "Request already exists for this email."}

    request_row = AccessRequest(
        email=payload.email,
        request_status="pending"
    )
    db.add(request_row)
    db.commit()

    await send_admin_request_email(payload.email)

    return {"message": "Access request submitted successfully."}

@app.post("/admin/approve")
async def approve_access(email: str, duration_months: int, db: Session = Depends(get_db)):
    request_row = db.query(AccessRequest).filter(
        AccessRequest.email == email,
        AccessRequest.request_status == "pending"
    ).order_by(AccessRequest.created_at.desc()).first()

    if not request_row:
        raise HTTPException(status_code=404, detail="Pending request not found.")

    code = generate_code()
    now = datetime.utcnow()
    code_expires_at = now + timedelta(minutes=30)

    if duration_months == 3:
        access_expires_at = now + timedelta(days=90)
        duration_label = "3 months"
    elif duration_months == 6:
        access_expires_at = now + timedelta(days=180)
        duration_label = "6 months"
    elif duration_months == 12:
        access_expires_at = now + timedelta(days=365)
        duration_label = "1 year"
    else:
        raise HTTPException(status_code=400, detail="Only 3, 6, or 12 months allowed.")

    request_row.code = code
    request_row.request_status = "approved"
    request_row.code_expires_at = code_expires_at
    request_row.access_expires_at = access_expires_at
    request_row.approved_at = now

    db.commit()

    await send_user_code_email(email, code, duration_label)

    return {"message": f"Approved {email} for {duration_label}."}

@app.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(payload: VerifyCodeRequest, db: Session = Depends(get_db)):
    request_row = db.query(AccessRequest).filter(
        AccessRequest.email == payload.email,
        AccessRequest.code == payload.code,
        AccessRequest.request_status == "approved",
        AccessRequest.is_used == False
    ).order_by(AccessRequest.created_at.desc()).first()

    if not request_row:
        return VerifyCodeResponse(
            success=False,
            email=payload.email,
            activatedAt=0,
            expiresAt=0,
            message="Invalid code."
        )

    now = datetime.utcnow()

    if request_row.code_expires_at is None or now > request_row.code_expires_at:
        return VerifyCodeResponse(
            success=False,
            email=payload.email,
            activatedAt=0,
            expiresAt=0,
            message="Code expired."
        )

    request_row.is_used = True
    db.commit()

    return VerifyCodeResponse(
        success=True,
        email=request_row.email,
        activatedAt=int(now.timestamp() * 1000),
        expiresAt=int(request_row.access_expires_at.timestamp() * 1000),
        message="Access granted."
    )

@app.get("/admin/requests")
def get_requests(db: Session = Depends(get_db)):
    requests = db.query(AccessRequest).order_by(AccessRequest.created_at.desc()).all()

    return [
        {
            "email": r.email,
            "status": r.request_status,
            "created_at": r.created_at,
            "approved_at": r.approved_at,
            "is_used": r.is_used
        }
        for r in requests
    ]