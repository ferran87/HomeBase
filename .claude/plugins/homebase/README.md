# HomeBase Plugin

Project-level Claude Code skills and commands for HomeBase.

## Skills (auto-triggered)
- **voice-pipeline** — triggers when working on `claude_voice.py` or the voice route
- **db-migration** — triggers when adding tables or running Alembic commands

## Commands (slash commands)
- `/dev` — print dev environment startup commands
- `/new-feature <name>` — scaffold a new feature module (route + model + service)

## Agents
- **voice-tester** — tests Claude classification accuracy with sample text payloads
