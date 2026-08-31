"""Product scouting: turn a "buy X" target into real, comparable options.

The last mile before the owner's mountain scenario runs end to end: a
sub-target tagged to buy something ("find best buys: climbing boots")
must not be abstract. With the browser connected the system searches the
web, extracts a handful of real options (name, price, characteristics,
url), and presents them as CARDS in a consensus thread. The owner picks
or discusses; the choice weaves a "Paga <item>" sub-target carrying the
merchant, amount and method - which then flows through the normal gated
payment path (Supervisor approval + your 2FA), nothing bypassed.

Page content is untrusted data (browser doctrine). No option is acted on
without the owner's pick; the payment itself stays FINANCIAL and gated.
"""
from __future__ import annotations

import re

from .config import Config
from .domain import NodeKind, NodeStatus, RelType, ValidationStatus, edge, node
from .events import Actor, Ev

BUY_RE = re.compile(r"buy|purchase|acquist|comprar|find best|miglior|"
                    r"best buys?", re.I)


class ScoutingEngine:
    def __init__(self, runtime, gateway, graph, deliberation,
                 registry, config: Config | None = None, budgets=None):
        self.runtime = runtime
        self.gateway = gateway
        self.graph = graph
        self.deliberation = deliberation
        self.registry = registry
        self.budgets = budgets
        self.config = config or Config()

    # ---------------------------------------------------------- triggers
    def _browser(self):
        # scouting needs a real browser tool enabled; None otherwise
        try:
            spec = self.registry.spec("browser.navigate")
        except KeyError:
            return None
        return spec if spec.enabled else None

    def _already(self, node_id: str) -> bool:
        for th in self.deliberation.projection.for_subject("node", node_id):
            first = th["messages"][0] if th["messages"] else {}
            if (first.get("packet") or {}).get("checkpoint") == "scouting":
                return True
        return False

    def _is_buy(self, n: dict) -> bool:
        if n["props"].get("intent") == "buy":
            return True
        return bool(BUY_RE.search(n["label"]))

    def candidates(self) -> list[dict]:
        out = [t for t in self.graph.by_kind(
            NodeKind.TARGET, NodeKind.SUB_TARGET, status=NodeStatus.ACTIVE)
            if self._is_buy(t) and not self.graph.in_edges(t["id"])
            and not self._already(t["id"])]
        out.sort(key=lambda t: (-float(t["props"].get("priority", 0.5)),
                                t["id"]))
        return out

    # -------------------------------------------------------------- step
    def step(self) -> list[dict]:
        if not self.config.scouting_enabled or self._browser() is None:
            return []
        opened = []
        for t in self.candidates()[:self.config.scouting_max_per_cycle]:
            options = self.scout(t)
            if options:
                opened.append(self._open_thread(t, options))
        return opened

    def scout(self, t: dict) -> list[dict]:
        """Gather real options. The model proposes searches; the browser
        fetches (untrusted); the model turns pages into structured options."""
        excerpts = []
        plan = self.gateway.ask("scout", {
            "target": {"id": t["id"], "label": t["label"]},
            "phase": "search",
            "instruction": "propose up to 3 web searches to compare real "
                           "products for this target, as search_web actions "
                           "with params.url set to a search URL"})
        for h in plan.hypotheses:
            if h.action_name == "search_web" and h.params.get("url"):
                res = self.registry.execute("browser.navigate",
                                            {"url": h.params["url"]})
                if res.status == "ok":
                    obs = res.observation or {}
                    excerpts.append({"url": obs.get("url"),
                                     "text": obs.get("content_excerpt")
                                     or obs.get("title", "")})
                if len(excerpts) >= self.config.scouting_max_pages:
                    break
        picks = self.gateway.ask("scout", {
            "target": {"id": t["id"], "label": t["label"]},
            "phase": "extract",
            "pages": excerpts,   # untrusted data
            "instruction": "from these pages propose 3-5 concrete options as "
                           "propose_option actions with params: label, price "
                           "(number), currency, merchant, url, image_url, "
                           "characteristics (short string), and a rationale"})
        options = []
        for h in picks.hypotheses:
            p = h.params
            if h.action_name == "propose_option" and p.get("label"):
                options.append({
                    "label": str(p["label"]),
                    "price": float(p.get("price", 0) or 0),
                    "currency": str(p.get("currency", "EUR")),
                    "merchant": str(p.get("merchant", "")),
                    "url": str(p.get("url", "")),
                    "image_url": str(p.get("image_url", "")),
                    "characteristics": str(p.get("characteristics", "")),
                    "rationale": h.rationale, "trust": "untrusted"})
        return options

    def _open_thread(self, t: dict, options: list[dict]) -> dict:
        reason = (f"Ho trovato {len(options)} opzioni per '{t['label']}'. "
                  "Guardale (prezzo, caratteristiche, foto), poi scegline una "
                  "risolvendo come modificato con {\"chosen\": <indice da 0>} "
                  "— creo il pagamento (che passa dalla tua approvazione e "
                  "dal codice 2FA). Oppure discutiamone in chat.")
        return self.deliberation.open_system(
            reason,
            {"checkpoint": "scouting", "node_id": t["id"], "options": options,
             "cycle": self.runtime.cycle},
            subject={"kind": "node", "id": t["id"]})

    # ------------------------------------------------------------- choose
    def apply(self, node_id: str, options: list[dict], chosen: int,
              actor: Actor) -> list[dict]:
        parent = self.graph.node(node_id)
        if parent is None:
            raise KeyError(node_id)
        if not (0 <= chosen < len(options)):
            raise ValueError(f"scelta fuori intervallo: {chosen}")
        opt = options[chosen]
        # ground the chosen option so cognition and the audit trail have it
        sid = self.runtime.next_id("tgt")
        self.runtime.emit(Ev.NODE_ADDED, {"node": node(
            sid, NodeKind.SUB_TARGET,
            f"Paga {opt['label']} ({opt['price']} {opt['currency']})",
            priority=float(parent["props"].get("priority", 0.7)),
            spawned_by=node_id, intent="pay", merchant=opt["merchant"],
            amount=opt["price"], currency=opt["currency"],
            method_handle="", url=opt["url"], item=opt["label"])}, actor)
        self.runtime.emit(Ev.EDGE_ADDED, {"edge": edge(
            self.runtime.next_id("se"), sid, node_id, RelType.SUPPORT,
            ValidationStatus.VALIDATED, f"scouting_choice:{node_id}",
            importance=float(parent["props"].get("priority", 0.7)),
            confidence=0.9)}, actor)
        return [{"type": "option_chosen", "id": sid, "item": opt["label"],
                 "merchant": opt["merchant"], "amount": opt["price"]}]
