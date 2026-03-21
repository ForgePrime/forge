# _future/ — Kod przygotowany na przyszłe tryby pracy

Ten katalog zawiera moduły które NIE SA aktywnie używane w obecnym trybie CLI.
Zostały przeniesione z `core/` żeby nie zaciemniać aktywnego kodu.

## Zawartość

### llm/
Pełna warstwa abstrakcji LLM: providery (Anthropic, OpenAI, Ollama, Claude Code),
kontrakty (planning, task execution, review), registry. Używane przez `forge-api/`
(platform mode — serwer API). W trybie CLI Forge korzysta z Claude Code jako LLM
i nie potrzebuje bezpośredniej integracji z providerami.

### context_assembler.py
Token-budgeted context assembly engine z priorytetyzacją sekcji (P1-P8).
Odpowiednik `cmd_context()` z `core/pipeline.py`, ale ze zarządzaniem rozmiarem
kontekstu. Przydatny przy mniejszych modelach lub bardzo dużych projektach.

## Kiedy wrócić do tych modułów

- Multi-agent mode z mniejszymi modelami (Haiku) — token budgeting z context_assembler
- Platform mode (forge-api/) — cała warstwa LLM
- Duże projekty (100+ guidelines) — context overflow management

## Jak reaktywować

1. Przenieś potrzebne moduły z powrotem do `core/`
2. Zaktualizuj importy (były: `from core.llm.xxx import ...`)
3. Zsynchronizuj z aktualnym stanem `core/pipeline.py`
