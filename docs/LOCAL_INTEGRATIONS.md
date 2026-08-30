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
| **Libreria provider LLM** (tua, esistente) | la libreria è sul tuo PC | `pgdca/cognition/gateway.py` → `LlmPort` | `examples/adapters/local_llm_provider_adapter.py` | è il gateway stesso |
| **CallAPICall** (voce/telefono) | progetto esistente sul tuo PC | `pgdca/ports/voice.py` → `VoiceCallPort` | `examples/adapters/call_api_call_adapter.py` | `voice.call` (EXTERNAL_COMMUNICATION) |
| **Email** | credenziali/caselle locali | `pgdca/ports/messaging.py` → `EmailPort` | da scrivere sul modello degli altri | `email.send` (EXTERNAL_COMMUNICATION), `email.fetch` (READ_ONLY, output untrusted) |
| **SMS** | credenziali locali | `pgdca/ports/messaging.py` → `SmsPort` | idem | `sms.send`, `sms.fetch` |
| **Browser agentico** | browser/profili locali | `pgdca/ports/browser.py` → `BrowserPort` | idem (Playwright/CDP a scelta) | `browser.navigate/click/type/extract` (EXTERNAL_COMMUNICATION) |
| **Vault / pagamenti** | segreti e metodi di pagamento locali | `pgdca/ports/vault.py` → `VaultPort` | idem | `vault.pay` (FINANCIAL) — solo handles, mai credenziali |
| **Identity / 2FA** | segreti locali | `pgdca/ports/vault.py` → `IdentityPort` | idem | `identity.auth_session`, `identity.request_2fa` (IDENTITY) |
| **Server MCP locali** | i server girano sul tuo PC | già supportato | — | import dalla GUI (Capabilities) o `POST /api/mcp/import` col comando locale |

Nel server di sviluppo questi tool compaiono nel **tab Capabilities**
come `DISABLED (pending local adapter)`: il punto di connessione esiste,
la capacità reale arriva con l'adapter.

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

- adapter reali per le porte sopra + estensione degli scenari oltre il
  dominio giocattolo;
- sandbox indurita per tool importati e compensazione delle azioni
  revocate;
- autenticazione reale della GUI (oggi l'header `X-Actor` è uno stub di
  sviluppo).
