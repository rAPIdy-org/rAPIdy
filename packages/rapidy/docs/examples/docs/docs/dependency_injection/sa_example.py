from typing import AsyncIterable

from pydantic_settings import SettingsConfigDict, BaseSettings
from rapidy import Rapidy, run_app
from rapidy.depends import FromDI, Provider, Scope, provide, from_context
from rapidy.web_response import Response
from sqlalchemy import make_url, DateTime, MetaData, Table, delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, AsyncEngine, create_async_engine
from rapidy.http import controller, get, post, PathParam, Body, put, delete
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import expression
from sqlalchemy.sql.schema import ColumnCollectionConstraint, Column


# --- App config ---
class PoolConfig(BaseModel):
    recycle_sec: int = 3600
    max_size: int = 10
    max_overflow_size: int = 10


class DBConfig(BaseModel):
    echo: bool = False
    pool: PoolConfig = PoolConfig()

    timeout: int = 30

    db_name: str
    user: str
    password: str
    host: str
    port: int = 5432

    @property
    def dsn(self) -> str:
        return f'postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}'


class AppConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080

    db: DBConfig

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )


# --- DB models ---

def _col_names_convertor(constraint: ColumnCollectionConstraint, table: Table) -> str:
    return "_".join([column.name for column in constraint.columns.values()])


convention: dict[str, str | Callable[[ColumnCollectionConstraint, Table], str]] = {
    "all_column_names": _col_names_convertor,
    "ix": "ix__%(table_name)s__%(all_column_names)s",
    "uq": "uq__%(table_name)s__%(all_column_names)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}


class UtcNow(expression.FunctionElement[Any]):
    type = DateTime()
    inherit_cache = True


@compiles(UtcNow, "postgresql")
def pg_utcnow(element: Any, compiler: Any, **kw: Any) -> str:
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


class BaseDBModel(DeclarativeBase):
    __tablename__: str

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    create_date: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=UtcNow(),
    )
    update_date: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=UtcNow(),
        onupdate=UtcNow(),
    )

    metadata = MetaData(
        schema="data",
        naming_convention=convention,
    )


class Article(BaseDBModel):
    __tablename__ = "article"

    title: Mapped[str]
    text: Mapped[str]


# --- DI Providers ---

class ConfigProvider(Provider):
    scope = Scope.APP
    config = from_context(provides=AppConfig)

    @provide
    def get_db_config(self, config: AppConfig) -> DBConfig:
        return config.db


class DBProvider(Provider):
    scope = Scope.APP

    @provide
    async def get_engine(self, db_config: DBConfig) -> AsyncIterable[AsyncEngine]:
        engine = create_async_engine(
            url=make_url(db_config.dsn),
            echo=db_config.echo,
            pool_size=db_config.pool.max_size,
            pool_recycle=db_config.pool.recycle_sec,
            max_overflow=db_config.pool.max_overflow_size,
            execution_options={
                "asyncpg_timeout": db_config.timeout,
            },
        )
        try:
            yield engine
        finally:
            await engine.dispose(True)

    @provide
    def get_pool(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(bind=engine, autoflush=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(self, pool: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        async with pool() as session, session.begin():
            exc = yield session
            if exc is not None:
                await session.rollback()


# --- Api ---

class ArticleCreate(BaseModel):
    title: str
    text: str


class ArticleUpdate(BaseModel):
    title: str | None = None
    text: str | None = None


class ArticleResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    text: str
    create_date: datetime
    update_date: datetime


@controller("/article")
class ArticleController:

    @get("/{article_id}")
    async def get_one(
        self,
        session: FromDI[AsyncSession],
        response: Response,
        article_id: UUID = PathParam(),
    ) -> ArticleResult | None:
        article = await session.get(Article, article_id)
        if article is None:
            response.set_status(404)
            return None

        return ArticleResult.model_validate(article)

    @get(response_type=list[ArticleResult])
    async def get_all(self, session: FromDI[AsyncSession]) -> list[ArticleResult]:
        result = await session.execute(select(Article))
        return [ArticleResult.model_validate(row) for row in result.scalars().all()]

    @post()
    async def create(self, session: FromDI[AsyncSession], data: ArticleCreate = Body()) -> ArticleResult:
        article = Article(**data.model_dump())
        session.add(article)

        await session.flush()
        await session.refresh(article)
        return ArticleResult.model_validate(article)

    @put("/{article_id}")
    async def put(
        self,
        session: FromDI[AsyncSession],
        article_id: UUID = PathParam(),
        data: ArticleUpdate = Body(),
    ) -> ArticleResult | None:
        stmt = (
            update(Article)
            .where(Article.id == article_id)
            .values(**data.model_dump(exclude_unset=True))
            .returning(Article)
        )
        result = await session.execute(stmt)
        updated_article = result.scalar_one_or_none()
        return ArticleResult.model_validate(updated_article) if updated_article else None

    @delete("/{article_id}")
    async def delete(
        self,
        session: FromDI[AsyncSession],
        article_id: UUID = PathParam(),
    ) -> None:
        await session.execute(delete(Article).where(Article.id == article_id))


def create_app() -> Rapidy:
    return Rapidy(
        http_route_handlers=[ArticleController],
        di_providers=[
            ConfigProvider(),
            DBProvider(),
        ],
        di_context={
            AppConfig: AppConfig(),
        },
    )

if __name__ == '__main__':
    app = create_app()
    run_app(app)
