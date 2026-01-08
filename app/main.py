from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import httpx
import secrets
import os
from pathlib import Path
from typing import Optional
from . import models, database

# Crear tablas al iniciar
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Nexus Integration Hub")
templates = Jinja2Templates(directory="app/templates")

# Token de máquina - se guarda en un archivo
TOKEN_FILE = Path("/code/data/.nexus_token")

def get_machine_token():
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None

def set_machine_token(token: str):
    TOKEN_FILE.write_text(token)
    return token

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

@app.get("/api/auth/status")
async def auth_status():
    token = get_machine_token()
    return {
        "configured": token is not None,
        "token": token if token else None
    }

@app.post("/api/auth/setup")
async def setup_auth():
    existing_token = get_machine_token()
    if existing_token:
        raise HTTPException(status_code=400, detail="Token already configured")
    
    new_token = secrets.token_urlsafe(32)
    set_machine_token(new_token)
    
    return {
        "status": "configured",
        "token": new_token,
        "message": "Guarda este token de forma segura. Lo necesitarás para acceder."
    }

@app.post("/api/auth/verify")
async def verify_token_endpoint(request: Request):
    data = await request.json()
    provided_token = data.get("token")
    
    if not provided_token:
        raise HTTPException(status_code=400, detail="Token required")
    
    machine_token = get_machine_token()
    
    if not machine_token:
        raise HTTPException(status_code=400, detail="System not configured")
    
    if provided_token == machine_token:
        return {"status": "authenticated", "valid": True}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth/reset")
async def reset_token(request: Request):
    data = await request.json()
    current_token = data.get("current_token")
    
    machine_token = get_machine_token()
    
    if not machine_token or current_token != machine_token:
        raise HTTPException(status_code=401, detail="Invalid current token")
    
    new_token = secrets.token_urlsafe(32)
    set_machine_token(new_token)
    
    return {
        "status": "reset",
        "token": new_token,
        "message": "Token regenerado exitosamente"
    }

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/setup")
async def setup_page(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})

@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/api/history")
def get_history(db: Session = Depends(database.get_db)):
    events = db.query(models.WebhookEvent).filter(
        models.WebhookEvent.is_deleted == False
    ).order_by(models.WebhookEvent.received_at.desc()).limit(10).all()
    return [
        {
            "id": e.id,
            "method": e.method,
            "payload": e.payload,
            "time": e.received_at.strftime("%H:%M:%S"),
            "is_favorite": e.is_favorite,
            "is_deleted": e.is_deleted
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

@app.post("/api/events/{event_id}/replay")
async def replay_event(event_id: int, target_url: str, db: Session = Depends(database.get_db)):
    event = db.query(models.WebhookEvent).filter(models.WebhookEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                json=event.payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            return {
                "status": "replayed",
                "event_id": event_id,
                "target_url": target_url,
                "response_status": response.status_code,
                "response_body": response.text
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")

@app.patch("/api/events/{event_id}/favorite")
def toggle_favorite(event_id: int, db: Session = Depends(database.get_db)):
    event = db.query(models.WebhookEvent).filter(models.WebhookEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.is_favorite = not event.is_favorite
    db.commit()
    db.refresh(event)
    
    return {
        "status": "updated",
        "event_id": event_id,
        "is_favorite": event.is_favorite
    }

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(database.get_db)):
    event = db.query(models.WebhookEvent).filter(models.WebhookEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.is_deleted = True
    db.commit()
    
    return {
        "status": "deleted",
        "event_id": event_id
    }

@app.post("/api/echo")
async def echo_endpoint(request: Request):
    """Endpoint de prueba que devuelve el payload recibido con metadata adicional"""
    payload = await request.json()
    
    return {
        "status": "success",
        "message": "¡Payload recibido correctamente!",
        "received_data": payload,
        "metadata": {
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "content_type": request.headers.get("content-type", "unknown"),
            "timestamp": "2026-01-08T14:22:00Z"
        },
        "echo": f"Recibí {len(str(payload))} caracteres de datos"
    }

@app.post("/api/send")
@app.get("/api/send")
async def send_manual_request(request: Request, db: Session = Depends(database.get_db)):
    if request.method == "POST":
        data = await request.json()
    else:
        data = dict(request.query_params)
    
    target_url = data.get("url")
    payload = data.get("payload", {})
    method = data.get("method", "POST")
    
    if not target_url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    resolved_url = target_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
    
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    resolved_url,
                    timeout=10.0
                )
                try:
                    response_json = response.json()
                    response_data = response_json
                except:
                    response_data = {"response": response.text}
            else:
                response = await client.post(
                    resolved_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                try:
                    response_json = response.json()
                    response_data = {"sent": payload, "response": response_json}
                except:
                    response_data = {"sent": payload, "response": response.text}
            
            new_event = models.WebhookEvent(
                source_ip="manual_send",
                method=method,
                headers={"target_url": target_url, "resolved_url": resolved_url},
                payload=response_data
            )
            db.add(new_event)
            db.commit()
            db.refresh(new_event)
            
            return {
                "status": "sent",
                "method": method,
                "target_url": target_url,
                "resolved_url": resolved_url,
                "response_status": response.status_code,
                "response_body": response.text,
                "event_id": new_event.id
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send failed: {str(e)}")