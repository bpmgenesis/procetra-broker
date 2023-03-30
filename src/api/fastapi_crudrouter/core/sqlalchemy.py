from typing import Any, Callable, List, Type, Generator, Optional, Union

from fastapi import Depends, HTTPException, Response, Request
from sqlalchemy import desc
from . import CRUDGenerator, NOT_FOUND, _utils
from ._types import DEPENDENCIES, PAGINATION, PYDANTIC_SCHEMA as SCHEMA

try:
    from sqlalchemy.orm import Session
    from sqlalchemy.ext.declarative import DeclarativeMeta as Model
    from sqlalchemy.exc import IntegrityError
except ImportError:
    Model = None
    Session = None
    IntegrityError = None
    sqlalchemy_installed = False
else:
    sqlalchemy_installed = True
    Session = Callable[..., Generator[Session, Any, None]]

from api.utils import create_id
from api.routers import globals

CALLABLE = Callable[..., Model]
CALLABLE_LIST = Callable[..., List[Model]]


class SQLAlchemyCRUDRouter(CRUDGenerator[SCHEMA]):
    def __init__(
            self,
            schema: Type[SCHEMA],
            db_model: Model,
            db: "Session",
            create_schema: Optional[Type[SCHEMA]] = None,
            update_schema: Optional[Type[SCHEMA]] = None,
            prefix: Optional[str] = None,
            tags: Optional[List[str]] = None,
            paginate: Optional[int] = None,
            get_all_route: Union[bool, DEPENDENCIES] = True,
            get_one_route: Union[bool, DEPENDENCIES] = True,
            create_route: Union[bool, DEPENDENCIES] = True,
            update_route: Union[bool, DEPENDENCIES] = True,
            delete_one_route: Union[bool, DEPENDENCIES] = True,
            delete_all_route: Union[bool, DEPENDENCIES] = True,
            **kwargs: Any
    ) -> None:
        assert (
            sqlalchemy_installed
        ), "SQLAlchemy must be installed to use the SQLAlchemyCRUDRouter."

        self.db_model = db_model
        self.db_func = db
        self._pk: str = db_model.__table__.primary_key.columns.keys()[0]
        self._pk_type: type = str  # _utils.get_pk_type(schema, self._pk)

        super().__init__(
            schema=schema,
            create_schema=create_schema,
            update_schema=update_schema,
            prefix=prefix or db_model.__tablename__,
            tags=tags,
            paginate=paginate,
            get_all_route=get_all_route,
            get_one_route=get_one_route,
            create_route=create_route,
            update_route=update_route,
            delete_one_route=delete_one_route,
            delete_all_route=delete_all_route,
            **kwargs
        )

    def _get_all(self, *args: Any, **kwargs: Any) -> CALLABLE_LIST:
        def route(
                request: Request,
                response: Response,
                db: Session = Depends(self.db_func),
                pagination: PAGINATION = self.pagination,
               # session=Depends(globals.get_session),
        ) -> List[Model]:

            skip, limit = pagination.get("skip"), pagination.get("limit")

            sort_list: List[str] = []

            if limit is None:
                limit = 100
            if skip is None:
                skip = 0

            order: str = request.query_params.get("_order")
            sort: str = request.query_params.get("_sort")

            if sort is not None:
                sort_list = sort.split(',')

            query = db.query(self.db_model)

            # filter iterasyonu
            for attr, value in request.query_params.items():
                if hasattr(self.db_model, attr):
                    query = query.filter(getattr(self.db_model, attr).like("%%%s%%" % value))

            # sort iterasyonu
            for sort_field in sort_list:
                if hasattr(self.db_model, sort_field):
                    if order == 'DESC':
                        query = query.order_by(desc(getattr(self.db_model, sort_field)))
                    else:
                        query = query.order_by(getattr(self.db_model, sort_field))

            # query = query.filter(getattr(self.db_model, 'tenant_id').like("%%%s%%" % value))

            db_models: List[Model] = (
                query
                .order_by(getattr(self.db_model, self._pk))
                .limit(limit)
                .offset(skip)
                .all()
            )
            # response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
            response.headers["x-total-count"] = str(len(db_models))
            return db_models

        return route

    def _get_one(self, *args: Any, **kwargs: Any) -> CALLABLE:
        def route(
                item_id: self._pk_type, db: Session = Depends(self.db_func)  # type: ignore
        ) -> Model:
            model: Model = db.query(self.db_model).get(item_id)

            if model:
                return model
            else:
                raise NOT_FOUND from None

        return route

    def _create(self, *args: Any, **kwargs: Any) -> CALLABLE:
        def route(
                model: self.create_schema,  # type: ignore
                db: Session = Depends(self.db_func),
        ) -> Model:
            try:
                # 'id': create_id(),
                dict = {'id': create_id(), **model.dict()}
                db_model: Model = self.db_model(**dict)
                db.add(db_model)
                db.commit()
                db.refresh(db_model)
                return db_model
            except IntegrityError:
                db.rollback()
                raise HTTPException(422, "Key already exists") from None

        return route

    def _update(self, *args: Any, **kwargs: Any) -> CALLABLE:
        def route(
                item_id: self._pk_type,  # type: ignore
                model: self.update_schema,  # type: ignore
                db: Session = Depends(self.db_func),
        ) -> Model:
            try:
                db_model: Model = self._get_one()(item_id, db)

                for key, value in model.dict(exclude={self._pk}).items():
                    if hasattr(db_model, key):
                        setattr(db_model, key, value)

                db.commit()
                db.refresh(db_model)

                return db_model
            except IntegrityError as e:
                db.rollback()
                self._raise(e)

        return route

    def _delete_all(self, *args: Any, **kwargs: Any) -> CALLABLE_LIST:
        def route(db: Session = Depends(self.db_func)) -> List[Model]:
            db.query(self.db_model).delete()
            db.commit()

            return self._get_all()(db=db, pagination={"skip": 0, "limit": None})

        return route

    def _delete_one(self, *args: Any, **kwargs: Any) -> CALLABLE:
        def route(
                item_id: self._pk_type, db: Session = Depends(self.db_func)  # type: ignore
        ) -> Model:
            db_model: Model = self._get_one()(item_id, db)
            db.delete(db_model)
            db.commit()

            return db_model

        return route
