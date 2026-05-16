"""Article entity — information source (公众号, news, FDA doc, paper, etc.).

NOT bilingual per ADR-0006 (article content is single-language; carries
`language` field instead of `_zh` siblings).
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifier (URL hash — design doc §5.1)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    title: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str | None] = mapped_column(String(64))  # wechat_gongzhonghao, news, paper, sec_filing, ...
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    publish_date: Mapped[date | None] = mapped_column(Date, index=True)
    credibility_tier: Mapped[str | None] = mapped_column(String(32))

    # Optional cached content (for offline claim extraction)
    cached_content: Mapped[str | None] = mapped_column(Text)
    cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
