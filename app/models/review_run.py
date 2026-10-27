from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ReviewRun(Base):
    __tablename__ = "review_runs"
    id = Column(Integer, primary_key=True, index=True)
    webhook_delivery_id = Column(Integer, ForeignKey('webhook_deliveries.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default='pending')  # pending, completed, failed
    # Relationship to findings
    findings = relationship('Finding', back_populates='review_run', cascade='all, delete-orphan')

class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True, index=True)
    review_run_id = Column(Integer, ForeignKey('review_runs.id'), nullable=False)
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    severity = Column(String, nullable=False)  # e.g., low, medium, high, critical
    confidence = Column(String, nullable=False)  # e.g., low, medium, high
    description = Column(String, nullable=False)
    suggestion = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    review_run = relationship('ReviewRun', back_populates='findings')
