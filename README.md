# Orquestrador AI 🤖

Automação Mobile inteligente com **LLM local (Ollama)** + **Appium**

## Estrutura do Projeto

```
.
├── app/
│   ├── api/
│   │   └── routes.py          # Rotas FastAPI
│   ├── services/
│   │   ├── llm_service.py     # Integração com o Ollama
│   │   └── automation_service.py # Motor de automação Appium
│   └── main.py                # Factory da aplicação
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── run.py                     # Ponto de entrada
├── requirements.txt
└── .gitignore
```

## Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.ai) rodando com o modelo `qwen2:7b`
- [Appium Server](https://appium.io) rodando na porta `4723`
- Emulador Android ativo

## Como Executar

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar o servidor (com hot-reload)
python run.py
```

Acesse em: **http://localhost:8000**

## Como Usar

1. **Configure** o nome do emulador e pacote do App.
2. **Descreva o objetivo** do teste (ex: "Clique em Redes e depois em Internet").
3. **Clique em "Gerar e Executar com IA"** — a LLM cria o roteiro e o Appium executa.
4. Veja a análise final da IA no painel de resultados.
