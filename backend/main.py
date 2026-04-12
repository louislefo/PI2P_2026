from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importation sécurisée des routeurs (qui initialisent le hardware au passage)
from routers import config_router, system_router, stream_router
from services.vision import processor

app = FastAPI(title="PI2P 2026 - Portail")

# Configuration CORS pour React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routes propres
app.include_router(config_router.router)
app.include_router(system_router.router)
app.include_router(stream_router.router)

@app.on_event("startup")
async def startup_event():
    print("🚀 [STARTUP] Démarrage des sous-systèmes...")
    processor.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 [SHUTDOWN] Arrêt des sous-systèmes...")
    processor.stop()
