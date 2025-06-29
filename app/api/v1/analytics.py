from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from app.db.database import get_db
from app.core.security import get_current_active_user, get_current_superuser
from app.models.user import User
from app.services.cost_tracker import cost_tracker
from app.services.master_chain_orchestrator import orchestrator
from app.schemas import BaseSchema

router = APIRouter()

class AnalyticsResponse(BaseSchema):
    period: Dict[str, str]
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    average_processing_time: float
    total_cost: float
    popular_workflows: List[Dict[str, Any]]
    model_performance: Dict[str, Any]

class CostAnalyticsResponse(BaseSchema):
    user_id: str
    period: Dict[str, str]
    total_cost: float
    service_breakdown: Dict[str, float]
    currency: str

@router.get("/user/processing", response_model=AnalyticsResponse)
async def get_user_processing_analytics(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's processing analytics for the specified period"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # In a real implementation, this would query the database
    # For now, we'll simulate analytics data
    
    import random
    
    total_jobs = random.randint(10, 100)
    successful_jobs = int(total_jobs * random.uniform(0.8, 0.95))
    failed_jobs = total_jobs - successful_jobs
    
    return AnalyticsResponse(
        period={
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        total_jobs=total_jobs,
        successful_jobs=successful_jobs,
        failed_jobs=failed_jobs,
        average_processing_time=round(random.uniform(60, 300), 2),
        total_cost=round(random.uniform(5, 50), 2),
        popular_workflows=[
            {"name": "standard_mastering", "usage_count": random.randint(5, 20)},
            {"name": "creative_enhancement", "usage_count": random.randint(3, 15)},
            {"name": "vocal_enhancement", "usage_count": random.randint(2, 10)}
        ],
        model_performance={
            "musicgen": {"success_rate": 0.95, "avg_time": 45.2},
            "stable_audio": {"success_rate": 0.92, "avg_time": 38.7},
            "aces": {"success_rate": 0.98, "avg_time": 25.1}
        }
    )

@router.get("/user/costs", response_model=CostAnalyticsResponse)
async def get_user_cost_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's cost analytics for the specified period"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    cost_data = await cost_tracker.get_user_costs(
        str(current_user.id), 
        start_date, 
        end_date
    )
    
    return CostAnalyticsResponse(**cost_data)

@router.get("/system/overview")
async def get_system_overview(
    current_user: User = Depends(get_current_superuser)
):
    """Get system-wide analytics overview (admin only)"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    system_costs = await cost_tracker.get_system_costs(start_date, end_date)
    
    # Add additional system metrics
    import random
    
    system_overview = {
        **system_costs,
        "active_users": random.randint(100, 1000),
        "total_processing_time": round(random.uniform(1000, 10000), 2),
        "system_health": {
            "api_uptime": 99.9,
            "model_availability": 95.2,
            "average_response_time": 2.3
        },
        "resource_utilization": {
            "cpu_usage": random.randint(40, 80),
            "memory_usage": random.randint(50, 85),
            "gpu_usage": random.randint(60, 90)
        }
    }
    
    return system_overview

@router.get("/models/performance")
async def get_model_performance_analytics(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_superuser)
):
    """Get detailed model performance analytics (admin only)"""
    
    # Simulate model performance data
    import random
    
    models = [
        "musicgen", "stable_audio", "google_musiclm", "audiocraft", 
        "jukebox", "melody_rnn", "music_vae", "aces_audio",
        "tepand_diff_rhythm", "suni_ai", "beethoven_ai", "mureka_ai"
    ]
    
    performance_data = {}
    
    for model in models:
        performance_data[model] = {
            "total_requests": random.randint(50, 500),
            "successful_requests": random.randint(45, 475),
            "failed_requests": random.randint(5, 25),
            "average_response_time": round(random.uniform(10, 120), 2),
            "p95_response_time": round(random.uniform(50, 200), 2),
            "error_rate": round(random.uniform(0.01, 0.15), 3),
            "cost_per_request": round(random.uniform(0.001, 0.1), 4),
            "uptime_percentage": round(random.uniform(95, 99.9), 2),
            "quality_score": round(random.uniform(0.8, 0.95), 2)
        }
    
    return {
        "period_days": days,
        "model_performance": performance_data,
        "summary": {
            "total_requests": sum(data["total_requests"] for data in performance_data.values()),
            "overall_success_rate": round(
                sum(data["successful_requests"] for data in performance_data.values()) /
                sum(data["total_requests"] for data in performance_data.values()), 3
            ),
            "average_response_time": round(
                sum(data["average_response_time"] for data in performance_data.values()) /
                len(performance_data), 2
            )
        }
    }

@router.get("/workflows/popularity")
async def get_workflow_popularity(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user)
):
    """Get workflow popularity analytics"""
    
    # Simulate workflow popularity data
    import random
    
    workflows = [
        "standard_mastering", "creative_enhancement", "generation_from_scratch",
        "vocal_enhancement", "auto_workflow", "custom_workflow"
    ]
    
    popularity_data = []
    
    for workflow in workflows:
        usage_count = random.randint(10, 200)
        popularity_data.append({
            "workflow_name": workflow,
            "usage_count": usage_count,
            "success_rate": round(random.uniform(0.85, 0.98), 3),
            "average_processing_time": round(random.uniform(60, 300), 2),
            "user_satisfaction": round(random.uniform(4.0, 4.8), 1),
            "cost_efficiency": round(random.uniform(0.7, 0.95), 2)
        })
    
    # Sort by usage count
    popularity_data.sort(key=lambda x: x["usage_count"], reverse=True)
    
    return {
        "period_days": days,
        "workflow_analytics": popularity_data,
        "trends": {
            "fastest_growing": popularity_data[0]["workflow_name"],
            "most_efficient": max(popularity_data, key=lambda x: x["cost_efficiency"])["workflow_name"],
            "highest_satisfaction": max(popularity_data, key=lambda x: x["user_satisfaction"])["workflow_name"]
        }
    }

@router.get("/real-time/metrics")
async def get_real_time_metrics(
    current_user: User = Depends(get_current_superuser)
):
    """Get real-time system metrics (admin only)"""
    
    # Get current active jobs
    active_jobs = len([job for job in orchestrator.active_jobs.values() 
                      if job.status.value in ["pending", "analyzing", "processing"]])
    
    # Simulate real-time metrics
    import random
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": active_jobs,
        "queue_length": random.randint(0, 20),
        "processing_capacity": {
            "total_slots": 50,
            "used_slots": active_jobs,
            "available_slots": 50 - active_jobs
        },
        "system_load": {
            "cpu_percent": random.randint(30, 80),
            "memory_percent": random.randint(40, 85),
            "gpu_percent": random.randint(50, 90)
        },
        "model_status": {
            "online": random.randint(10, 12),
            "offline": random.randint(0, 2),
            "degraded": random.randint(0, 1)
        },
        "recent_errors": random.randint(0, 5),
        "requests_per_minute": random.randint(20, 100)
    }