import httpx
import json
import os
from dotenv import load_dotenv
from google import genai

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class LLMService:
    """Serviço de comunicação com múltiplos provedores de LLM (Ollama e Google Gemini)."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2:7b")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # Inicializa o cliente oficial do Google Gemini
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.gemini_model = "gemini-3-flash-preview"

    async def get_completion(self, prompt: str, provider: str = "ollama") -> str:
        if provider.lower() == "google":
            return await self._get_gemini_completion(prompt)
        return await self._get_ollama_completion(prompt)

    async def _get_ollama_completion(self, prompt: str) -> str:
        payload = {
            "model": self.ollama_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é um especialista em automação mobile com Appium. "
                        "Ajude o usuário a planejar, analisar e executar testes de automação. "
                        "Responda sempre em português brasileiro de forma clara e objetiva."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(self.ollama_url, json=payload)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                return "Erro: Tempo limite de conexão com o Ollama esgotado."
            except Exception as e:
                return f"Erro ao conectar com o Ollama: {str(e)}"

    async def _get_gemini_completion(self, prompt: str) -> str:
        """Usa o SDK oficial google-genai para obter a resposta do Gemini."""
        try:
            # O processamento é delegado ao SDK oficial.
            # Nota: O SDK 'google-genai' versão 1.x pode ter chamadas síncronas ou assíncronas.
            # Usaremos a forma sugerida pelo usuário para consistência.
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=(
                    "Você é um especialista em automação mobile com Appium. "
                    "Ajude o usuário a planejar, analisar e executar testes de automação. "
                    "Responda sempre em português brasileiro de forma clara e objetiva.\n\n"
                    f"Solicitação: {prompt}"
                )
            )
            return response.text
        except Exception as e:
            return f"Erro ao conectar com o Google Gemini (SDK): {str(e)}"


# Instância singleton
llm_service = LLMService()
