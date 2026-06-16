from datetime import date, timedelta
from calendar import monthrange
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Bill, BillReport, BillFrequency, BillCategory
import anthropic
from config import settings

router = APIRouter(prefix="/bills", tags=["bills"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class BillCreate(BaseModel):
    name: str
    amount: float
    category: BillCategory = BillCategory.other
    frequency: BillFrequency = BillFrequency.monthly
    due_day: Optional[int] = None      # 1-31, for recurring
    due_date: Optional[date] = None    # for one-off
    notes: Optional[str] = None


class BillUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[BillCategory] = None
    frequency: Optional[BillFrequency] = None
    due_day: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_next_due(bill: Bill) -> Optional[date]:
    today = date.today()
    if bill.frequency == BillFrequency.one_off:
        return bill.due_date
    if not bill.due_day:
        return None
    day = min(bill.due_day, 28)
    candidate = today.replace(day=day)
    if candidate < today:
        # advance by the correct period
        if bill.frequency == BillFrequency.weekly:
            candidate = today + timedelta(weeks=1)
        elif bill.frequency == BillFrequency.monthly:
            m = today.month % 12 + 1
            y = today.year + (1 if today.month == 12 else 0)
            candidate = today.replace(year=y, month=m, day=day)
        elif bill.frequency == BillFrequency.quarterly:
            m = ((today.month - 1 + 3) % 12) + 1
            y = today.year + ((today.month - 1 + 3) // 12)
            candidate = today.replace(year=y, month=m, day=day)
        elif bill.frequency == BillFrequency.annual:
            candidate = today.replace(year=today.year + 1, day=day)
    return candidate


def _monthly_amount(bill: Bill) -> float:
    freq_multipliers = {
        BillFrequency.weekly:    52 / 12,
        BillFrequency.monthly:   1,
        BillFrequency.quarterly: 1 / 3,
        BillFrequency.annual:    1 / 12,
        BillFrequency.one_off:   0,
    }
    return bill.amount * freq_multipliers.get(bill.frequency, 1)


def _bill_to_dict(bill: Bill) -> dict:
    return {
        "id": bill.id,
        "name": bill.name,
        "amount": bill.amount,
        "category": bill.category,
        "frequency": bill.frequency,
        "due_day": bill.due_day,
        "due_date": bill.due_date.isoformat() if bill.due_date else None,
        "next_due": bill.next_due.isoformat() if bill.next_due else None,
        "is_active": bill.is_active,
        "notes": bill.notes,
        "monthly_equivalent": round(_monthly_amount(bill), 2),
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/")
def list_bills(db: Session = Depends(get_db)):
    bills = db.query(Bill).filter(Bill.is_active == True).order_by(Bill.next_due).all()
    return [_bill_to_dict(b) for b in bills]


@router.post("/")
def create_bill(data: BillCreate, db: Session = Depends(get_db)):
    bill = Bill(**data.model_dump())
    bill.next_due = _compute_next_due(bill)
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return _bill_to_dict(bill)


@router.patch("/{bill_id}")
def update_bill(bill_id: int, data: BillUpdate, db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(bill, field, val)
    bill.next_due = _compute_next_due(bill)
    db.commit()
    db.refresh(bill)
    return _bill_to_dict(bill)


@router.delete("/{bill_id}", status_code=204)
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    db.delete(bill)
    db.commit()


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    bills = db.query(Bill).filter(Bill.is_active == True).all()
    today = date.today()
    in_7_days = today + timedelta(days=7)
    in_30_days = today + timedelta(days=30)

    monthly_total = sum(_monthly_amount(b) for b in bills)
    quarterly_total = monthly_total * 3
    annual_total = monthly_total * 12

    by_category: dict[str, float] = {}
    for b in bills:
        cat = b.category or "other"
        by_category[cat] = by_category.get(cat, 0) + _monthly_amount(b)

    due_soon = []
    for b in bills:
        if b.next_due and b.next_due <= in_30_days:
            days_until = (b.next_due - today).days
            due_soon.append({
                **_bill_to_dict(b),
                "days_until_due": days_until,
                "overdue": days_until < 0,
                "urgent": 0 <= days_until <= 7,
            })
    due_soon.sort(key=lambda x: x["days_until_due"])

    # Monthly breakdown for chart (12 months)
    monthly_breakdown = []
    for i in range(12):
        m = (today.month - 1 + i) % 12 + 1
        y = today.year + ((today.month - 1 + i) // 12)
        label = date(y, m, 1).strftime("%b %Y")
        total = 0
        for b in bills:
            if b.frequency == BillFrequency.one_off:
                if b.due_date and b.due_date.year == y and b.due_date.month == m:
                    total += b.amount
            else:
                total += _monthly_amount(b)
        monthly_breakdown.append({"month": label, "total": round(total, 2)})

    return {
        "monthly_total": round(monthly_total, 2),
        "quarterly_total": round(quarterly_total, 2),
        "annual_total": round(annual_total, 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "due_soon": due_soon,
        "monthly_breakdown": monthly_breakdown,
        "total_bills": len(bills),
    }


# ── AI Report ────────────────────────────────────────────────────────────────

@router.post("/report")
def generate_report(db: Session = Depends(get_db)):
    bills = db.query(Bill).filter(Bill.is_active == True).all()
    if not bills:
        raise HTTPException(status_code=400, detail="No bills to analyse")

    monthly_total = sum(_monthly_amount(b) for b in bills)
    bill_lines = "\n".join(
        f"- {b.name}: £{b.amount:.2f} ({b.frequency}, category: {b.category})"
        for b in bills
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"""You are a business finance advisor for EASTEND Salon, a hair salon in East London.

Here are the salon's current bills:
{bill_lines}

Monthly total: £{monthly_total:.2f}
Quarterly total: £{monthly_total * 3:.2f}
Annual total: £{monthly_total * 12:.2f}

Write a concise cost-cutting report in markdown. Include:
1. **Overview** — brief summary of spend by category
2. **Quick Wins** — 3–5 specific actions to reduce costs immediately
3. **Medium-term savings** — 2–3 ideas that require more planning
4. **Benchmarks** — typical UK salon spend ratios (rent 10–15% of revenue, supplies 5–8%, etc.) and how EASTEND compares
5. **Priority Actions** — a ranked list of the most impactful changes

Be specific with £ estimates where possible. Keep it practical and actionable."""
        }]
    )
    content = msg.content[0].text

    report = BillReport(
        report_content=content,
        monthly_total=round(monthly_total, 2),
        quarterly_total=round(monthly_total * 3, 2),
        annual_total=round(monthly_total * 12, 2),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "generated_at": report.generated_at.isoformat(),
        "report_content": content,
        "monthly_total": report.monthly_total,
        "quarterly_total": report.quarterly_total,
        "annual_total": report.annual_total,
    }


@router.get("/report/latest")
def get_latest_report(db: Session = Depends(get_db)):
    report = db.query(BillReport).order_by(BillReport.generated_at.desc()).first()
    if not report:
        return None
    return {
        "id": report.id,
        "generated_at": report.generated_at.isoformat(),
        "report_content": report.report_content,
        "monthly_total": report.monthly_total,
        "quarterly_total": report.quarterly_total,
        "annual_total": report.annual_total,
    }
