#!/usr/bin/env bash
# Render every PlantUML source under docs/diagrams to SVG with a pinned PlantUML image,
# so the output is the same on every machine and in CI.
set -euo pipefail

PLANTUML_IMAGE="plantuml/plantuml:1.2026.8"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORMAT="${1:-svg}"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "${ROOT}/docs/diagrams:/diagrams" \
  --workdir /diagrams \
  "${PLANTUML_IMAGE}" \
  -t"${FORMAT}" -failfast2 -nometadata ./*.puml
