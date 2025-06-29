from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, timedelta
from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        
        **Parameters**
        * `model`: A SQLAlchemy model class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Get a single record by ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = None,
        sort_order: str = "desc"
    ) -> List[ModelType]:
        """Get multiple records with pagination and sorting"""
        query = db.query(self.model)
        
        # Apply sorting if specified
        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
        else:
            # Default sort by created_at if available
            if hasattr(self.model, 'created_at'):
                query = query.order_by(desc(self.model.created_at))
        
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record"""
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # Update timestamp if available
        if hasattr(db_obj, 'updated_at'):
            db_obj.updated_at = datetime.utcnow()
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType:
        """Delete a record by ID"""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def soft_delete(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Soft delete a record (if model supports it)"""
        obj = db.query(self.model).get(id)
        if obj and hasattr(obj, 'is_deleted'):
            obj.is_deleted = True
            if hasattr(obj, 'updated_at'):
                obj.updated_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def restore(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Restore a soft-deleted record"""
        obj = db.query(self.model).get(id)
        if obj and hasattr(obj, 'is_deleted'):
            obj.is_deleted = False
            if hasattr(obj, 'updated_at'):
                obj.updated_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def count(self, db: Session, *, filters: Dict[str, Any] = None) -> int:
        """Count total records with optional filters"""
        query = db.query(self.model)
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        return query.count()

    def exists(self, db: Session, *, id: Any) -> bool:
        """Check if record exists by ID"""
        return db.query(self.model).filter(self.model.id == id).first() is not None

    def get_by_field(self, db: Session, *, field: str, value: Any) -> Optional[ModelType]:
        """Get record by any field"""
        if hasattr(self.model, field):
            return db.query(self.model).filter(getattr(self.model, field) == value).first()
        return None

    def get_multi_by_field(
        self,
        db: Session,
        *,
        field: str,
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records by field value"""
        if hasattr(self.model, field):
            return db.query(self.model).filter(
                getattr(self.model, field) == value
            ).offset(skip).limit(limit).all()
        return []

    def bulk_create(self, db: Session, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records"""
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        db.commit()
        for db_obj in db_objs:
            db.refresh(db_obj)
        return db_objs

    def bulk_update(
        self,
        db: Session,
        *,
        ids: List[Any],
        update_data: Dict[str, Any]
    ) -> int:
        """Bulk update multiple records"""
        if hasattr(self.model, 'updated_at'):
            update_data['updated_at'] = datetime.utcnow()
        
        updated_count = db.query(self.model).filter(
            self.model.id.in_(ids)
        ).update(update_data, synchronize_session=False)
        db.commit()
        return updated_count

    def bulk_delete(self, db: Session, *, ids: List[Any]) -> int:
        """Bulk delete multiple records"""
        deleted_count = db.query(self.model).filter(
            self.model.id.in_(ids)
        ).delete(synchronize_session=False)
        db.commit()
        return deleted_count

    def search(
        self,
        db: Session,
        *,
        query: str,
        fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Search records across multiple fields"""
        search_conditions = []
        for field in fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                search_conditions.append(field_attr.ilike(f"%{query}%"))
        
        if search_conditions:
            return db.query(self.model).filter(
                or_(*search_conditions)
            ).offset(skip).limit(limit).all()
        return []

    def filter_by_date_range(
        self,
        db: Session,
        *,
        date_field: str,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Filter records by date range"""
        if hasattr(self.model, date_field):
            date_attr = getattr(self.model, date_field)
            return db.query(self.model).filter(
                and_(date_attr >= start_date, date_attr <= end_date)
            ).offset(skip).limit(limit).all()
        return []

    def get_recent(
        self,
        db: Session,
        *,
        days: int = 7,
        limit: int = 100
    ) -> List[ModelType]:
        """Get recent records from the last N days"""
        if hasattr(self.model, 'created_at'):
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return db.query(self.model).filter(
                self.model.created_at >= cutoff_date
            ).order_by(desc(self.model.created_at)).limit(limit).all()
        return []

    def get_paginated(
        self,
        db: Session,
        *,
        page: int = 1,
        size: int = 20,
        sort_by: str = None,
        sort_order: str = "desc",
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get paginated results with metadata"""
        query = db.query(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        
        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
        
        # Get total count
        total = query.count()
        
        # Calculate pagination
        skip = (page - 1) * size
        items = query.offset(skip).limit(size).all()
        pages = (total + size - 1) // size  # Ceiling division
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }