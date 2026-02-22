/* ──────────────────────────────────────────────────────────────────
   Quality AI — Logic
   ────────────────────────────────────────────────────────────────── */

const terminal = document.getElementById('terminal');
const btnExecute = document.getElementById('btn-execute');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const scenarioDropdown = document.getElementById('scenario-dropdown');
const llmSelector = document.getElementById('llm-selector');

const appPkgSelect = document.getElementById('app-pkg-select');
const appPkgCustom = document.getElementById('app-pkg-custom');
const goalTextarea = document.getElementById('dynamic-goal');
const deviceImg = document.getElementById('device-screen');

let scenarios = [];
let screenshotInterval = null;

// -- Refresh Screenshot --
function refreshScreenshot() {
    if (deviceImg) {
        // Adiciona timestamp para evitar cache do navegador
        deviceImg.src = `/screenshots/screenshot.png?t=${new Date().getTime()}`;
    }
}

// -- Handle Package Selection --
appPkgSelect.onchange = () => {
    if (appPkgSelect.value === 'custom') {
        appPkgCustom.style.display = 'block';
    } else {
        appPkgCustom.style.display = 'none';
        appPkgCustom.value = '';
    }
};

// -- Status Check --
async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        statusDot.className = 'dot online';
        statusText.textContent = `IA: ${data.providers.join(' / ').toUpperCase()}`;
    } catch {
        statusDot.className = 'dot';
        statusText.textContent = 'LLM: OFFLINE';
    }
}

// -- Load Scenarios --
async function loadScenarios() {
    try {
        const res = await fetch('/api/scenarios');
        scenarios = await res.json();

        scenarios.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.name;
            scenarioDropdown.appendChild(opt);
        });
    } catch (e) {
        console.error('Falha ao carregar cenários:', e);
    }
}

// -- Handle Scenario Selection --
scenarioDropdown.onchange = () => {
    const selectedId = scenarioDropdown.value;
    const scenario = scenarios.find(s => s.id === selectedId);

    if (scenario) {
        // Tenta encontrar o pacote no dropdown
        let found = false;
        for (let i = 0; i < appPkgSelect.options.length; i++) {
            if (appPkgSelect.options[i].value === scenario.package) {
                appPkgSelect.selectedIndex = i;
                found = true;
                break;
            }
        }

        if (found) {
            appPkgCustom.style.display = 'none';
            appPkgCustom.value = '';
        } else {
            appPkgSelect.value = 'custom';
            appPkgCustom.value = scenario.package;
            appPkgCustom.style.display = 'block';
        }

        goalTextarea.value = scenario.goal;
        log(`📂 Cenário selecionado: ${scenario.name}`, 'ai');
    } else {
        appPkgSelect.selectedIndex = 0;
        appPkgCustom.value = '';
        appPkgCustom.style.display = 'none';
        goalTextarea.value = '';
    }
};

// -- Helpers --
function colorizeLog(text) {
    if (!text) return '';
    return text
        .split('\n')
        .map(line => {
            if (line.includes('---')) return `<div class="log-header">${line.replace(/-/g, '')}</div>`;
            if (line.includes('✅')) return `<div class="log-success">${line}</div>`;
            if (line.includes('❌')) return `<div class="log-error">${line}</div>`;
            if (line.includes('🤖') || line.includes('⚠️')) return `<div class="log-ai">${line}</div>`;
            if (line.trim().length > 0 && !line.includes('⏳')) return `<div>${line}</div>`;
            return line;
        })
        .join('');
}

function log(msg, type = '') {
    if (type) {
        const div = document.createElement('div');
        div.className = `log-${type}`;
        div.textContent = msg;
        terminal.appendChild(div);
    } else {
        terminal.innerHTML += colorizeLog(msg);
    }
    terminal.scrollTop = terminal.scrollHeight;
}

function clearLog() {
    terminal.innerHTML = '';
}

// -- Execution --
btnExecute.onclick = async () => {
    const device = document.getElementById('dev-name').value.trim();

    // Calcula o pacote final
    let app = appPkgSelect.value;
    if (app === 'custom') {
        app = appPkgCustom.value.trim();
    }

    const goal = goalTextarea.value.trim();

    if (!goal) return alert('Informe o objetivo do teste.');
    if (!device) return alert('Informe o emulador.');

    const provider = llmSelector.value;
    const mode = document.getElementById('exec-mode').value;
    const selectedId = scenarioDropdown.value;
    const scenario = scenarios.find(s => s.id === selectedId);

    clearLog();
    btnExecute.disabled = true;

    log(`⏳ Modo: ${mode === 'fixed' ? 'SCRIPT FIXO 📜' : 'IA DINÂMICA 🧠'}`);
    log(`📱 Dispositivo: ${device}`);
    log(`🎯 App: ${app || 'Auto'}`);

    // Inicia atualização de screenshot
    screenshotInterval = setInterval(refreshScreenshot, 2000);

    try {
        const payload = {
            device,
            package: app,
            goal,
            provider,
            mode,
            steps: (mode === 'fixed' && scenario) ? scenario.steps : []
        };

        const res = await fetch('/api/run-scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        log(`\n--- LOG DE EXECUÇÃO (${data.plan}) ---`);
        log(colorizeLog(data.log));

        log('\n--- ANÁLISE FINAL ---', 'ai');
        log(data.analysis);

    } catch (e) {
        log(`\n❌ Erro crítico: ${e.message}`, 'error');
    } finally {
        btnExecute.disabled = false;
        // Para atualização de screenshot
        if (screenshotInterval) {
            clearInterval(screenshotInterval);
            screenshotInterval = null;
        }
    }
};

// Start
loadScenarios();
checkStatus();
setInterval(checkStatus, 10000);
