# models.py
from sqlalchemy import Column, String, LargeBinary, DateTime
from datetime import datetime
from .database import Base


class TaskResult(Base):
    """ タスクの実行結果を保存するテーブル
    """
    __tablename__ = "task_results"

    task_id = Column(String, primary_key=True, index=True)
    user_id = Column(String)
    trace_back = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow())
    modified_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=datetime.utcnow())
    result = Column(LargeBinary)
