# 🔐 Guía de Autenticación Nexus Hub

## ¿Qué es el Sistema de Autenticación?

Nexus Hub ahora incluye un sistema de autenticación **Challenge-Response** que protege el acceso a los eventos guardados. Sin un token válido, no puedes ver el dashboard.

## Cómo Funciona

### 1️⃣ **Solicitar Challenge**
- Ingresas un valor aleatorio (ej: "mi-secreto-123")
- El servidor te devuelve:
  - El challenge que enviaste
  - Los primeros 16 caracteres del hash esperado

### 2️⃣ **Calcular el Hash**
Debes calcular: `SHA256(challenge + secret_key)`

**Secret Key actual:** `nexus_secret_key_2026`

**Ejemplo:**
```
Challenge: "mi-secreto-123"
Secret Key: "nexus_secret_key_2026"
Concatenar: "mi-secreto-123nexus_secret_key_2026"
SHA256: calcular el hash
Tomar primeros 16 caracteres
```

### 3️⃣ **Verificar y Obtener Token**
- Envías el hash calculado
- Si es correcto, recibes un token de acceso válido por 24 horas
- El token se guarda automáticamente en tu navegador

## Cómo Usar

### Opción A: Usar la Interfaz Web

1. Ve a `http://localhost:8000`
2. Serás redirigido a `/login`
3. Ingresa un valor en "Solicitar Challenge"
4. Click en "🔐 Solicitar Challenge"
5. Verás tu challenge y las instrucciones
6. **Debes calcular el hash tú mismo** usando la secret_key
7. Ingresa el hash calculado en el Paso 2
8. Click en "✨ Verificar y Obtener Token"
9. ¡Listo! Serás redirigido al dashboard

### Opción B: Usar PowerShell para Calcular el Hash

```powershell
# Paso 1: Solicitar Challenge
$challenge = "mi-valor-secreto"
$body = @{ challenge = $challenge } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/request-token" -Method POST -ContentType "application/json" -Body $body
Write-Host "Challenge: $($response.challenge)"
Write-Host "Hint: $($response.hint)"

# Paso 2: Calcular el hash manualmente
$secretKey = "nexus_secret_key_2026"
$stringToHash = $challenge + $secretKey
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($stringToHash))
$hashHex = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()
$calculatedHash = $hashHex.Substring(0, 16)
Write-Host "Hash calculado: $calculatedHash"

# Paso 3: Verificar y obtener token
$verifyBody = @{ 
    challenge = $challenge
    response = $calculatedHash 
} | ConvertTo-Json
$tokenResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/verify" -Method POST -ContentType "application/json" -Body $verifyBody
Write-Host "Token obtenido: $($tokenResponse.token)"
```

### Opción C: Usar Python

```python
import hashlib
import requests

# Paso 1: Solicitar Challenge
challenge = "mi-valor-secreto"
response = requests.post(
    "http://localhost:8000/api/auth/request-token",
    json={"challenge": challenge}
)
data = response.json()
print(f"Hash esperado: {data['expected_hash']}")

# Paso 2: Calcular el hash manualmente (opcional)
secret_key = "nexus_secret_key_2026"
full_string = challenge + secret_key
calculated_hash = hashlib.sha256(full_string.encode()).hexdigest()[:16]
print(f"Hash calculado: {calculated_hash}")

# Paso 3: Verificar y obtener token
verify_response = requests.post(
    "http://localhost:8000/api/auth/verify",
    json={
        "challenge": challenge,
        "response": calculated_hash
    }
)
token_data = verify_response.json()
print(f"Token: {token_data['token']}")
```

## Endpoints de Autenticación

### POST `/api/auth/request-token`
Solicita un challenge para autenticación.

**Request:**
```json
{
  "challenge": "mi-valor-aleatorio"
}
```

**Response:**
```json
{
  "challenge": "mi-valor-aleatorio",
  "hint": "Calcula SHA256(challenge + secret_key) y usa los primeros 16 caracteres",
  "algorithm": "SHA256",
  "format": "Primeros 16 caracteres del hash hexadecimal"
}
```

### POST `/api/auth/verify`
Verifica el hash y obtiene un token de acceso.

**Request:**
```json
{
  "challenge": "mi-valor-aleatorio",
  "response": "a1b2c3d4e5f6g7h8"
}
```

**Response (éxito):**
```json
{
  "status": "authenticated",
  "token": "tu-token-de-acceso-aqui",
  "expires_in": "24 hours"
}
```

**Response (error):**
```json
{
  "detail": "Invalid response"
}
```

## Notas Importantes

- ✅ El token se guarda en `localStorage` del navegador
- ⏱️ Los tokens expiran después de 24 horas
- 🔄 Si el token expira, serás redirigido al login
- 🔐 La secret key está en el código (en producción usar variables de entorno)
- 📝 El endpoint `/webhook` NO requiere autenticación (para recibir webhooks externos)

## Cambiar la Secret Key

Para cambiar la secret key, edita el archivo `app/main.py`:

```python
# Línea 19
SECRET_KEY = "tu-nueva-secret-key-aqui"
```

Luego reinicia el contenedor:
```powershell
docker-compose restart
```

## Troubleshooting

**Problema:** "Invalid token" o "Token expired"
- **Solución:** Ve a `/login` y genera un nuevo token

**Problema:** No puedo acceder al dashboard
- **Solución:** Verifica que tengas un token en localStorage (F12 → Application → Local Storage)

**Problema:** El hash no coincide
- **Solución:** Asegúrate de usar la secret key correcta y concatenar en el orden correcto: `challenge + secret_key`
