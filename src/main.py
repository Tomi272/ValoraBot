# Archivo: src/main.py
from fastapi import FastAPI
from src.modules.identity.router import router as identity_router
from src.modules.products.router import router as products_router

app = FastAPI(
    title="ValoraBot Enterprise Core API",
    version="1.0.0"
)

# Inclusión de las rutas del módulo Identity & Access Context
app.include_router(identity_router)
app.include_router(products_router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "ValoraBot Core API"}