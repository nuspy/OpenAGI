# Integrazioni locali — punti di connessione

Documento minimale: cosa si integra **solo in sviluppo locale sulla tua
macchina** (perché i progetti e le credenziali vivono lì) e cosa è già
pronto in questo repository. Qui sono implementati **solo i punti di
connessione**: porta tipizzata + mock + conformance suite; l'adapter
reale si scrive localmente e si collega senza toccare il core
(ports & adapters, spec §16).

## Le integrazioni rimandate al locale

| Integrazione | Perché locale | Porta (qui) | Skeleton adapter | Tool esposti (risk class) |
|---|---|---|---|---|
| **llmswitch** (libreria provider LLM) | la libreria è sul tuo PC | `pgdca/cognition/gateway.py` → `LlmPort` | ✅ **implementato**: `examples/adapters/local_llm_provider_adapter.py` | è il gateway stesso |
| **CallAPICall** (voce/telefono) | progetto esistente sul tuo PC | `pgdca/ports/voice.py` → `VoiceCallPort` | ✅ **implementato**: `examples/adapters/call_api_call_adapter.py` | `voice.call` (EXTERNAL_COMMUNICATION) |
| **Email** | credenziali/caselle locali | `pgdca/ports/messaging.py` → `EmailPort` | da scrivere sul modello degli altri | `email.send` (EXTERNAL_COMMUNICATION), `email.fetch` (READ_ONLY, output untrusted) |
| **SMS** | credenziali locali | `pgdca/ports/messaging.py` → `SmsPort` | idem | `sms.send`, `sms.fetch` |
| **Browser agentico** | browser/profili locali | `pgdca/ports/browser.py` → `BrowserPort` | idem (Playwright/CDP a scelta) | `browser.navigate/click/type/extract` (EXTERNAL_COMMUNICATION) |
| **Vault / pagamenti** | segreti e metodi di pagamento locali | `pgdca/ports/vault.py` → `VaultPort` | idem | `vault.pay` (FINANCIAL) — solo handles, mai credenziali |
| **Identity / 2FA** | segreti locali | `pgdca/ports/vault.py` → `IdentityPort` | idem | `identity.auth_session`, `identity.request_2fa` (IDENTITY) |
| **Server MCP locali** | i server girano sul tuo PC | già supportato | — | import dalla GUI (Capabilities) o `POST /api/mcp/import` col comando locale |

Nel server di sviluppo questi tool compaiono nel **tab Capabilities**
come `DISABLED (pending local adapter)`: il punto di connessione esiste,
la capacità reale arriva con l'adapter.

## Stato reale (2026-08-30, macchina del proprietario)

### llmswitch dietro `LlmPort` — COLLEGATO

`LocalProviderAdapter` risolve l'endpoint per funzione cognitiva tramite
il `Registry` di llmswitch (endpoint OpenAI-compatibili; regola della
VRAM inclusa per i motori locali), tiene le istruzioni nel system prompt
con la richiesta come DATI (stesso framing dell'adapter Anthropic),
allega l'usage reale come `_usage` e supporta il routing M13
(`consumer_by_role` → provider diverso per ruolo, `model_by_role` →
modello diverso per ruolo).

Setup:

```bash
pip install -e C:/Projects/llmswitch          # nel venv del repo
python -m pgdca.api.server --adapter llmswitch
```

Variabili d'ambiente (nessun segreto nel repo: le chiavi stanno nel file
del registro llmswitch, fuori dalle cartelle di progetto):

| Variabile | Default | Significato |
|---|---|---|
| `PGDCA_LLMSWITCH_APP` | `pgdca` | app name del registro (`%LOCALAPPDATA%\pgdca\llm_providers.json`) |
| `PGDCA_LLMSWITCH_CONSUMER` | `chat` | consumer di default |
| `PGDCA_LLMSWITCH_CONSUMER_BY_ROLE` | `{}` | JSON ruolo→consumer (M13, es. `{"critique": "copilot"}`) |
| `PGDCA_LLMSWITCH_MODEL_BY_ROLE` | `{}` | JSON ruolo→modello (M13) |
| `PGDCA_LLMSWITCH_CARICA` | `1` | `0` = mai caricare modelli in VRAM di propria iniziativa |
| `PGDCA_LLM_MAX_TOKENS` | `16000` | tetto di completion |

Provider non supportati dall'adapter (errore chiaro): i CLI-agenti
(nessun endpoint, secondi a risposta), il dialetto Anthropic (usa
`AnthropicLlmAdapter`) e Cloud Code. Verifica: `pytest
tests/test_local_llm_adapter.py` (fake, gira ovunque);
`PGDCA_LLMSWITCH_LIVE=1` aggiunge la conformance vera contro il registro
reale. Loop end-to-end dimostrato con LM Studio (`qwen/qwen3.8-27b`).

### CallAPICall dietro `VoiceCallPort` — COLLEGATO

Lato CallAPICall (repo `C:\Projects\callAPIcall`, commit "API REST
/external/*") il control server (`:8770`) espone le chiamate pilotate
turno-per-turno dall'esterno: `POST /external/call` (con `greeting`
obbligatorio: è la PRIMA frase pronunciata), `/say`, `/heard`
(long-poll), `/transcript`, `/state`, `/hangup`. Il "cervello" della
chiamata è un `ExternalBrain` a code, non l'agente Hermes.

`CallAPICallAdapter` mappa la porta su quelle API con un dettaglio che
preserva la compliance: la chiamata reale parte alla **prima**
`speak()`, il cui testo diventa il `greeting` — e la prima `speak()` del
wrapper `voice.call` è sempre la disclosure AI (art. 50), che quindi
arriva in testa alla chiamata anche sul filo.

Variabili d'ambiente: `CALLBRIDGE_CONTROL_URL` (default
`http://127.0.0.1:8770`), `CALLBRIDGE_CONTROL_TOKEN` (il token sta nel
`config.json` locale di CallAPICall, non qui), `CALLBRIDGE_VOICE`,
`CALLBRIDGE_LANG`. Avvio del bridge: `main.py serve` (solo control
server) o l'architettura split del README di CallAPICall.

Collegamento nel loop:

```python
from examples.adapters.call_api_call_adapter import CallAPICallAdapter
from pgdca.tools.external import register_external_ports
register_external_ports(ctrl.registry, voice=CallAPICallAdapter(),
                        principal="Andrea")
```

⚠️ La conformance suite della porta voce **compone numeri veri**: va
eseguita SOLO a mano, verso un numero di test fornito dal proprietario.
I test automatici (`tests/test_call_api_call_adapter.py`) girano su un
fake in-memory dell'API REST; `CALLBRIDGE_LIVE=1` aggiunge solo un ping
a `/health`, mai una chiamata.

## Passi di integrazione (uguali per ogni porta)

1. Implementa la `Protocol` della porta nel tuo repo locale (o partendo
   dagli skeleton in `examples/adapters/`).
2. Esegui la conformance suite della porta
   (`pgdca.ports.<modulo>.conformance(adapter)` → lista vuota = ok).
3. Collega l'adapter:
   - LLM: `python -m pgdca.api.server --adapter ...` o
     `Controller(runtime, adapter=TuoAdapter(), ...)`;
   - altri: `register_external_ports(ctrl.registry, voice=TuoAdapter(), ...)`
     (`pgdca/tools/external.py`).
4. Verifica nella GUI → Capabilities: il tool passa da DISABLED ad
   ACTIVE.
5. Non cambia nient'altro: Supervisor, guardrail Tier 1/2, budget,
   taint e journal si applicano identici ai tool reali.

## Requisiti di sicurezza (non negoziabili, valgono anche in locale)

- **Segreti mai nel contesto LLM né negli eventi**: le porte accettano
  e restituiscono solo *handles* (`payment_method_id`,
  `auth_session_id`, …); i codici 2FA restano lato umano.
- **Output esterni = dati untrusted**: trascrizioni, email ricevute,
  pagine web e output MCP arrivano marcati `untrusted` e sottostanno
  alla dottrina injection (taint).
- **Disclosure AI nelle chiamate vocali** (AI Act art. 50): il wrapper
  `voice.call` pronuncia la disclosure come prima frase — è nel codice,
  l'adapter non può saltarla.
- **Identità onesta**: `email.send` firma "per conto di <principal>";
  mai impersonificazione.
- **Promozione di risk class solo umana**: un adapter nuovo non allarga
  mai da solo ciò che può fare.

## Cosa faremo più avanti (quando integreremo in locale)

- adapter reali per le porte rimanenti (email, SMS, browser, vault,
  identity) + estensione degli scenari oltre il dominio giocattolo;
- sandbox indurita per tool importati e compensazione delle azioni
  revocate;
- autenticazione reale della GUI (oggi l'header `X-Actor` è uno stub di
  sviluppo).
