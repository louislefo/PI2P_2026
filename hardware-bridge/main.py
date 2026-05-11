import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import servo, intercom, keypad
from core.hardware import call_button, move_servo

app = FastAPI(title="PI2P Hardware Bridge", version="2.0 (Modular)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(servo.router)
app.include_router(intercom.router)
app.include_router(keypad.router)

_main_loop = None

@app.on_event("startup")
async def startup():
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    print("✅ [HW-BRIDGE] Boucle asyncio capturée")
    
    # Connexion du bouton physique au gestionnaire d'appels (CallManager)
    if hasattr(call_button, "when_pressed"):
        # gpiozero appelle cette fonction dans un thread séparé
        call_button.when_pressed = lambda: intercom.call_manager.trigger_call(_main_loop)
        print("🔗 [HW-BRIDGE] Bouton physique connecté au CallManager")

    # Démarrage du scanner de clavier en arrière-plan
    asyncio.create_task(keypad.keypad_manager.run_scanner())

    print("🔧 [SERVO] Initialisation → position FERMÉE (0°)")
    move_servo(0)
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
