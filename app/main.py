from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json
from . import models, database

# Crear tablas al iniciar
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Nexus Integration Hub")
templates = Jinja2Templates(directory="app/templates")

# --- Administrador de WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Endpoints ---

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    db.execute("SELECT 1")
    return {"status": "ok"}

@app.get("/api/history")
def get_history(db: Session = Depends(database.get_db)):
    # Buscamos los últimos 10 eventos registrados
    events = db.query(models.WebhookEvent).order_by(models.WebhookEvent.received_at.desc()).limit(10).all()
    return [
        {
            "id": e.id,
            "method": e.method,
            "payload": e.payload,
            "time": e.received_at.strftime("%H:%M:%S")
        } for e in events
    ]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(database.get_db)):
    # 1. Capturar JSON
    payload = await request.json()
    
    # 2. Guardar en la Base de Datos
    new_event = models.WebhookEvent(
        source_ip=request.client.host,
        method=request.method,
        headers=dict(request.headers),
        payload=payload
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # 3. Avisar a la pantalla por WebSocket
    event_data = {
        "id": new_event.id,
        "method": new_event.method,
        "payload": payload,
        "time": new_event.received_at.strftime("%H:%M:%S")
    }
    await manager.broadcast(json.dumps(event_data))
    
    return {"status": "captured", "id": new_event.id}