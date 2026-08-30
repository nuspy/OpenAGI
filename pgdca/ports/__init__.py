"""External-world ports (interface-first, spec: Ports and Adapters).

Each module defines: the typed Protocol, structured result types, a
mock adapter, and a conformance suite. Real adapters are implemented in
local development (see docs/LOCAL_INTEGRATIONS.md) and plug in via
`pgdca.tools.external.register_external_ports` without touching the
core.
"""
