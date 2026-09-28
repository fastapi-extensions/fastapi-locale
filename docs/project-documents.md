# Project documents

These are the engineering documents for fastapi-locale, in the order they are written. Each one builds on
the one before it. Requirement IDs from the SRS (for example `LOC-07`) are used throughout, so every
design decision and test can be traced back to a need.

| Area | Document | Status |
| --- | --- | --- |
| Research | [Existing libraries](research/existing-libraries.md) | Approved |
| Requirements | [Software Requirements Specification](requirements/software-requirements-specification.md) | Approved |
| Modeling | [Use case model](modeling/use-case-model.md) | Approved |
| Modeling | [Domain model](modeling/domain-model.md) | Approved |
| Architecture | [Software architecture](architecture/software-architecture.md) | Approved |
| Architecture | [Architecture decision records](adr/README.md) | Accepted, except ADR-0009 |
| Design | [Detailed design](design/detailed-design.md) | Approved |
| Verification | [Test plan](testing/test-plan.md) | Approved |
| Development | [Development guide](development/development-guide.md) | Approved |

User-facing documentation (quick start, guides, API reference) is in the same site, under the user guide.

## Diagrams

All diagrams are UML, written in [PlantUML](https://plantuml.com). Sources are in
`docs/diagrams/` and share one style file, `diagrams/include/style.iuml`. The rendered SVG files are
committed next to their sources, so they display on GitHub and in the docs site without extra tools.

| Diagram | UML type | Used in |
| --- | --- | --- |
| `use-case` | Use case | Use case model |
| `domain-model` | Class (conceptual) | Domain model |
| `state-request-locale`, `state-catalog-store` | State machine | Domain model |
| `system-context` | Component (context) | Architecture |
| `components` | Component | Architecture |
| `deployment` | Deployment | Architecture |
| `sequence-startup`, `sequence-request`, `sequence-validation-error`, `sequence-lazy-text` | Sequence | Architecture |
| `activity-locale-resolution`, `activity-accept-language`, `activity-message-lookup`, `activity-catalog-workflow` | Activity | Architecture |
| `class-design` | Class (design) | Detailed design |
| `module-dependencies` | Package / component | Detailed design |

To change a diagram, edit its `.puml` file and render all diagrams with Docker:

```sh
scripts/render-diagrams.sh
```

The script uses a pinned PlantUML image, so everyone gets the same output. Commit the `.puml` and `.svg`
files together.
