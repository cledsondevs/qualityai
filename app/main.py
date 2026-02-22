from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Orquestrador AI",
        description="Automação Mobile inteligente com LLM local (Ollama) + Appium",
        version="1.0.0",
    )

    # Rotas da API
    app.include_router(router, prefix="/api")

    # Screenshots da automação
    app.mount("/screenshots", StaticFiles(directory="app/static"), name="screenshots")

    # Arquivos estáticos do frontend
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()
