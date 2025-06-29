from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete, func, desc, asc, or_, and_
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

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Get a single record by ID"""
        statement = select(self.model).filter(self.model.id == id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> List[ModelType]:
        """Get multiple records with pagination and sorting"""
        statement = select(self.model)
        
        # Apply sorting if specified
        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "asc":
                statement = statement.order_by(asc(sort_column))
            else:
                statement = statement.order_by(desc(sort_column))
        else:
            # Default sort by created_at if available
            if hasattr(self.model, 'created_at'):
                statement = statement.order_by(desc(self.model.created_at))
        
        statement = statement.offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record"""
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True) # Pydantic v2 uses model_dump
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # Update timestamp if available
        if hasattr(db_obj, 'updated_at'):
            setattr(db_obj, 'updated_at', datetime.utcnow()) # Use setattr for consistency
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """Delete a record by ID"""
        obj = await self.get(db, id) # Use async get
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def soft_delete(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """Soft delete a record (if model supports it)"""
        obj = await self.get(db, id) # Use async get
        if obj and hasattr(obj, 'is_deleted'):
            setattr(obj, 'is_deleted', True)
            if hasattr(obj, 'updated_at'):
                setattr(obj, 'updated_at', datetime.utcnow())
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
        return obj

    async def restore(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """Restore a soft-deleted record"""
        # This might need a specific filter if soft-deleted items are usually excluded by default
        statement = select(self.model).filter(self.model.id == id)
        result = await db.execute(statement)
        obj = result.scalar_one_or_none()

        if obj and hasattr(obj, 'is_deleted'):
            setattr(obj, 'is_deleted', False)
            if hasattr(obj, 'updated_at'):
                setattr(obj, 'updated_at', datetime.utcnow())
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
        return obj

    async def count(self, db: AsyncSession, *, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total records with optional filters"""
        statement = select(func.count()).select_from(self.model)
        if filters:
            filter_conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    filter_conditions.append(getattr(self.model, field) == value)
            if filter_conditions:
                statement = statement.filter(and_(*filter_conditions))

        result = await db.execute(statement)
        return result.scalar_one()

    async def exists(self, db: AsyncSession, *, id: Any) -> bool:
        """Check if record exists by ID"""
        statement = select(self.model.id).filter(self.model.id == id)
        result = await db.execute(statement)
        return result.scalar_one_or_none() is not None

    async def get_by_field(self, db: AsyncSession, *, field: str, value: Any) -> Optional[ModelType]:
        """Get record by any field"""
        if hasattr(self.model, field):
            statement = select(self.model).filter(getattr(self.model, field) == value)
            result = await db.execute(statement)
            return result.scalar_one_or_none()
        return None

    async def get_multi_by_field(
        self,
        db: AsyncSession,
        *,
        field: str,
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records by field value"""
        if hasattr(self.model, field):
            statement = select(self.model).filter(
                getattr(self.model, field) == value
            ).offset(skip).limit(limit)
            result = await db.execute(statement)
            return result.scalars().all()
        return []

    async def bulk_create(self, db: AsyncSession, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records"""
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        await db.commit()
        # Refreshing multiple objects might need individual refresh calls or a different strategy
        # For now, let's assume individual refresh if needed, or skip if IDs are set by DB.
        # If primary keys are auto-incrementing and set by the DB, refresh is needed to get them.
        for db_obj in db_objs:
            await db.refresh(db_obj)
        return db_objs

    async def bulk_update(
        self,
        db: AsyncSession,
        *,
        ids: List[Any],
        update_data: Dict[str, Any]
    ) -> int:
        """Bulk update multiple records"""
        if hasattr(self.model, 'updated_at'):
            update_data['updated_at'] = datetime.utcnow()
        
        statement = (
            sqlalchemy_update(self.model)
            .where(self.model.id.in_(ids))
            .values(**update_data)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(statement)
        await db.commit()
        return result.rowcount

    async def bulk_delete(self, db: AsyncSession, *, ids: List[Any]) -> int:
        """Bulk delete multiple records"""
        statement = (
            sqlalchemy_delete(self.model)
            .where(self.model.id.in_(ids))
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(statement)
        await db.commit()
        return result.rowcount

    async def search(
        self,
        db: AsyncSession,
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
                # Ensure the column type supports ilike (e.g., String types)
                if hasattr(field_attr, 'ilike'):
                    search_conditions.append(field_attr.ilike(f"%{query}%"))
        
        if search_conditions:
            statement = select(self.model).filter(
                or_(*search_conditions)
            ).offset(skip).limit(limit)
            result = await db.execute(statement)
            return result.scalars().all()
        return []

    async def filter_by_date_range(
        self,
        db: AsyncSession,
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
            statement = select(self.model).filter(
                and_(date_attr >= start_date, date_attr <= end_date)
            ).offset(skip).limit(limit)
            result = await db.execute(statement)
            return result.scalars().all()
        return []

    async def get_recent(
        self,
        db: AsyncSession,
        *,
        days: int = 7,
        limit: int = 100
    ) -> List[ModelType]:
        """Get recent records from the last N days"""
        if hasattr(self.model, 'created_at'):
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            statement = select(self.model).filter(
                self.model.created_at >= cutoff_date
            ).order_by(desc(self.model.created_at)).limit(limit)
            result = await db.execute(statement)
            return result.scalars().all()
        return []

    async def get_paginated(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get paginated results with metadata"""
        
        # Count query
        count_statement = select(func.count()).select_from(self.model)
        if filters:
            filter_conditions_count = []
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    filter_conditions_count.append(getattr(self.model, field) == value)
            if filter_conditions_count:
                 count_statement = count_statement.filter(and_(*filter_conditions_count))
        
        total_result = await db.execute(count_statement)
        total = total_result.scalar_one()

        # Data query
        data_statement = select(self.model)
        if filters:
            filter_conditions_data = []
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                     filter_conditions_data.append(getattr(self.model, field) == value)
            if filter_conditions_data:
                data_statement = data_statement.filter(and_(*filter_conditions_data))

        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "asc":
                data_statement = data_statement.order_by(asc(sort_column))
            else:
                data_statement = data_statement.order_by(desc(sort_column))
        
        skip = (page - 1) * size
        data_statement = data_statement.offset(skip).limit(size)

        items_result = await db.execute(data_statement)
        items = items_result.scalars().all()

        pages = (total + size - 1) // size if size > 0 else 0
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }