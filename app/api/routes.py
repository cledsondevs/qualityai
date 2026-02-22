import os
import json
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_service import llm_service
from app.services.automation_service import AutomationService

router = APIRouter()


# ---------- Schemas ----------

class PromptRequest(BaseModel):
    prompt: str

class DynamicRequest(BaseModel):
    device: str
    package: str
    goal: str
    provider: str = "ollama"

class ScenarioRunRequest(BaseModel):
    device: str
    package: str
    goal: str
    mode: str = "dynamic"  # "dynamic" ou "fixed"
    steps: list[str] = []
    provider: str = "ollama"

class ScenarioItauRequest(BaseModel):
    device: str
    agencia: str
    conta: str
    senha: str


# ---------- Endpoints ----------

@router.get("/scenarios", summary="Lista os cenários de teste salvos")
async def list_scenarios():
    scenarios_dir = os.path.join(os.getcwd(), "app", "scenarios")
    all_scenarios = []
    if os.path.exists(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".json"):
                with open(os.path.join(os.getcwd(), "app", "scenarios", filename), 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_scenarios.extend(data)
                    else:
                        all_scenarios.append(data)
    return all_scenarios


@router.get("/status", summary="Verifica o status da API")
async def get_status():
    return {
        "status": "online",
        "providers": ["ollama", "google"],
        "default": "ollama"
    }


@router.post("/ask-llm", summary="Faz uma pergunta direta à LLM")
async def ask_llm(request: PromptRequest):
    response = await llm_service.get_completion(request.prompt)
    return {"response": response}


@router.post("/run-dynamic", summary="Executa automação reativa via IA")
async def run_dynamic(request: DynamicRequest):
    app_id = request.package.strip()
    provider = request.provider.lower()
    
    # Instancia um novo serviço para cada execução (evita conflitos de driver)
    service = AutomationService()

    # 1. Descoberta Automática de Pacote
    package_discovered = app_id
    if "." not in app_id and app_id.lower() != "settings":
        discovery_prompt = (
            f"Qual é o ID do pacote Android (package name) mais provável para o aplicativo chamado '{app_id}'?\n"
            "Responda APENAS o ID do pacote, sem aspas e sem explicações."
        )
        package_discovered = (await llm_service.get_completion(discovery_prompt, provider=provider)).strip().strip("\"'")

    # 2. Execução Reativa
    execution_log = await service.run_reactive_loop(
        device_name=request.device,
        app_package=package_discovered,
        goal=request.goal,
        llm_fn=lambda p: llm_service.get_completion(p, provider=provider)
    )

    # 3. Análise Final
    analysis_prompt = (
        f"O objetivo era: '{request.goal}'\n\n"
        f"O log de execução reativa foi:\n{execution_log}\n\n"
        "Com base nisso, dê uma conclusão final curta sobre o sucesso da tarefa."
    )
    final_analysis = await llm_service.get_completion(analysis_prompt, provider=provider)

    return {
        "package_discovered": package_discovered,
        "plan": f"Orquestração Reativa ({provider.upper()})",
        "log": execution_log,
        "analysis": final_analysis,
    }


@router.post("/run-scenario", summary="Executa um cenário (Fixo ou Dinâmico)")
async def run_scenario(request: ScenarioRunRequest):
    provider = request.provider.lower()
    service = AutomationService()
    
    if request.mode == "fixed" and request.steps:
        # Execução Determinística (Sem IA)
        execution_log = await service.run_fixed_script(
            device_name=request.device,
            app_package=request.package,
            steps=request.steps
        )
        plan_desc = "Script Fixo (Determinístico)"
    else:
        # Execução Reativa (Com IA)
        execution_log = await service.run_reactive_loop(
            device_name=request.device,
            app_package=request.package,
            goal=request.goal,
            llm_fn=lambda p: llm_service.get_completion(p, provider=provider)
        )
        plan_desc = f"IA Reativa ({provider.upper()})"

    # Análise Final via IA
    analysis_prompt = (
        f"O objetivo era: '{request.goal}'\n\n"
        f"O log de execução foi:\n{execution_log}\n\n"
        "Com base nisso, dê uma conclusão final curta sobre o sucesso da tarefa."
    )
    final_analysis = await llm_service.get_completion(analysis_prompt, provider=provider)

    return {
        "package": request.package,
        "mode": request.mode,
        "plan": plan_desc,
        "log": execution_log,
        "analysis": final_analysis,
    }


@router.post("/run-scenario/itau", summary="Cenário fixo antigo: Login no Itaú Investimentos")
async def run_scenario_itau(request: ScenarioItauRequest):
    service = AutomationService()
    log = await service.run_itau_login(
        device_name=request.device,
        agencia=request.agencia,
        conta=request.conta,
        senha=request.senha,
        llm_fn=llm_service.get_completion,
    )

    # LLM analisa o resultado
    analysis = await llm_service.get_completion(
        f"O resultado do cenário de login no Itaú foi:\n{log}\n\n"
        "Dê uma conclusão curta em português sobre o que funcionou e o que falhou."
    )

    return {"log": log, "analysis": analysis}
