#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
SCRIPT_NAME="$(basename "$0")"

# 1) Crear carpetas base
for d in src tests docs config scripts data logs assets output; do
  mkdir -p "$ROOT/$d"
done

# 2) Mover directorios principales
if [ -d "$ROOT/app" ]; then
  echo "Mover app/ → src/app/"
  mv "$ROOT/app" "$ROOT/src/app"
fi

for d in test tests; do
  if [ -d "$ROOT/$d" ]; then
    echo "Mover $d/ → tests/"
    mv "$ROOT/$d" "$ROOT/tests"
  fi
done

# 3) Mover archivos raíz por extensión
declare -A MAP=(
  ["docs"]="*.md *.rst"
  ["config"]="*.json *.toml *.ini"
  ["scripts"]="*.sh *.bat *.spec run_*.py"
  ["data"]="*.xlsx *.xls *.csv *.db *.sqlite"
  ["logs"]="*.log"
  ["assets"]="*.png *.jpg *.jpeg *.svg *.pdf"
)
for dir in "${!MAP[@]}"; do
  for pat in ${MAP[$dir]}; do
    shopt -s nullglob
    for f in $ROOT/$pat; do
      echo "  → ${f##*/} → $dir/"
      mv "$f" "$ROOT/$dir/"
    done
    shopt -u nullglob
  done
done

# 4) Mover todo lo que quede en raíz (excepto .git, .venv y carpetas nuevas) a output/
for f in "$ROOT"/*; do
  name="${f##*/}"
  if [[ "$name" == "$SCRIPT_NAME" || "$name" == ".git" || "$name" == ".venv" ||
        "$name" == "src" || "$name" == "tests" || "$name" == "docs" ||
        "$name" == "config" || "$name" == "scripts" || "$name" == "data" ||
        "$name" == "logs" || "$name" == "assets" || "$name" == "output" ]]; then
    continue
  fi
  if [ -d "$f" ]; then
    echo "Mover carpeta $name → output/"
    mv "$f" "$ROOT/output/"
  elif [ -f "$f" ]; then
    echo "Mover archivo $name → output/"
    mv "$f" "$ROOT/output/"
  fi
done

echo "✅ Repositorio reorganizado:"
tree -L 2 -C "$ROOT"
