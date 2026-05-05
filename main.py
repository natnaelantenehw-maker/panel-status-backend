

import os
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from database import Base, engine, SessionLocal
from models import AccessRequest
from schemas import AccessRequestCreate, VerifyCodeRequest, VerifyCodeResponse
from email_service import send_admin_request_email, send_user_code_email
from fastapi import Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Query


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




@app.get("/admin", response_class=HTMLResponse)
def admin_page(password: str = Query(...), db: Session = Depends(get_db)):
    if password != ADMIN_PASSWORD:
        return HTMLResponse(content="<h2>Unauthorized</h2>", status_code=403)
    requests = db.query(AccessRequest).order_by(
        AccessRequest.request_status.desc(),
        AccessRequest.created_at.desc()
    ).all()

    total_count = len(requests)
    pending_count = len([r for r in requests if r.request_status == "pending"])
    approved_count = len([r for r in requests if r.request_status == "approved"])
    used_count = len([r for r in requests if r.is_used])

    rows = ""

    for r in requests:
        approved_at = r.approved_at if r.approved_at else "-"
        used = "Yes" if r.is_used else "No"
        row_style = "background-color: #fff8e1;" if r.request_status == "pending" else ""

        if r.request_status == "pending":
            action_buttons = f"""
                <form method="post" action="/admin/approve-web" style="display:inline;">
                    <input type="hidden" name="password" value="{ADMIN_PASSWORD}">
                    <input type="hidden" name="email" value="{r.email}">
                    <input type="hidden" name="duration_months" value="3">
                    <button class="btn3" type="submit">3 Months</button>
                </form>

                <form method="post" action="/admin/approve-web" style="display:inline;">
                    <input type="hidden" name="password" value="{ADMIN_PASSWORD}">
                    <input type="hidden" name="email" value="{r.email}">
                    <input type="hidden" name="duration_months" value="6">
                    <button class="btn6" type="submit">6 Months</button>
                </form>

                <form method="post" action="/admin/approve-web" style="display:inline;">
                    <input type="hidden" name="password" value="{ADMIN_PASSWORD}">
                    <input type="hidden" name="email" value="{r.email}">
                    <input type="hidden" name="duration_months" value="12">
                    <button class="btn12" type="submit">1 Year</button>
                </form>
            """
        else:
            action_buttons = "<span class='disabled'>No action</span>"

        rows += f"""
            <tr style="{row_style}">
                <td>{r.email}</td>
                <td class="{r.request_status}">{r.request_status}</td>
                <td>{used}</td>
                <td>{r.created_at}</td>
                <td>{approved_at}</td>
                <td>{action_buttons}</td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Panel Status Admin</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f5f7fa;
                padding: 30px;
            }}

            h1 {{
                color: #17345D;
            }}

            .top-bar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 18px;
            }}

            .refresh-btn {{
                background: #17345D;
                color: white;
                padding: 10px 16px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}

            .stats {{
                display: flex;
                gap: 12px;
                margin-bottom: 18px;
            }}

            .stat-card {{
                background: white;
                padding: 14px 18px;
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
                min-width: 140px;
            }}

            .stat-label {{
                font-size: 13px;
                color: #666;
            }}

            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #17345D;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}

            th, td {{
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}

            th {{
                background: #17345D;
                color: white;
            }}

            .pending {{
                color: #c77700;
                font-weight: bold;
            }}

            .approved {{
                color: green;
                font-weight: bold;
            }}

            button {{
                padding: 8px 12px;
                margin: 2px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                color: white;
            }}

            .btn3 {{
                background: #2F4E7A;
            }}

            .btn6 {{
                background: #6E9C63;
            }}

            .btn12 {{
                background: #C8A24F;
                color: black;
            }}

            .disabled {{
                color: #888;
            }}
        </style>
    </head>
    <body>

        <div class="top-bar">
            <h1>Panel Status License Requests</h1>
            <button class="refresh-btn" onclick="location.reload()">Refresh</button>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value">{total_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pending</div>
                <div class="stat-value">{pending_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Approved</div>
                <div class="stat-value">{approved_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Used Codes</div>
                <div class="stat-value">{used_count}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Used</th>
                    <th>Created At</th>
                    <th>Approved At</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

    </body>
    </html>
    """

    return HTMLResponse(content=html)


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
async def approve_access(password: str, email: str, duration_months: int, db: Session = Depends(get_db)):
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
        access_expires_at = now + timedelta(minutes=3)
        duration_label = "3 minutes test"
    elif duration_months == 6:
        access_expires_at = now + timedelta(days=180)
        duration_label = "6 months"
    elif duration_months == 12:
        access_expires_at = now + timedelta(days=365)
        duration_label = "1 year"
    else:
        raise HTTPException(status_code=400, detail="Only 3, 6, or 12 months allowed.")

    # 1. Send email first
    try:
       await send_user_code_email(email, code, duration_label)
    except Exception as e:
       print("Failed to send user code email:", e)
       return HTMLResponse(
        content=f"<h2>Email sending failed</h2><p>{e}</p><a href='/admin?password={password}'>Back</a>",
        status_code=500
       )

# 2. Only mark approved after email succeeds
    request_row.code = code
    request_row.request_status = "approved"
    request_row.code_expires_at = code_expires_at
    request_row.access_expires_at = access_expires_at
    request_row.approved_at = now

    db.commit()

    return RedirectResponse(url=f"/admin?password={password}", status_code=303)



@app.post("/admin/approve-web")
async def approve_access_web(
    password: str = Form(...),
    email: str = Form(...),
    duration_months: int = Form(...),
    db: Session = Depends(get_db)
):
    if password != ADMIN_PASSWORD:
        return HTMLResponse(content="<h2>Unauthorized</h2>", status_code=403)

    request_row = db.query(AccessRequest).filter(
        AccessRequest.email == email,
        AccessRequest.request_status == "pending"
    ).order_by(AccessRequest.created_at.desc()).first()

    if not request_row:
        return RedirectResponse(url=f"/admin?password={password}", status_code=303)

    code = generate_code()
    now = datetime.utcnow()
    code_expires_at = now + timedelta(minutes=30)

    if duration_months == 3:
        access_expires_at = now + timedelta(minutes=3)
        duration_label = "3 minutes test"
    elif duration_months == 6:
        access_expires_at = now + timedelta(days=180)
        duration_label = "6 months"
    elif duration_months == 12:
        access_expires_at = now + timedelta(days=365)
        duration_label = "1 year"
    else:
        return RedirectResponse(url=f"/admin?password={password}", status_code=303)

    # 1. Send email first
    try:
       await send_user_code_email(email, code, duration_label)
    except Exception as e:
       print("Failed to send user code email:", e)
       return HTMLResponse(
         content=f"<h2>Email sending failed</h2><p>{e}</p><a href='/admin?password={password}'>Back</a>",
         status_code=500
       )

# 2. Only mark approved after email succeeds
    request_row.code = code
    request_row.request_status = "approved"
    request_row.code_expires_at = code_expires_at
    request_row.access_expires_at = access_expires_at
    request_row.approved_at = now

    db.commit()

    return RedirectResponse(url=f"/admin?password={password}", status_code=303)


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