from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from ...database import models
from ...database.session import get_db
from ... import schemas

router = APIRouter()

@router.get("/", response_model=schemas.OpportunityListResponse)
def list_opportunities(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return"),
    status: str = Query(None, description="Filter by opportunity status (e.g., 'pending_review')")
):
    """
    Retrieve a list of detected opportunities.

    Supports pagination and filtering by status.
    """
    query = db.query(models.Opportunity)

    if status:
        query = query.filter(models.Opportunity.status == status)

    total_count = query.count()

    opportunities = query.order_by(models.Opportunity.detected_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total_count,
        "opportunities": opportunities
    }


@router.get("/{opportunity_id}", response_model=schemas.OpportunitySchema)
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve the details of a single opportunity by its ID.
    """
    opportunity = db.query(models.Opportunity).filter(models.Opportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return opportunity


@router.patch("/{opportunity_id}/status")
def update_opportunity_status(
    opportunity_id: int,
    new_status: str = Query(..., description="The new status (e.g., 'approved', 'discarded')"),
    db: Session = Depends(get_db)
):
    """
    Update the status of an opportunity.

    This is used to mark an opportunity as reviewed, approved, or discarded.
    """
    opportunity = db.query(models.Opportunity).filter(models.Opportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Here you might want to validate the new_status against an Enum or a list
    allowed_statuses = ["pending_review", "approved", "discarded"]
    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"
        )

    opportunity.status = new_status
    db.commit()

    return {"message": f"Opportunity {opportunity_id} status updated to {new_status}"}