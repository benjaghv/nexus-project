from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from .database import Base

class WebhookEvent(Base):
    """
    Modelo para almacenar cualquier petición entrante.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    # IP de origen de quien envió el webhook
    source_ip = Column(String, index=True, nullable=True)
    # Método HTTP (POST, GET, PUT, etc.)
    method = Column(String, index=True)
    # Guardamos los headers y el cuerpo como JSON puro
    headers = Column(JSON)
    payload = Column(JSON)
    # Timestamp automático al momento de recibirlo
    received_at = Column(DateTime(timezone=True), server_default=func.now())