from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.models.today_plan import TodayPlanItem
from app.models.subject import Subject
from app.models.weekly_schedule import WeeklySchedule
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def today_plan_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    today = date.today()
    items = db.query(TodayPlanItem).filter(
        TodayPlanItem.user_id == user.id,
        TodayPlanItem.study_mode == user.study_mode,
        TodayPlanItem.date == today,
    ).order_by(TodayPlanItem.completed.asc(), TodayPlanItem.id.asc()).all()

    subjects = db.query(Subject).filter(Subject.user_id == user.id, Subject.study_mode == user.study_mode).all()

    completed_count = sum(1 for item in items if item.completed)
    total_count = len(items)

    return request.app.state.templates.TemplateResponse(
        request,
        "today_plan.html",
        context={
            "items": items,
            "subjects": subjects,
            "completed_count": completed_count,
            "total_count": total_count,
            "study_mode": user.study_mode,
        },
    )


@router.post("/generate-from-schedule")
async def generate_from_schedule(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    today = date.today()
    day_of_week = today.weekday()

    existing = db.query(TodayPlanItem).filter(
        TodayPlanItem.user_id == user.id,
        TodayPlanItem.study_mode == user.study_mode,
        TodayPlanItem.date == today,
    ).count()
    if existing > 0:
        return RedirectResponse(url="/today-plan", status_code=303)

    schedule_entries = db.query(WeeklySchedule).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.day_of_week == day_of_week,
    ).order_by(WeeklySchedule.order).all()

    created = 0
    for entry in schedule_entries:
        subject = db.query(Subject).filter(Subject.id == entry.subject_id).first()
        if subject:
            item = TodayPlanItem(
                title=subject.name,
                subject_id=subject.id,
                estimated_minutes=45,
                priority="media",
                item_type="estudo",
                date=today,
                user_id=user.id,
                study_mode=user.study_mode,
            )
            db.add(item)
            created += 1

    if created > 0:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return RedirectResponse(url="/today-plan", status_code=303)


@router.post("/create")
async def create_item(
    request: Request,
    title: str = Form(...),
    subject_id: int = Form(0),
    estimated_minutes: int = Form(30),
    time_optional: str = Form(""),
    priority: str = Form("media"),
    item_type: str = Form("estudo"),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if priority not in ("baixa", "media", "alta"):
        priority = "media"
    if item_type not in ("estudo", "revisao", "simulado", "projeto", "concurso"):
        item_type = "estudo"

    item = TodayPlanItem(
        title=title.strip(),
        subject_id=subject_id if subject_id else None,
        estimated_minutes=estimated_minutes,
        time_optional=time_optional.strip() if time_optional.strip() else None,
        priority=priority,
        item_type=item_type,
        date=date.today(),
        user_id=user.id,
        study_mode=user.study_mode,
    )
    db.add(item)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/today-plan", status_code=303)


@router.post("/{item_id}/toggle")
async def toggle_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)

    item = db.query(TodayPlanItem).filter(
        TodayPlanItem.id == item_id, TodayPlanItem.user_id == user.id, TodayPlanItem.study_mode == user.study_mode
    ).first()
    if not item:
        return JSONResponse(content={"error": "Not found"}, status_code=404)

    item.completed = not item.completed
    try:
        db.commit()
    except Exception:
        db.rollback()

    return JSONResponse(content={
        "completed": item.completed,
        "item_id": item.id,
    })


@router.post("/{item_id}/update")
async def update_item(
    item_id: int,
    request: Request,
    title: str = Form(...),
    subject_id: int = Form(0),
    estimated_minutes: int = Form(30),
    time_optional: str = Form(""),
    priority: str = Form("media"),
    item_type: str = Form("estudo"),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    item = db.query(TodayPlanItem).filter(
        TodayPlanItem.id == item_id, TodayPlanItem.user_id == user.id, TodayPlanItem.study_mode == user.study_mode
    ).first()
    if not item:
        return RedirectResponse(url="/today-plan", status_code=303)

    if priority not in ("baixa", "media", "alta"):
        priority = "media"
    if item_type not in ("estudo", "revisao", "simulado", "projeto", "concurso"):
        item_type = "estudo"

    item.title = title.strip()
    item.subject_id = subject_id if subject_id else None
    item.estimated_minutes = estimated_minutes
    item.time_optional = time_optional.strip() if time_optional.strip() else None
    item.priority = priority
    item.item_type = item_type
    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/today-plan", status_code=303)


@router.post("/{item_id}/delete")
async def delete_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    item = db.query(TodayPlanItem).filter(
        TodayPlanItem.id == item_id, TodayPlanItem.user_id == user.id, TodayPlanItem.study_mode == user.study_mode
    ).first()
    if item:
        db.delete(item)
        try:
            db.commit()
        except Exception:
            db.rollback()
    return RedirectResponse(url="/today-plan", status_code=303)
