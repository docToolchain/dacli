# Development Plan: Dokumentation nach Bug-Fixes aktualisieren

*Generated on 2026-01-31 by Vibe Feature MCP*
*Workflow: [minor](https://mrsimpson.github.io/responsible-vibe-mcp/workflows/minor)*

## Goal

Dokumentation (Specs, User Manual) aktualisieren, um die Änderungen aus den letzten 12 geschlossenen Issues zu reflektieren:
- Parameter-Validierung dokumentieren (#220)
- CLI-Warnungen dokumentieren (#225, #226)
- insert 'after' Verhalten klarstellen (#229)
- Element-Typen vervollständigen

## Key Decisions

- **Workflow**: minor - Dokumentationsänderungen ohne Code-Änderungen
- **Betroffene Dateien**:
  - `src/docs/50-user-manual/20-mcp-tools.adoc`
  - `src/docs/spec/02_api_specification.adoc`
  - `src/docs/spec/06_cli_specification.adoc`
  - `src/docs/spec/03_acceptance_criteria.adoc`

## Notes

Issues, die KEINE Dokumentationsänderungen erfordern: #218, #219, #216, #217, #223, #224, #227 (Implementation-Bugs oder Meta-Issues)

## Explore

### Phase Entrance Criteria
- [x] Initiale Phase - keine Entrance Criteria

### Tasks
- [x] Issues analysieren und kategorisieren
- [x] Betroffene Dokumentationsdateien identifizieren
- [x] Konkrete Änderungen definieren

### Completed
- [x] Created development plan file
- [x] 12 Issues analysiert
- [x] 4 Dateien als betroffen identifiziert

## Implement

### Phase Entrance Criteria
- [x] Alle betroffenen Dokumentationsdateien sind identifiziert
- [x] Konkrete Änderungen sind definiert
- [x] Keine offenen Fragen

### Tasks
*All completed*

### Completed
- [x] 20-mcp-tools.adoc: Parameter-Constraints und 'after' Klarstellung
- [x] 02_api_specification.adoc: Parameter-Constraints und plantuml hinzufügen
- [x] 06_cli_specification.adoc: Warnungen und 'after' Klarstellung
- [x] 03_acceptance_criteria.adoc: Neue Szenarien hinzufügen

## Finalize

### Phase Entrance Criteria
- [ ] Alle Dokumentationsänderungen sind umgesetzt
- [ ] Keine Syntaxfehler in den Dateien

### Tasks
- [ ] Version bump (Patch)
- [ ] Commit erstellen
- [ ] PR erstellen

### Completed
*None yet*


---
*This plan is maintained by the LLM. Tool responses provide guidance on which section to focus on and what tasks to work on.*
