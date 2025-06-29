from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
import uuid

from app.db.database import get_async_db # Changed import
from app.crud import api_key as crud_api_key
from app.schemas import APIKeyCreate, APIKeyResponse, APIKeyDetail, APIKeyCreateResponse
from app.api.deps import get_current_active_user # Changed import
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    api_key_in: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """
    Create new API key
    """
    # Get client IP
    client_ip = request.client.host
    
    # Create API key
    api_key_obj, raw_key = await crud_api_key.create_with_user( # Added await
        db, 
        obj_in=api_key_in, 
        user_id=current_user.id,
        created_from_ip=client_ip
    )
    
    return APIKeyCreateResponse(
        api_key=api_key_obj,
        key=raw_key
    )

@router.get("/", response_model=List[APIKeyDetail])
async def read_api_keys( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve user's API keys
    """
    api_keys = await crud_api_key.get_by_user(db, user_id=current_user.id) # Added await
    
    # Add computed properties
    result = []
    for key in api_keys:
        key_detail = APIKeyDetail.from_orm(key)
        key_detail.masked_key = key.masked_key
        key_detail.days_until_expiry = key.days_until_expiry
        key_detail.is_expiring_soon = key.is_expiring_soon
        result.append(key_detail)
    
    return result

@router.get("/{key_id}", response_model=APIKeyDetail)
async def read_api_key( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get API key by ID
    """
    api_key = await crud_api_key.get(db, id=key_id) # Added await
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Add computed properties
    # Assuming APIKeyDetail.from_orm is compatible with async or the ORM object is fully loaded
    key_detail = APIKeyDetail.from_orm(api_key)
    key_detail.masked_key = api_key.masked_key
    key_detail.days_until_expiry = api_key.days_until_expiry
    key_detail.is_expiring_soon = api_key.is_expiring_soon
    
    return key_detail

@router.delete("/{key_id}")
async def delete_api_key( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete API key (soft delete by deactivating)
    """
    api_key = await crud_api_key.get(db, id=key_id) # Added await
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Deactivate instead of delete
    await crud_api_key.deactivate(db, key_id=key_id) # Added await
    
    return {"message": "API key deleted successfully"}

@router.post("/{key_id}/activate")
async def activate_api_key( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Activate API key
    """
    api_key = await crud_api_key.get(db, id=key_id) # Added await
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await crud_api_key.activate(db, key_id=key_id) # Added await
    
    return {"message": "API key activated successfully"}

@router.post("/{key_id}/deactivate")
async def deactivate_api_key( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Deactivate API key
    """
    api_key = await crud_api_key.get(db, id=key_id) # Added await
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await crud_api_key.deactivate(db, key_id=key_id) # Added await
    
    return {"message": "API key deactivated successfully"}

@router.post("/{key_id}/extend")
async def extend_api_key( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    key_id: uuid.UUID,
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Extend API key expiry
    """
    api_key = await crud_api_key.get(db, id=key_id) # Added await
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if api_key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await crud_api_key.extend_expiry(db, key_id=key_id, days=days) # Added await
    
    return {"message": f"API key extended by {days} days"}