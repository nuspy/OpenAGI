# PGDCA — Analisi critica e proposte di modifica

**Documenti analizzati**: `PGDCA_Scientific_Paper.docx` (v1.0), `PGDCA_Cognitive_Architecture_Design_Rationale.md` (v1.0), `PGDCA_Cloud_Code_Implementation_Spec.md` (v1.0) — tutti datati 30 agosto 2026.
**Stato del documento**: decisioni registrate il 30/08/2026 — revisione v1.1 applicata ai documenti (M21 e M22 respinte, non applicate; il paper porta le modifiche come tracked changes da accettare/rifiutare in Word).
**Processo**: ogni voce Mx viene approvata, discussa fino al consenso o respinta; la tabella di stato qui sotto viene aggiornata a ogni decisione; le voci approvate vengono poi applicate ai tre documenti (i `.md` con edit diretti, il paper `.docx` con *tracked changes* revisionabili in Word).

---

## 1. Tabella di stato

| ID | Titolo | Priorità | Origine | Stato | Documenti target |
|----|--------|----------|---------|-------|------------------|
| M1 | Governance dei goal + corrigibilità | P0 | analisi | APPROVATA | Spec, Rationale, Paper |
| M2 | Difesa da prompt injection | P0 | analisi | APPROVATA | Spec, Rationale, Paper |
| M3 | Budget di autonomia consolidati | P0 | analisi | APPROVATA | Spec, Paper |
| M4 | Fette verticali + scala di milestone | P0 | analisi | APPROVATA | Spec, Rationale |
| M5 | Event sourcing, consistenza e replay | P1 | analisi | APPROVATA | Spec |
| M6 | Disciplina di scoring calibrato | P1 | analisi | APPROVATA | Spec |
| M7 | Guardrail sul grafo causale | P1 | analisi | APPROVATA | Spec, Rationale |
| M8 | Guardrail sul policy learning | P1 | analisi | APPROVATA | Spec |
| M9 | Cold start e curriculum | P1 | analisi | APPROVATA | Spec |
| M10 | Sicurezza nell'acquisizione di tool | P1 | analisi | APPROVATA | Spec |
| M11 | Compliance e privacy | P1 | analisi | APPROVATA | Spec, Paper |
| M12 | Riconciliazione incrementale | P2 | analisi | APPROVATA | Spec |
| M13 | Hardening del LLM gateway | P2 | analisi | APPROVATA | Spec |
| M14 | Schema canonico unificato | P2 | analisi | APPROVATA | tutti |
| M15 | Gerarchia come ruoli | P2 | analisi | APPROVATA | Spec, Rationale |
| M16 | Principio sostitutivo/complementare | P2 | analisi | APPROVATA | tutti |
| M17 | Igiene della memoria | P2 | analisi | APPROVATA | Spec |
| M18 | Operator console | — | analisi | ASSORBITA in M25 | — |
| M19 | Related work e riposizionamento | P1 | analisi | APPROVATA | Paper |
| M20 | Valutazione operazionalizzata | P1 | analisi | APPROVATA | Paper |
| M21 | SGI ridimensionata | P2 | analisi | RESPINTA | — |
| M22 | Consistenza e refusi | P3 | analisi | RESPINTA | — |
| M23 | Guardrail a due livelli | P0 | utente (rev. 2) | REQUISITO — asimmetria confermata | Spec, Rationale |
| M24 | Decision Supervisor | P0 | utente (rev. 2) | REQUISITO | Spec, Paper |
| M25 | GUI completa, frontend separato | P0 | utente (rev. 2) | REQUISITO | Spec, Rationale |
| M26 | Tool esterni interface-first | P1 | utente (rev. 2) | REQUISITO | Spec |
| M27 | Co-decisione in itinere | P1 | utente (rev. 2) | REQUISITO | Spec |
| M28 | Skills e MCP server importabili | P1 | utente (rev. 3) | REQUISITO | Spec, Rationale |

Priorità: **P0** = da risolvere prima di iniziare l'implementazione · **P1** = prima revisione dei documenti · **P2** = seconda passata · **P3** = cosmetica.

Le voci M23–M28 recepiscono i requisiti espressi dall'utente: sono requisiti da specificare nei documenti, non proposte da approvare.

**Registro delle decisioni (30/08/2026)**: approvate M1–M17 e M19–M20; respinte M21 e M22 (la sezione SGI e le denominazioni restano come in v1.0); confermata l'attivazione asimmetrica dei guardrail Tier 2 (M23); aggiunto il requisito M28 (skills e MCP server importabili).

*Nota sulla numerazione*: i riferimenti "§N" nelle proposte usano la numerazione **v1.0** dei documenti; nella v1.1 la numerazione è scalata per l'inserimento delle nuove sezioni.

---

## 2. Sintesi di verifica (cosa dicono i documenti)

- **Ipotesi centrale (T1)**: oltre una soglia di competenza del modello base, una parte sostanziale del gap verso l'AGI è architetturale, non di scala: si colma esternalizzando le funzioni esecutive (goal persistenti, memoria, pianificazione, verifica, audit, risorse, acquisizione di capacità) in un'architettura di controllo deterministica attorno a inferenza LLM ripetuta.
- **Distinzione chiave**: *model intelligence* (capacità in una singola inferenza) vs *system intelligence* (capacità emergente da un loop chiuso persistente con continuità temporale). L'LLM propone; il controller governa stato, lifecycle, autorizzazioni, scheduling.
- **Meccanismi portanti**: gerarchia di goal a 7 livelli con sub-goal provvisori (ipotesi falsificabili); goal reconciliation continua; grafo causale globale con relazioni first-class pesate (14–18 tipi, ~12 attributi) e antagonismi cross-goal; arbitraggio multi-obiettivo con opportunity cost e information gain; discovery di opportunità/tool/capacità come atto cognitivo; memoria multi-store (event / graph / vector / structured / policy); journal auditabile; distinzione decision quality ≠ outcome quality; astrazione episodio → pattern → policy senza aggiornare i pesi del modello; self-model calibrato; autorità deterministica sulle azioni esterne (vault, secure handles, risk class, escalation umana).
- **Valori e principi**: 18 principi architetturali (Rationale §72) + 25 decisioni non negoziabili (Spec §81); falsificabilità dichiarata (Paper §29), failure modes previsti (Paper §30), ablation study con budget di inferenza controllato (Paper §27, Rationale §84).

---

## 3. Opinione

### 3.1 Verdetto sintetico

Progetto insolitamente ben ragionato e internamente coerente, molto sopra la media dei framework agentici; la direzione è giusta e allineata all'evoluzione del campo. I documenti sono pronti per pubblicazione/implementazione **dopo** aver chiuso quattro buchi critici:

1. **Governance dei goal** — chi ratifica le modifiche ai goal persistenti? Manca un contratto di corrigibilità.
2. **Prompt injection** — mai menzionata in nessuno dei tre documenti, ed è il vettore d'attacco n.1 per un sistema che legge web/email e può pagare/comunicare.
3. **Budget di autonomia** — presenti a frammenti (§51, §63 dello spec), da consolidare in un meccanismo unico.
4. **Strategia implementativa** — lo spec è massimalista (≈16 sottosistemi, 10 worker, 6 tecnologie di storage prima che il loop giri) e la Definition of Done coincide con "AGI raggiunta".

I requisiti aggiunti dall'utente (guardrail a due livelli, Decision Supervisor, GUI completa) chiudono in modo naturale i primi tre buchi, fornendo il meccanismo concreto (Tier 1 / supervisor / superficie di override) che le mie proposte M1–M3 richiedevano.

### 3.2 Punti di forza (da preservare)

1. **Audit decision-quality ≠ outcome-quality → policy learning**: il meccanismo più distintivo e di maggior valore; quasi nessun framework lo implementa. È corretto in teoria della decisione (separare la bontà della scelta dalla fortuna dell'esito) ed è la base giusta per un apprendimento esperienziale che non premi la fortuna né punisca la sfortuna.
2. **Goal reconciliation continua con sub-goal come ipotesi**: la risposta corretta al failure mode storico degli agenti autonomi di prima generazione (AutoGPT e simili): perdere il filo, fissarsi su sub-task diventati irrilevanti.
3. **Separazione autorità deterministica / cognizione generativa** (vault, secure handles, risk class): architettura di sicurezza corretta, analoga ai sistemi capability-based. Anche la posizione su CAPTCHA (nessun bypass, human-in-the-loop) è corretta legalmente ed eticamente.
4. **Memoria multi-store** e rifiuto del vector-DB universale: corretto; la similarità semantica non è gestione dello stato.
5. **Onestà metodologica**: sezioni su falsificabilità, failure modes attesi, controllo del budget di inferenza nelle ablation — rare in questo genere di proposte.
6. **Il rationale come documento anti-erosione** per gli agenti implementatori: pratica intelligente; previene la semplificazione silenziosa dell'architettura in "prompt → LLM → tool".

### 3.3 Debolezze principali

1. **Governance dei goal sottospecificata**: il sistema riscrive continuamente la propria struttura di goal; Spec §65 chiede "stronger evidence/authorization" per modificare i goal persistenti ma non definisce né l'evidenza né l'autorità. Manca un contratto di corrigibilità (PAUSE/STOP/OVERRIDE incondizionati).
2. **Prompt injection assente**: PGDCA combina per design la "lethal trifecta" (accesso a dati privati + ingestione di contenuto esterno non fidato + capacità di comunicazione/pagamento verso l'esterno). Un sistema che naviga il web, legge email e trascrive telefonate ingerisce continuamente testo potenzialmente avversariale; senza una dottrina architetturale di separazione dati/istruzioni, qualunque pagina web può tentare di dirottare il loop cognitivo.
3. **Massimalismo implementativo**: le fasi (Spec §75, Rationale §75) sono strati orizzontali — prima tutta l'infrastruttura, poi il comportamento. Il rischio classico è mesi di lavoro senza mai chiudere il loop end-to-end. La Definition of Done (§82) elenca di fatto le capacità di un'AGI operativa: come criterio di completamento è irraggiungibile e invita allo scope creep.
4. **Pseudo-quantificazione e cold start**: importance 9.9, confidence 0.85 — numeri elicitati dall'LLM sono noti per essere non calibrati, incoerenti tra prompt e sensibili all'ancoraggio. La formula di utilità multi-termine dà rigore apparente a input rumorosi. In più il policy store e le statistiche di calibrazione sono vuoti proprio all'inizio, quando servirebbero di più.
5. **Grafo causale**: archi ipotizzati dall'LLM + propagazione multi-hop = errore composto a ogni salto. Il paper prevede la "causal hallucination" tra i failure modes (§30) ma lo spec non ha guardrail corrispondenti in §10.
6. **Concorrenza non specificata**: 10 background worker + il main loop scrivono su grafo/memoria condivisi; nessun modello di consistenza, transazionalità o idempotenza è definito.
7. **Paper — related work insufficiente**: mancano 40 anni di architetture cognitive e i lavori LLM più vicini (dettaglio in M19). Qualunque reviewer tecnico lo nota alla prima lettura.
8. **Valutazione non operazionalizzata**: 18 metriche elencate senza definizione operativa, nessun ambiente nominato, nessun protocollo statistico (dettaglio in M20).
9. **Compliance assente**: AI Act Art. 50 (obbligo di disclosure nelle interazioni vocali con umani — in applicazione dal 2 agosto 2026), GDPR (l'inferenza di motivazioni umane è profilazione di persone fisiche), consenso alle registrazioni, PSD2/SCA sui pagamenti (dettaglio in M11).

### 3.4 Sull'ipotesi centrale (posizione onesta)

Concordo parzialmente con T1, e propongo di rafforzarla distinguendo due classi di funzioni architetturali:

- **Complementi durevoli** — ciò che un modello non può fornire per definizione, per quanto diventi capace: persistenza fuori dal contesto, autorità e confini di sicurezza, budget, audit trail, attuazione nel mondo, provenance. Qui l'architettura vince sempre, e il suo valore *cresce* con la capacità del modello (più autonomia ⇒ più bisogno di controllo e verificabilità).
- **Sostituti erodibili** — funzioni che compensano debolezze attuali del modello: scaffold di pianificazione, gestione manuale del contesto, branching esplicito, alcune forme di critica strutturata. L'evidenza recente del campo (scaffold elaborati ripetutamente superati da modelli migliori con harness semplici) indica che questa classe si eroderà.

T1 così com'è non distingue le due classi ed è esposta all'obiezione "bitter lesson / gli scaffold evaporano". La versione difendibile — e scientificamente più interessante — è: *l'architettura domina per l'autonomia long-horizon (classe complementare), mentre la classe sostitutiva va progettata per essere rimossa a costo zero quando i modelli migliorano*. L'erosione stessa della classe sostitutiva è una predizione falsificabile che si può aggiungere all'Appendix B del paper. Questa distinzione (M16) rende la tesi più forte e anticipa l'obiezione più probabile in review.

Un corollario pratico: i provider di modelli stanno internalizzando pezzi di scaffold (gestione del contesto, memoria, tool use nativo). PGDCA dovrebbe progettare le interfacce in modo da *assorbire* i miglioramenti dei modelli invece di competere con essi — coerente con i requisiti interface-first dell'utente (M26).

---

## 4. Proposte in dettaglio

### Governance e sicurezza

**M1 (P0) — Governance dei goal + corrigibilità.**
Nuove non-negotiable: (a) creazione/modifica/cancellazione di meta-goal e persistent goal solo con ratifica umana esplicita — il sistema propone, l'umano ratifica; (b) log delle derive interpretative dei goal (quando il sistema ri-legge il significato di un goal, la nuova interpretazione è un evento) con review umana periodica; (c) PAUSE/STOP/ROLLBACK onorati incondizionatamente a livello controller, mai mediati dall'LLM; nessuna policy appresa può creare incentivi a resistere/ritardare l'override. Si implementa naturalmente come guardrail Tier 1 (M23).
→ Spec §65, §81 (+2 voci); Rationale §72; Paper §21, §34.

**M2 (P0) — Difesa da prompt injection.**
Dottrina architetturale "contenuto esterno = dati, mai istruzioni": tagging di provenienza su tutto ciò che entra (pagine web, email, SMS, trascrizioni vocali, output di altre AI); *taint tracking* — un'azione ad alto rischio proposta subito dopo l'ingestione di contenuto esterno recente richiede autorizzazione elevata; separazione strutturale istruzioni/dati nei prompt costruiti dal gateway; test avversariali di injection tra i required tests (Rationale §77). Motivazione: l'injection indiretta via contenuto recuperato è documentata e sistematica (Greshake et al. 2023), e PGDCA riunisce tutte e tre le condizioni della "lethal trifecta" (Willison 2025).
→ Spec: nuova sezione in security/; Rationale: nuovo principio in §72; Paper §30 (failure mode aggiuntivo: *instruction injection via ingested content*).

**M3 (P0) — Budget di autonomia consolidati.**
Un'unica sezione "bounded autonomy": tetti hard per finestra temporale su spesa, numero di comunicazioni esterne, azioni di classe irreversibile (sempre con autorizzazione fresca, mai batch), compute/token per goal. Principio *ratchet*: i budget si allargano solo per decisione umana, mai per policy learning o per decisione del sistema. I budget sono risorse first-class nel resource model, applicate dal controller (e dal Decision Supervisor, M24), non dall'LLM.
→ Spec: consolidare §51+§63; Paper §21.

### Fattibilità implementativa

**M4 (P0) — Fette verticali + scala di milestone.**
Definire una Fase 0 "Minimum Viable Loop" (MVL): loop completo goal → reconcile → plan → act (2 tool) → verify → journal → audit → policy su un dominio giocattolo, backend API-first con GUI minima (viewer del grafo + decision inbox), solo PostgreSQL, processo singolo. Ri-tagliare le fasi successive come incrementi *verticali* (ogni incremento attraversa tutti gli strati e chiude il loop su uno scenario più ricco), ognuno con uno scenario di accettazione eseguibile e la propria fetta di GUI (M25). Riformulare la Definition of Done (§82) da "AGI raggiunta" a north star + scala di milestone verificabili (allineata ai Levels 2→5 del paper §25), ciascuna di valore autonomo.
→ Spec §75, §80, §82; Rationale §75.

**M5 (P1) — Event sourcing, consistenza e replay deterministico.**
Event sourcing come unica fonte di verità: ogni scrittura (del main loop, dei worker, della GUI) è un evento nell'event store; grafo, memoria, policy store e viste della GUI sono proiezioni derivate e ricostruibili. Worker idempotenti; concorrenza ottimistica (o single-writer per aggregato); letture snapshot per i reader. Replay deterministico — event store + log completo di input/output dell'LLM ⇒ ri-simulazione fedele di qualunque decisione passata — promosso a non-negotiable: è economico da imporre dall'inizio e impossibile da retrofittare. Risolve anche il problema di concorrenza (debolezza 6).
→ Spec: nuova sezione + §26, §33, §59, §81.

**M6 (P1) — Disciplina di scoring calibrato.**
Elicitazione ordinale (critico/alto/medio/basso) mappata su bande numeriche invece di pseudo-decimali; confronti pairwise per le priorità tra goal (più robusti delle stime assolute); incertezza obbligatoria su ogni stima; gate di *sensitivity analysis* nell'arbitraggio: se la decisione si ribalta perturbando pesi a bassa confidence, la decisione non è matura ⇒ azione di information gain o escalation; metriche di calibrazione nominate esplicitamente in §44 (Brier score, Expected Calibration Error) e raccolte fin dal primo giorno; regola anti-falsa-precisione: la precisione dichiarata dell'output non può superare quella degli input.
→ Spec §5, §9, §31, §44.

**M7 (P1) — Guardrail sul grafo causale.**
Stati di validazione degli archi (HYPOTHESIZED / OBSERVED / VALIDATED) con transizioni guidate dall'evidenza; profondità di propagazione default 2–3 hop; l'incertezza si propaga moltiplicativamente lungo i cammini; le decisioni sopra una soglia d'impatto non possono poggiare su catene multi-hop non validate (⇒ prima validare l'anello debole o escalare); igiene del grafo: pruning periodico di archi stantii o mai corroborati. Collega il failure mode "causal hallucination" (Paper §30) a mitigazioni concrete.
→ Spec §10; Rationale §15.

**M8 (P1) — Guardrail sul policy learning.**
Evidenza minima (n episodi indipendenti) per la transizione CANDIDATE → ACTIVE; *shadow mode* intermedio: la policy raccomanda senza agire e si registra l'accordo controfattuale con le decisioni effettive; scope di applicabilità di default ristretto al dominio d'origine, allargato solo con evidenza di transfer; decadimento/aging (una policy non riconfermata perde confidence); regole di conflitto (policy specifica batte generale; a parità, si escala); rivalidazione periodica delle policy ad alto uso.
→ Spec §29–30.

**M9 (P1) — Cold start e curriculum.**
Pacchetto di policy seed scritte a mano (incluse le lezioni già codificate nei documenti, es. "prioritizza enabler non sostituibili ad alto impatto"); curriculum di scenari in sandbox/simulazione prima di azioni nel mondo reale; *apprentice mode*: soglie di escalation alte all'avvio, rilassate progressivamente al crescere della calibrazione misurata per dominio — autonomia guadagnata con l'evidenza, non presunta.
→ Spec: nuova sezione, collegata a M3 e M24.

**M10 (P1) — Sicurezza nell'acquisizione di tool.**
La tool discovery è un vettore di supply-chain: esecuzione sandbox-first per ogni tool scoperto o auto-costruito; verifica di provenance; credenziali least-privilege per tool (mai credenziali condivise); promozione a risk class ≥ EXTERNAL_COMMUNICATION solo con approvazione umana (via Decision Supervisor, M24); pinning e scanning delle dipendenze per i tool costruiti.
→ Spec §14–15, §50.

**M11 (P1) — Compliance e privacy.**
(a) Disclosure AI nelle interazioni vocali (AI Act, Reg. UE 2024/1689, Art. 50 — in applicazione): il sistema si presenta come AI quando chiama; (b) consenso alle registrazioni secondo la giurisdizione; (c) GDPR sui modelli Actor/Motivation: l'inferenza di motivazioni di persone identificabili è profilazione (Art. 4(4)) ⇒ base giuridica, minimizzazione, retention limitata, cancellabilità su richiesta, nessuna inferenza di categorie sensibili; (d) identità onesta in email/SMS: il sistema agisce dichiaratamente "per conto di", mai impersonificazione; (e) pagamenti progettati per SCA/PSD2: l'approvazione umana è il caso normale sopra soglia, non un'eccezione da aggirare; (f) regola etica esplicita: le motivazioni inferite non si usano mai per manipolare — solo influenza trasparente (argomenti, offerte, richieste esplicite).
→ Spec §16–24 + nuova sezione; Paper: paragrafo ethics/compliance in §34 o sezione dedicata.

### Ingegneria (seconda passata)

**M12 (P2) — Riconciliazione incrementale.**
La riconciliazione "continua di tutto" (Spec §46) è O(grafo)×LLM a ogni ciclo: insostenibile. Renderla event-driven con dirty-marking — si rivaluta solo il sottografo toccato da eventi nuovi — più sweep completi solo nei loop macro/meta (§47); `review_interval` per nodo (già in Rationale §52) generalizzato a tutti i nodi rilevanti.
→ Spec §46–47.

**M13 (P2) — Hardening del LLM gateway.**
Validazione dell'output strutturato con repair loop e fallback definiti (retry con correzione → modello alternativo → escalation); routing di modello per costo/funzione (modelli piccoli per classificazione/retrieval/estrazione, grandi per ragionamento strategico — già indicato nel Paper §31, va normato nello spec); *diversità di modello per i critic* (un critic della stessa famiglia del generatore condivide i bias: mitigazione diretta del failure mode "multi-agent confirmation" del Paper §30); log completo I/O per il replay (M5); contabilità dei costi per funzione cognitiva (quanto costa un ciclo di reconciliation? un audit? un branch?).
→ Spec §49, §52.

**M14 (P2) — Schema canonico unificato.**
Un'appendice condivisa richiamata da tutti e tre i documenti: un solo elenco di attributi delle relazioni (oggi tre varianti leggermente diverse tra Paper §8, Rationale §11, Spec §8); tassonomia dei tipi ripulita (ENABLE/ENABLES duplicati; BLOCK/OBSTRUCT/INHIBITS da fondere o distinguere con semantica esplicita); una sola forma canonica della funzione di utilità con nota "configurabile" (oggi tre formulazioni in Paper §9, Rationale §13, Spec §5); un solo piano di fasi cross-referenziato (oggi tre elenchi differenti: Paper §35, Rationale §75, Spec §75/§80).
→ tutti e tre i documenti.

**M15 (P2) — Gerarchia come ruoli, non strati obbligati.**
I 7 livelli (META-GOAL → … → ACTION) diventano ruoli semantici a profondità variabile: un goal semplice può avere 3 livelli, uno complesso 7; ciò che conta è la semantica del ruolo (stabilità decrescente, provvisorietà crescente), non il numero di strati. Evita la decomposizione burocratica di obiettivi banali.
→ Spec §3.1; Rationale §6.

**M16 (P2) — Principio sostitutivo/complementare.**
Nuovo principio di design (vedi §3.4): ogni componente è classificato come *complemento durevole* (persistenza, autorità, audit, budget, attuazione, provenance — non migreranno mai nel modello) o *sostituto erodibile* (compensa debolezze attuali del modello; va dietro interfacce, economico da rimuovere o degradare a pass-through quando i modelli migliorano). Nel paper, questa distinzione risponde frontalmente all'obiezione "gli scaffold evaporano" e produce una predizione falsificabile aggiuntiva per l'Appendix B.
→ Rationale §72+§83; Spec §2; Paper §32/§34.

**M17 (P2) — Igiene della memoria.**
TTL/archiviazione per classi di memoria; trigger di consolidamento (non solo accumulo); review su contraddizione (una contraddizione rilevata apre un item di lavoro, non resta passiva); forgetting controllato (l'oblio selettivo è una feature: memoria e grafo che crescono senza limiti degradano la precision del retrieval); metriche di qualità del retrieval misurate (precision@k sui casi d'uso reali).
→ Spec §33–36.

**M18 — Operator console.** *Assorbita da M25*: il requisito utente di un livello GUI completo estende e sostituisce questa proposta.

### Paper

**M19 (P1) — Related work e riposizionamento della novità.**
Aggiungere e differenziare i lavori mancanti. Mappa concetto → prior art:

| Concetto PGDCA | Prior art | Rapporto |
|---|---|---|
| Experience abstraction (episodio→policy) | SOAR *chunking* (Laird, Newell, Rosenbloom 1987); Reflexion (già citato) | PGDCA generalizza a policy dichiarative condizionali con confidence e ciclo di vita |
| Goal reconciliation | BDI: *intention reconsideration* (Bratman 1987; Rao & Georgeff 1995; Kinny & Georgeff 1991, bold vs cautious) | PGDCA la rende processo continuo multi-scala guidato da eventi |
| Tassonomia memoria episodica/semantica/procedurale + controllo | CoALA (Sumers et al. 2024); ACT-R (Anderson et al. 2004) | CoALA è il lavoro più vicino in assoluto: differenziazione esplicita obbligatoria |
| "LLM dentro un OS" | MemGPT (Packer et al. 2023); AIOS (Mei et al. 2024) | l'analogia OS è già pubblicata; PGDCA aggiunge autorità, goal e audit |
| Skill/capability acquisition | Voyager (Wang et al. 2023) | skill library appresa; PGDCA aggiunge capability-gap analysis e tool discovery |
| Reflection → memoria persistente | Generative Agents (Park et al. 2023) | memory stream + reflection; PGDCA aggiunge l'audit decisionale |
| LLM propone / verificatore esterno decide | LLM-Modulo (Kambhampati et al. 2024) | supporta direttamente T2 e T5 |
| Strategy branching | Tree of Thoughts (Yao et al. 2023); LATS (Zhou et al. 2024) | ricerca su albero di strategie |
| U(a) multi-attributo | MAUT (Keeney & Raiffa 1976) | fondazione teorica della formula di §9 |
| System model S_t, Env, ξ_t | POMDP / belief-state control | inquadramento formale disponibile, da dichiarare |

Enunciare la novità in una frase onesta: *l'integrazione coerente in un'unica architettura persistente di*: (1) audit che separa decision quality da outcome quality collegato al policy learning; (2) grafo causale globale con antagonismi cross-goal e opportunity cost nell'arbitraggio; (3) autorità deterministica come confine di sicurezza di prima classe; (4) capability-acquisition rate come metrica primaria; (5) la predizione falsificabile "oltre soglia, l'architettura spiega una frazione crescente della varianza long-horizon". Verificare inoltre i riferimenti esistenti: [3] è privo di autori; [9] ha un ID da controllare.
→ Paper §4 + References.

**M20 (P1) — Valutazione operazionalizzata.**
Nominare gli ambienti esistenti utilizzabili subito (GAIA, WebArena/OSWorld, τ-bench, TheAgentCompany) e proporre **PGDCA-Bench** per la persistenza multi-giorno che oggi nessun benchmark copre: ambiente simulato con seed deterministici, condizioni mutevoli, opportunità e guasti iniettati, goal in competizione, capability gap nascosti, conseguenze ritardate. Definire operativamente le 18 metriche di §27 (es.: goal preservation = drift semantico misurato tra goal ratificato e comportamento; error recurrence = tasso di ripetizione per classe d'errore della tassonomia §55; calibrazione = Brier/ECE; successo normalizzato sul costo; intervention rate umano). Protocollo statistico: n run per condizione, seed dichiarati, intervalli di confidenza, ipotesi pre-registrate (l'Appendix B è già materiale pre-registrabile). Enforcement del budget di inferenza pari tra condizioni via LLM gateway. Aggiungere eval avversariale (resistenza all'injection, M2) e di sicurezza (rispetto di budget e STOP sotto pressione, M1/M3).
→ Paper §27–28 + Appendix B.

**M21 (P2) — SGI ridimensionata.**
Mantenere la definizione di SGI ma compattarla come outlook speculativo (sottosezione in Discussion/Future Work); alleggerirla in abstract e keywords. Il neologismo attirerà critiche sproporzionate rispetto al valore che aggiunge alla tesi principale, che si regge interamente da sola.
→ Paper §2.2, §26, abstract.

**M22 (P3) — Consistenza e refusi.**
"Cloud Code" → "Claude Code" nello spec (titolo, intestazione, §80); "deterministic" chiarito come "deterministic control semantics" alla prima occorrenza in ogni documento; nota sul nome del repository: "OpenAGI" collide con il progetto di ricerca esistente agiresearch/OpenAGI (Ge et al., NeurIPS 2023) — valutare disambiguazione del nome del progetto.
→ Spec, Rationale, repo.

### Requisiti aggiunti dall'utente (rev. 2) — sicurezza, GUI, interfacce

**M23 (P0, requisito) — Guardrail a due livelli.**
**Tier 1 "Constitution"**: guardrail editabili *solo manualmente* dall'umano via GUI; il sistema non può modificarli, con enforcement a livello di storage/API — l'identità di sistema non ha il permesso di scrittura (garanzia tecnica, non convenzione) — e versionamento completo. **Tier 2 "negoziati"**: implementati dall'AI/sistema (es. derivati da audit o policy learning), editabili e discutibili uomo↔macchina nella GUI di co-decisione (M27). Precedenza: Tier 1 > Tier 2; un Tier 2 non può mai allentare un Tier 1. Ogni guardrail porta la matrice richiesta: peso di flessibilità di applicazione (hard block / soft block / warn / advisory), condizioni di applicazione specifiche, esclusioni, eccezioni — tutto editabile in GUI, riusando lo schema delle policy (Spec §30) ma in store e classe distinti. M1 (ratifica dei goal) e M3 (budget) si implementano naturalmente come guardrail Tier 1.
*Dettaglio da discutere*: propongo attivazione asimmetrica dei Tier 2 — un guardrail che *restringe* il comportamento può auto-attivarsi subito; uno che lo *amplia* richiede approvazione umana preventiva.
→ Spec: nuova sezione "Guardrail System" (security/) + §81; Rationale: nuovo principio.

**M24 (P0, requisito) — Decision Supervisor (componente di sicurezza).**
Componente distinto che controlla le decisioni dell'AI *a ogni livello* — modifiche ai goal, scelta di strategia, allocazione risorse, invocazione tool, comunicazioni esterne — non solo le azioni verso l'esterno: generalizza l'Action Gateway (Spec §66). Valuta ogni decisione contro guardrail Tier 1 + Tier 2 + lista di comportamenti consentiti/bloccati con la matrice di flessibilità. Ogni verdetto (concesso / negato / richiede umano) è un evento auditabile nel journal. Override manuale via GUI: l'umano può ribaltare un'autorizzazione respinta o revocarne una concessa; l'override è a sua volta un evento auditabile e alimenta l'audit del supervisor stesso (dove è troppo severo o troppo permissivo? per quali classi di decisione?).
→ Spec: nuova sezione "Decision Supervisor" + aggiornare §48, §66; Paper §21 (una frase).

**M25 (P0, requisito) — Livello GUI completo, frontend separato dal backend.**
Frontend web (browser) separato; backend API-first (REST + WebSocket/SSE per gli eventi live); ogni componente core espone stato e configurazione via API — "ogni componente ha una GUI". Viste richieste: (a) esploratore del grafo goal/target/fattori: nodi, relazioni tipate (supporto, necessario, enabler, contrario, bloccante, …) e pesi dei parametri (importanza, costo, probabilità, …) visualizzati ed *editabili a mano*, oppure *discutibili con l'AI* in finestra separata/dialog/frame dei dettagli del nodo; (b) editor dei guardrail Tier 1/Tier 2 con matrice di flessibilità; (c) definizione di target primario e secondari; (d) decision inbox + override del Decision Supervisor; (e) GUI di configurazione (provider LLM, tool, budget, connettori); (f) dashboard journal/audit/budget. Ogni modifica manuale è un evento con provenance `human_edit` — si integra con l'event sourcing di M5: la GUI legge proiezioni, scrive comandi. Assorbe M18.
→ Spec: nuova sezione "GUI & API Layer", moduli `api/` e `ui/` in §58, fase dedicata nel piano; Rationale: nota sulla cooperazione via GUI.

**M26 (P1, requisito) — Tool esterni interface-first (ports & adapters).**
Ogni integrazione esterna è definita da una *porta* (contratto tipizzato) con implementazioni sostituibili via adapter/bridge: **audio/telefono** = solo porta + mock ora, integrazione successiva con l'applicazione esistente (Call Happy Call) via adapter; **provider LLM** = porta provider-agnostica nel gateway, la libreria già esistente dell'utente si collega come adapter; **browser agentico** e **vault** = idem. Ogni porta con mock per i test, feature flag e una conformance test suite per validare un nuovo adapter prima dell'uso in produzione. Coerente con M16: i sostituti erodibili stanno dietro interfacce.
→ Spec: rafforzare §16, §17, §20 + sottosezione "Ports & Adapters" in §58.

**M27 (P1, requisito) — Componente + GUI di co-decisione in itinere.**
Componente "Deliberation" (in collaboration/): l'umano può aprire in qualsiasi momento una decisione, una strategia o un nodo del grafo e ridiscuterla con il sistema; il sistema risponde con il rationale ricostruito dal journal (evidenze, alternative considerate, stime, policy applicate); l'esito — conferma, modifica, annullamento — è un evento che può innescare replanning. Bidirezionale: anche il sistema apre thread di discussione nella stessa GUI (gli escalation packet di Spec §69 diventano thread). Le discussioni sono salvate come episodi e alimentano audit e policy learning.
→ Spec: estendere §21, §69 + collaboration/ in §58; GUI in M25.

**M28 (P1, requisito) — Skills e MCP server importabili.**
Il sistema deve poter usare capacità importate in forma pacchettizzata, al pari dei runtime agentici moderni (es. Claude Code, Hermes):
(a) **Skill package** — conoscenza procedurale autocontenuta: manifest (nome, descrizione, trigger di applicabilità, risk class, versione, provenance) + istruzioni + script/risorse opzionali. Le skill importate si registrano nella memoria procedurale/policy con provenance `imported` (distinta dalle skill *apprese* via Skill Acquisition, Spec §72) e vengono caricate on demand (progressive disclosure) per rispettare i budget di contesto (§37).
(b) **MCP server** (Model Context Protocol) — il tool registry agisce da client MCP: all'import enumera tool e risorse del server, li mappa in nodi del Tool Graph con schemi e stime di costo/latenza/affidabilità, assegna le risk class, esegue i conformance test in sandbox e registra. Un server MCP è un tipo di adapter dietro le porte dei tool (M26).
Sicurezza (per entrambi): sandbox-first, verifica di provenance, credenziali least-privilege, promozione a risk class ≥ EXTERNAL_COMMUNICATION solo con approvazione umana via Decision Supervisor (M10/M24); descrizioni e output dei tool sono contenuto non fidato (M2 — il *description poisoning* è un attacco noto agli ecosistemi MCP); versioni pinnate, un update ri-innesca la validazione. Gestione dalla GUI di configurazione (M25): import, enable/disable, ispezione, permessi. La tool discovery (Spec §71) include i registry di skill/MCP tra i canali di acquisizione di capacità.
→ Spec: nuova sezione "Imported Skills and MCP Servers" + §14–15, §58, §60–61; Rationale: sezione interface-first; GUI in M25.

---

## 5. Cosa NON propongo di cambiare

La separazione multi-store della memoria; la distinzione decision/outcome; l'autorità deterministica e il design vault/secure-handles; la posizione su CAPTCHA (no bypass, human-in-the-loop); i sub-goal come ipotesi falsificabili; l'ablation study con budget controllato; la struttura a tre documenti con il rationale come contratto anti-erosione. Sono corretti così.

---

## 6. Riferimenti citati nell'analisi

Da verificare puntualmente (ID e venue) in fase di applicazione di M19.

- Laird, J. E., Newell, A., Rosenbloom, P. S. (1987). *SOAR: An architecture for general intelligence.* Artificial Intelligence 33(1).
- Anderson, J. R., et al. (2004). *An Integrated Theory of the Mind* (ACT-R). Psychological Review 111(4).
- Bratman, M. (1987). *Intention, Plans, and Practical Reason.* Harvard University Press.
- Rao, A. S., Georgeff, M. P. (1995). *BDI Agents: From Theory to Practice.* ICMAS.
- Kinny, D., Georgeff, M. (1991). *Commitment and Effectiveness of Situated Agents.* IJCAI.
- Sumers, T., Yao, S., Narasimhan, K., Griffiths, T. (2024). *Cognitive Architectures for Language Agents.* TMLR; arXiv:2309.02427.
- Packer, C., et al. (2023). *MemGPT: Towards LLMs as Operating Systems.* arXiv:2310.08560.
- Mei, K., et al. (2024). *AIOS: LLM Agent Operating System.* arXiv:2403.16971.
- Wang, G., et al. (2023). *Voyager: An Open-Ended Embodied Agent with Large Language Models.* arXiv:2305.16291.
- Park, J. S., et al. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* UIST; arXiv:2304.03442.
- Kambhampati, S., et al. (2024). *LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks.* ICML; arXiv:2402.01817.
- Yao, S., et al. (2023). *Tree of Thoughts: Deliberate Problem Solving with Large Language Models.* NeurIPS; arXiv:2305.10601.
- Zhou, A., et al. (2024). *Language Agent Tree Search (LATS).* ICML; arXiv:2310.04406.
- Keeney, R. L., Raiffa, H. (1976). *Decisions with Multiple Objectives.* Wiley.
- Greshake, K., et al. (2023). *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec; arXiv:2302.12173.
- Willison, S. (2025). *The lethal trifecta for AI agents.* simonwillison.net.
- Xia, C. S., et al. (2024). *Agentless: Demystifying LLM-based Software Engineering Agents.* arXiv:2407.01489. (evidenza dell'erosione degli scaffold)
- Ge, Y., et al. (2023). *OpenAGI: When LLM Meets Domain Experts.* NeurIPS; arXiv:2304.04370. (collisione di nome col repository)
- Mialon, G., et al. (2023). *GAIA: A Benchmark for General AI Assistants.* arXiv:2311.12983.
- Zhou, S., et al. (2023). *WebArena.* arXiv:2307.13854. · Xie, T., et al. (2024). *OSWorld.* arXiv:2404.07972. · Yao, S., et al. (2024). *τ-bench.* arXiv:2406.12045. · Xu, F., et al. (2024). *TheAgentCompany.* arXiv:2412.14161.
- Regolamento (UE) 2024/1689 (AI Act), Art. 50. · Regolamento (UE) 2016/679 (GDPR), Artt. 4(4), 22.

---

## 7. Processo di applicazione delle modifiche approvate

1. L'utente approva / discute / respinge ogni voce; la tabella di stato (§1) viene aggiornata a ogni decisione.
2. Le voci approvate si applicano ai documenti: i due `.md` con edit diretti; il paper `.docx` con *tracked changes* (revisionabili e accettabili/rifiutabili in Word), rigenerando il mirror `.md` dopo ogni modifica.
3. Commit incrementali per gruppi di modifiche approvate, sul branch `claude/pgdca-analysis-feedback-ccn86f`.
4. Verifica finale: validazione del `.docx`, render PDF di controllo, coerenza cross-documento dei termini canonici (M14).

**Stato**: passi 1–2 completati con la v1.0; decisioni registrate il 30/08/2026; v1.1 applicata ai due `.md` (nuove sezioni + numerazione scalata) e al paper `.docx` come tracked changes da accettare/rifiutare in Word.
