from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.analytics_engine import get_growth_summary, get_client_health_overview
from app.services.ai_helper import ai_helper

router = APIRouter()

@router.get("/growth-summary", status_code=status.HTTP_200_OK)
def read_growth_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retrieves the complete Business Growth summary: Business Health Score,
    Smart Insights, Growth Coach Priorities, Opportunities, and Risks.
    Future AI-ready explanations are automatically merged.
    """
    try:
        summary = get_growth_summary(db, user_id=current_user.id)
        # Enrich the rule-based metrics with the future AI coaching narrative (if keys present)
        enriched = ai_helper.enrich_growth_summary(summary)
        return enriched
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate growth summary metrics: {str(e)}"
        )

@router.get("/client-health", status_code=status.HTTP_200_OK)
def read_client_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Retrieves detailed client health scores and activity tracking logs for all user clients.
    """
    try:
        return get_client_health_overview(db, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve client health metrics: {str(e)}"
        )
