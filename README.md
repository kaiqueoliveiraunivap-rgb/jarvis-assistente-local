# J.A.R.V.I.S.

Assistente digital local e residente para Windows 10/11. O projeto combina voz, contexto, memória, automação controlada, monitoramento e uma interface própria — sem dar ao modelo acesso irrestrito a Python, PowerShell ou CMD.

O foco desta versão é funcionalidade real. Há 62 tools registradas para Windows, arquivos, teclado, mouse, áudio, mídia, navegador, visão e monitoramento. Componentes opcionais retornam um diagnóstico claro quando o respectivo pacote ou modelo ainda não está instalado.

## O que já funciona

- interface PySide6 escura com núcleo animado, waveform, dashboard, console, overlay e system tray;
- estados globais e reações visuais (`STANDBY`, `LISTENING`, `THINKING`, `EXECUTING`, `ALERT` etc.);
- wake word local por openWakeWord, usando o modelo `hey_jarvis`, com fallback por transcrição;
- STT offline em português por faster-whisper, com VAD, silêncio, timeout e escolha de microfone;
- TTS por Piper; fallback para a voz SAPI do Windows;
- conversation mode com timeout configurável;
- interrupção do TTS ao dizer “Jarvis” quando o detector dedicado está ativo;
- intents diretos sem LLM para comandos comuns;
- conversa e planejamento por Ollama, por meio de uma interface de provider substituível;
- planos JSON limitados a tools registradas e argumentos validados;
- confirmação antes de desligar, reiniciar, suspender ou excluir;
- cancelamento cooperativo e proteção de processos essenciais do Windows;
- memória SQLite seletiva, com recusa de senhas, tokens, cartões e segredos;
- macros e aliases persistentes em JSON;
- contexto de horário, janela ativa, ociosidade, CPU, RAM, disco, bateria e uptime;
- alertas com importância e cooldown;
- captura de tela somente conforme a política de privacidade, com indicador visual;
- análise de tela por um modelo multimodal do Ollama configurado pelo usuário;
- 32 testes automatizados, todos sem ações destrutivas reais.

## Arquitetura de segurança

```text
voz/texto
   │
   ▼
IntentRouter ─── comando conhecido ───► DeterministicPlanner
   │                                         │
   └── ambíguo ─► Ollama ─► plano JSON ─────┘
                                             │
                                             ▼
ToolRegistry ─► PermissionManager ─► Executor ─► Windows
                      │
                      └── confirmação para risco alto
```

O Ollama recebe nomes e esquemas de tools. Uma resposta do modelo só vira ação depois que:

1. o JSON é válido;
2. a tool existe no registro local;
3. não há parâmetros desconhecidos ou ausentes;
4. a política de risco permite a ação;
5. uma confirmação explícita é obtida, quando necessária.

Não existe tool para shell, Python arbitrário, PowerShell arbitrário ou instalação silenciosa. Tools `CRITICAL` são negadas por padrão. Exclusões usam a Lixeira, não remoção permanente.

## Requisitos

- Windows 10 ou Windows 11;
- Python 3.12 ou superior;
- microfone para comandos de voz;
- [Ollama para Windows](https://ollama.com/download/windows) para conversa e planejamento local;
- aproximadamente 3–8 GB livres para dependências e modelos, conforme os modelos escolhidos.

## Distribuição Windows 1.0.0

Para uso em outro computador, prefira `dist/JARVIS-Windows-v1.0.0.zip`. Esse pacote contém o runtime Python, `JARVIS.exe` sem console, um executável de diagnóstico com console, instalador, desinstalador e modelos pequenos de wake word. O usuário final não precisa instalar Python.

Também são gerados:

- `JARVIS-Portable-v1.0.0.zip`, que mantém configurações e dados na pasta extraída;
- `JARVIS-Source-v1.0.0.zip`, para desenvolvimento;
- `SHA256SUMS.txt`, para conferir a integridade dos downloads.

O instalador distribuível usa `%LOCALAPPDATA%\Programs\JARVIS` para a aplicação e `%LOCALAPPDATA%\JARVIS` para configurações, SQLite, memórias, logs, cache e modelos. Ollama e os modelos grandes de IA/Whisper não são incluídos no ZIP; o download é sempre informado e solicitado.

Para reconstruir os pacotes a partir do código-fonte:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
build.bat
```

## Instalação

No Explorador, abra esta pasta e execute:

```bat
install.bat
```

O instalador:

1. valida Python 3.12+;
2. cria `.venv`;
3. instala interface, automação e voz;
4. prepara configurações e SQLite;
5. baixa `hey_jarvis` e Whisper `small` para uso offline;
6. testa a inicialização;
7. verifica microfone, áudio, Ollama e dependências.

Para incluir Playwright e um Chromium isolado:

```bat
install.bat --with-browser
```

Depois, instale/inicie o Ollama e baixe o modelo configurado. `qwen3:4b` está disponível no [catálogo oficial do Ollama](https://ollama.com/library/qwen3/tags):

```bat
ollama pull qwen3:4b
```

Inicie o assistente:

```bat
start_jarvis.bat
```

Na primeira execução, o wizard configura nome, microfone, saída/voz, wake word, modelo STT, modelo de IA, personalidade, privacidade, proatividade e inicialização com Windows.

## Modos de execução

```bat
start_jarvis.bat                 rem interface normal
start_jarvis.bat --background    rem somente na bandeja
start_jarvis.bat --cli           rem modo texto
start_jarvis.bat --check         rem smoke test e diagnóstico de IA
start_jarvis.bat --no-monitor    rem sem monitoramento nesta sessão
```

Também é possível executar o diagnóstico completo:

```bat
.venv\Scripts\python.exe -m jarvis.diagnostics
```

## Voz e wake word

O caminho preferencial em standby é:

```text
microfone 16 kHz → openWakeWord “hey_jarvis” → faster-whisper → comando
```

O [openWakeWord](https://github.com/dscripka/openWakeWord) fornece o modelo `hey_jarvis` e também aceita modelos customizados. Para usar seu próprio arquivo `.onnx`/`.tflite`, defina `voice.wake_model_path` em `data/settings.json`.

No Windows/Python 3.12, prefira modelos customizados `.onnx`. O instalador baixa os recursos oficiais de `hey_jarvis` e usa ONNXRuntime; se esse download falhar, o diagnóstico sinaliza a ausência e o fallback por transcrição permanece ativo.

Se o modelo dedicado não carregar, o sistema usa detecção da palavra “Jarvis” na transcrição local. Esse fallback funciona, mas consome mais recursos porque precisa transcrever cada fala detectada.

Configurações principais de voz:

```json
{
  "voice": {
    "microphone": null,
    "wake_word": "jarvis",
    "wake_model_path": null,
    "whisper_model": "small",
    "language": "pt",
    "sensitivity": 0.55,
    "silence_seconds": 1.1,
    "conversation_timeout_seconds": 35.0
  }
}
```

Modelos Whisper maiores tendem a reconhecer melhor, mas usam mais RAM e demoram mais. `small` é o padrão equilibrado.

## Text-to-speech

Para Piper, configure o executável (se ele não estiver no PATH) e um modelo `.onnx`:

```json
{
  "voice": {
    "piper_executable": "C:\\caminho\\piper.exe",
    "piper_model": "C:\\caminho\\pt_BR-voz-medium.onnx"
  }
}
```

Sem um modelo Piper configurado, o J.A.R.V.I.S. usa SAPI/pywin32. O modo `SILENT` mantém respostas na interface e suprime a fala originada pelo fluxo de voz.

## Ollama e modelos

A IA é desacoplada por `AIProvider`. A implementação atual é `OllamaClient`; outra implementação pode ser adicionada sem alterar intents, tools ou executor.

```json
{
  "ai": {
    "provider": "ollama",
    "model": "qwen3:4b",
    "vision_model": null,
    "endpoint": "http://127.0.0.1:11434",
    "temperature": 0.35
  }
}
```

Sem Ollama, todos os comandos determinísticos continuam operando. Apenas conversa livre, planejamento ambíguo e análise multimodal ficam indisponíveis.

Para visão, instale um modelo multimodal compatível no Ollama e preencha `ai.vision_model`. Capturas nunca são feitas quando `screen_awareness` é `OFF`.

## Comandos

Alguns exemplos já roteados sem LLM:

| Categoria | Exemplos |
|---|---|
| Aplicativos | “Jarvis, abra o Spotify”, “feche o Discord”, “volte para o VS Code” |
| Janelas | “maximize o Chrome”, “coloque o VS Code à esquerda”, “organize minhas janelas” |
| Áudio | “volume 30%”, “mute”, “aumente o volume” |
| Mídia | “próxima música”, “pause”, “faixa anterior” |
| Teclado | “escreva Olá mundo”, “pressione Enter”, “Ctrl S” |
| Mouse | “clique”, “clique duas vezes”, “role para baixo” |
| Arquivos | “procure apresentação.pptx”, “abra Downloads”, “crie uma pasta chamada Projetos” |
| Navegador | “abra o YouTube”, “pesquise Python no Google” |
| Sistema | “quanto de RAM estou usando?”, “quais programas usam mais memória?” |
| Visão | “tire uma screenshot”, “olha esse erro”, “o que está na tela?” |
| Memória | “lembre que meu projeto principal é Gigi”, “lembra de projeto principal?” |
| Modos | “modo trabalho”, “modo foco”, “modo jogo”, “modo silencioso” |
| Controle | “cancelar”, “pare”, “desligue o computador” → pede confirmação |

## Tools disponíveis

O registro é montado em `jarvis/tools/builtin_tools/__init__.py`. As famílias implementadas incluem:

- apps: abrir, fechar, localizar e verificar processos;
- janelas: listar, focar, mover, redimensionar, minimizar, maximizar, restaurar e posicionar;
- entrada: digitar, pressionar teclas/hotkeys, mover/clicar/arrastar/rolar;
- clipboard: ler, escrever e limpar;
- áudio/mídia: volume exato, mute, teclas multimídia;
- arquivos: procurar, abrir, criar pasta, copiar, mover, renomear, informar e enviar à Lixeira;
- sistema: CPU, RAM, disco, bateria, processos, uptime, bloqueio, suspensão, desligamento e reinício;
- navegador: URL e busca do Google; Playwright opcional em sessão isolada;
- visão: screenshot sob política de privacidade.

Para criar uma tool, use o decorador e registre o handler explicitamente:

```python
@tool(
    name="minha_tool",
    description="Executar uma ação específica",
    category="custom",
    risk=RiskLevel.LOW,
)
def minha_tool(value: str) -> ToolResult:
    return ToolResult.ok("Pronto.", {"value": value})
```

## Macros e aliases

Macros ficam em `data/custom_commands.json`:

```json
{
  "aliases": {"navegador": "chrome"},
  "macros": {
    "modo_programacao": {
      "description": "Preparar ambiente de programação",
      "triggers": ["modo programação", "vamos trabalhar"],
      "actions": [
        {"tool": "open_app", "args": {"name": "vs code"}},
        {"tool": "open_app", "args": {"name": "chrome"}}
      ]
    }
  }
}
```

Ao carregar, cada ação é validada pelo registro. Uma macro com tool inventada ou argumentos desconhecidos interrompe o carregamento em vez de executar parcialmente.

## Memória e privacidade

O banco `data/jarvis.db` usa quatro categorias:

- `SHORT_TERM`: contexto em memória da conversa atual;
- `LONG_TERM`: preferências persistentes;
- `EPISODIC`: eventos relevantes concluídos;
- `SEMANTIC`: fatos úteis solicitados pelo usuário.

O avaliador não salva tudo. Senhas, tokens, chaves de API, PINs e sequências parecidas com cartão são recusados. Conteúdo de tela não é transformado automaticamente em memória. Logs passam por redator de segredos e rotacionam em `logs/jarvis.log`.

Políticas de tela:

- `OFF`: captura bloqueada;
- `ON_DEMAND`: padrão; captura somente por comando;
- `ACTIVE`: arquitetura preparada para observação ampliada, mantendo indicador visual.

A câmera permanece desativada. Esta versão não implementa captura de câmera escondida nem vigilância contínua.

## Proatividade

O monitor roda por evento, em intervalo configurável e sem loops agressivos. Ele observa:

- RAM a partir de 90%;
- CPU a partir de 95%;
- disco a partir de 92%;
- bateria até 8% fora da tomada.

Cada tipo de alerta possui cooldown (15 minutos por padrão). `FOCUS`, `GAMING` e `SILENT` reduzem interrupções. Nenhum padrão de rotina executa ação importante sem autorização.

## Estrutura

```text
jarvis/
├── ai/             providers, Ollama, prompts e planners
├── automation/     macros, rotinas, scheduler e proatividade
├── browser/        URLs e Playwright opcional
├── computer/       apps, janelas, entrada, áudio, arquivos e sistema
├── context/        tempo, atividade, tela e estado do computador
├── core/           assistente, eventos, estado, intents, permissões e executor
├── database/       SQLite e migrações
├── memory/         memória seletiva e tipos persistentes
├── personality/    estilo, humor comportamental e preferências
├── tools/          contrato, risco e registro central
├── ui/             janela, núcleo, waveform, overlay, tray e wizard
├── vision/         screenshot e análise multimodal
└── voice/          microfone, wake word, Whisper, Piper/SAPI e barge-in
```

## Testes

```bat
run_tests.bat
```

Ou diretamente:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes usam banco e arquivos temporários. Desligamento, reinício, exclusão, teclado, mouse, apps e janelas nunca são acionados pela suíte.

## Solução de problemas

### `Python não foi encontrado`

Instale Python 3.12+ e marque a opção para adicioná-lo ao PATH. Feche e reabra o terminal antes de repetir `install.bat`.

### Ollama indisponível

Confirme que o aplicativo está iniciado e rode:

```bat
ollama list
ollama pull qwen3:4b
```

Verifique se `ai.endpoint` continua em `http://127.0.0.1:11434`. HTTP remoto é bloqueado; endpoints remotos precisam usar HTTPS.

### Microfone não aparece

- autorize acesso ao microfone em Configurações do Windows → Privacidade;
- execute `python -m jarvis.diagnostics`;
- deixe `voice.microphone` como `null` para usar o dispositivo padrão.

### Wake word gera falsos positivos

Ajuste `voice.sensitivity` gradualmente. Para ambientes específicos, treine um modelo customizado seguindo os recursos do openWakeWord e configure `wake_model_path`.

### Volume exato não funciona

Confirme a instalação de `pycaw` e `comtypes`. Teclas de aumentar/diminuir mídia usam a API de teclado do Windows e continuam independentes.

### Brilho não muda

Alguns monitores externos não expõem controle DDC/CI ou exigem que ele seja habilitado no menu físico. O módulo retorna o erro do dispositivo sem alterar outras configurações.

### Interface não abre

Execute `start_jarvis.bat --cli` e depois `python -m jarvis.diagnostics`. O log fica em `logs/jarvis.log`.

## Limites conhecidos

- a qualidade do wake word depende do microfone, do modelo e do ambiente; o fallback por Whisper é mais pesado;
- interrupção de TTS por “Jarvis” usa o detector dedicado; “pare/cancelar” é imediato quando o sistema já está ouvindo, mas não possui ainda um classificador acústico dedicado durante a fala;
- análise de tela exige um `vision_model` multimodal local configurado no Ollama;
- automação avançada do navegador usa um perfil Playwright isolado e não reutiliza senhas do navegador pessoal;
- temperatura de hardware depende do que o Windows e os drivers expõem; o projeto não força drivers de baixo nível;
- ações administrativas arbitrárias continuam deliberadamente indisponíveis.

## Desenvolvimento

O núcleo evita imports pesados na inicialização. Dependências de voz, visão e automação são carregadas apenas quando usadas. Para uma verificação rápida:

```bat
.venv\Scripts\python.exe -m compileall -q jarvis tests main.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe main.py --check
```

Ao adicionar funcionalidades:

1. declare risco e categoria da tool;
2. valide entradas antes de qualquer efeito;
3. prefira APIs específicas a shell;
4. exija confirmação para mudanças destrutivas;
5. crie teste com mock ou diretório temporário;
6. nunca registre conteúdo sensível.
