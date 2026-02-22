import re
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

APPIUM_SERVER = "http://localhost:4723"

# Prefixos de ação suportados
CLICK_PREFIXES   = ["clique em", "click on", "toque em"]
TYPE_PREFIXES    = ["digite", "escreva", "type", "insira"]
SCROLL_DOWN      = ["role para baixo", "scroll down", "deslize para baixo", "rolar para baixo"]
SCROLL_UP        = ["role para cima",  "scroll up",   "deslize para cima",  "rolar para cima"]
WAIT_PREFIXES    = ["espere", "aguarde", "wait"]


from app.core.parser import ui_parser
from app.core.hasher import ui_hasher


class AutomationService:
    """Serviço responsável por executar automações no emulador Android via Appium."""

    def __init__(self):
        self.driver = None
        self.last_ui_hash = None
        self.stuck_counter = 0
        self.decision_cache = {}  # {hash: last_decision}

    def _build_options(self, device_name: str, app_package: str) -> UiAutomator2Options:
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.automation_name = "UiAutomator2"
        options.device_name = device_name
        options.app_package = app_package
        options.no_reset = True
        options.adb_exec_timeout = 60000   # 60s
        options.new_command_timeout = 120  # 2 min
        return options

    def _quit(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            self.last_ui_hash = None
            self.stuck_counter = 0
            self.decision_cache = {}

    # ── Helpers de Ação ────────────────────────────────────────────────

    def _extract(self, step: str, prefixes: list) -> str | None:
        """Extrai o alvo de um comando, agora mais resiliente a textos extras."""
        low = step.strip().lower()
        # Se a IA respondeu com várias linhas, pega a primeira que contenha um prefixo conhecido
        lines = low.split('\n')
        for line in lines:
            line = line.strip()
            for p in prefixes:
                if line.startswith(p):
                    # Pega o texto original para não perder maiúsculas se necessário (ex: senhas)
                    idx = line.find(p)
                    value = line[idx + len(p):].strip().strip("\"':-")
                    # Limpa colchetes ou lixo comum
                    value = re.sub(r'[\[\]]', '', value).split('/')[0].strip()
                    return value
        return None

    def _click_element(self, target: str) -> bool:
        """Tenta click por texto ou content-desc."""
        # Ignora lixo comum que a IA possa colocar como "Botão" ou "Ícone"
        target = re.sub(r'(?i)^(botão|ícone|campo|seta)\s+', '', target)
        
        for selector in [
            f'new UiSelector().textContains("{target}")',
            f'new UiSelector().descriptionContains("{target}")',
            f'new UiSelector().textMatches("(?i).*{target}.*")',
            f'new UiSelector().className("android.widget.EditText")' if target.lower() in ["campo", "input"] else None
        ]:
            if not selector: continue
            try:
                el = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, selector)
                el.click()
                return True
            except Exception:
                pass
        return False

    def _scroll(self, direction: str = "down"):
        size = self.driver.get_window_size()
        cx = size["width"] // 2
        start_y = int(size["height"] * 0.7) if direction == "down" else int(size["height"] * 0.3)
        end_y   = int(size["height"] * 0.3) if direction == "down" else int(size["height"] * 0.7)
        self.driver.swipe(cx, start_y, cx, end_y, duration=600)

    async def _execute_step(self, step_text: str, log_list: list) -> bool:
        """Executa um comando unitário vindo da IA."""
        # Clique
        target = self._extract(step_text, CLICK_PREFIXES)
        if target:
            if self._click_element(target):
                log_list.append(f"✅ Executou: Clique em '{target}'")
                return True
            return False

        # Digitar (no elemento ativo ou tenta focar)
        value = self._extract(step_text, TYPE_PREFIXES)
        if value:
            try:
                # Tenta enviar para o elemento que está com foco
                el = self.driver.switch_to.active_element
                el.send_keys(value)
                log_list.append(f"✅ Executou: Digitou '{value}'")
                return True
            except Exception:
                # Se falhar, tenta achar um EditText e clicar antes
                try:
                    el = self.driver.find_element(AppiumBy.CLASS_NAME, "android.widget.EditText")
                    el.click()
                    el.send_keys(value)
                    return True
                except:
                    return False

        # Rolar
        if any(p in step_text.lower() for p in SCROLL_DOWN):
            self._scroll("down")
            log_list.append("✅ Executou: Rolagem para baixo")
            return True
        if any(p in step_text.lower() for p in SCROLL_UP):
            self._scroll("up")
            log_list.append("✅ Executou: Rolagem para cima")
            return True

        # Esperar
        wait_val = self._extract(step_text, WAIT_PREFIXES)
        if wait_val and wait_val.isdigit():
            time.sleep(int(wait_val))
            log_list.append(f"✅ Executou: Espera de {wait_val}s")
            return True

        return False

    # ── Modos de Execução ─────────────────────────────────────────────

    async def run_reactive_loop(
        self,
        device_name: str,
        app_package: str,
        goal: str,
        llm_fn,
    ) -> str:
        """
        [SPRINT 5] Otimização Arquitetural: UI Local Parsing + Decision Cache.
        """
        MAX_STEPS = 15
        results = []

        try:
            options = self._build_options(device_name, app_package)
            self.driver = webdriver.Remote(command_executor=APPIUM_SERVER, options=options)
            self.driver.implicitly_wait(5)
            self.driver.activate_app(app_package)
            time.sleep(3)

            for i in range(MAX_STEPS):
                results.append(f"\n--- PASSO {i+1} ---")
                
                # 1. Observar
                source = self.driver.page_source
                self.driver.save_screenshot('app/static/screenshot.png')  # Captura em tempo real
                minified_ui = ui_parser.parse_to_json(source)
                current_hash = ui_hasher.calculate_hash(minified_ui)
                
                is_stuck = False
                if current_hash == self.last_ui_hash:
                    self.stuck_counter += 1
                    if self.stuck_counter >= 2:
                        results.append("⚠️ Tela estática. Buscando alternativa...")
                        is_stuck = True
                else:
                    self.stuck_counter = 0
                
                self.last_ui_hash = current_hash

                # 2. Decidir (com Cache Otimizado)
                first_line = ""
                # Se não estamos travados e temos a tela em cache, podemos pular a IA (opcional)
                # No momento, vamos usar o cache apenas para AJUDAR o prompt se estivermos travados.
                
                prompt = (
                    "VOCÊ É UM ROBÔ DE AUTOMAÇÃO ANDROID.\n"
                    f"OBJETIVO: '{goal}'\n\n"
                    f"ESTRUTURA DA TELA (JSON):\n{minified_ui}\n\n"
                    "REGRAS:\n"
                    "1. Responda APENAS com a ação: Clique em [X], Digite [Y], Role para baixo, Espere [N].\n"
                    "2. Se o objetivo foi alcançado: 'OBJETIVO_ALCANÇADO'.\n"
                )
                
                if is_stuck:
                    prev_decision = self.decision_cache.get(current_hash, "Nenhuma")
                    prompt += f"\n⚠️ ATENÇÃO: Você está preso nesta tela. A última ação foi '{prev_decision}'. TENTE ALGO DIFERENTE."

                decision = (await llm_fn(prompt)).strip().strip("\"'")
                first_line = decision.split('\n')[0].strip()
                results.append(f"🤖 IA Decidiu: {first_line}")
                
                # Salva no cache
                self.decision_cache[current_hash] = first_line

                if "OBJETIVO_ALCANÇADO" in first_line.upper():
                    results.append("✅ Objetivo final atingido!")
                    break
                if first_line.upper().startswith("ERRO:"):
                    results.append(f"❌ Abortado: {first_line}")
                    break

                # 3. Atuar
                if not await self._execute_step(first_line, results):
                    results.append(f"⚠️ Falha técnica ao executar '{first_line}'.")
                
                time.sleep(2)
            else:
                results.append("❌ Limite de passos atingido.")

            return "\n".join(results)
        except Exception as e:
            return f"Erro na orquestração Sprint 5: {str(e)}"
        finally:
            self._quit()

    async def run_fixed_script(
        self,
        device_name: str,
        app_package: str,
        steps: list[str]
    ) -> str:
        """
        [SPRINT 6] Execução Determinística: Roda uma lista de passos fixos sem IA.
        """
        results = []
        try:
            options = self._build_options(device_name, app_package)
            self.driver = webdriver.Remote(command_executor=APPIUM_SERVER, options=options)
            self.driver.implicitly_wait(5)
            self.driver.activate_app(app_package)
            time.sleep(3)

            for i, step in enumerate(steps):
                results.append(f"\n--- PASSO {i+1} (FIXO) ---")
                results.append(f"📜 Comando: {step}")
                
                # Captura antes de cada passo fixo
                try:
                    self.driver.save_screenshot('app/static/screenshot.png')
                except:
                    pass
                
                if not await self._execute_step(step, results):
                    results.append(f"❌ Falha crítica no passo fixo: '{step}'. Interrompendo.")
                    break
                
                time.sleep(2)
            else:
                results.append("\n✅ Script fixo concluído com sucesso!")

            return "\n".join(results)
        except Exception as e:
            return f"Erro na execução fixa: {str(e)}"
        finally:
            self._quit()

    async def run_itau_login(self, device_name: str, agencia: str, conta: str, senha: str, llm_fn) -> str:
        """Cenário híbrido customizado (pode usar o loop reativo se quiser, mas mantemos o fluxo fixo inteligente)."""
        goal = f"Fazer login com Agencia {agencia}, Conta {conta} e Senha {senha}"
        return await self.run_reactive_loop(device_name, "com.itau.investimentos", goal, llm_fn)



# Singleton removido para evitar colisões em execuções paralelas.
# O AutomationService deve ser instanciado por requisição no routes.py.
