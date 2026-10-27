from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from app.database import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String, unique=True, nullable=False, index=True)
    event = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    def mark_processed(self, session):
        self.processed = True
        self.processed_at = datetime.utcnow()
        session.add(self)
        session.commit()
