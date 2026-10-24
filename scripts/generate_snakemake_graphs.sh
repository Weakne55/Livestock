#!/usr/bin/env bash
# Только визуализация: построение rulegraph/DAG Snakemake без выполнения правил.
set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Использование:
  bash scripts/generate_snakemake_graphs.sh RUN_CONFIG.yaml [SAMPLES.tsv] [METADATA.tsv]

Аргументы 2 и 3 переопределяют samples/metadata из YAML, не меняя сам YAML.
Пригодится, когда исторические TSV были перенесены в резервную копию.
Результат: docs/images/snakemake_rulegraph.svg и docs/images/snakemake_dag.svg.
EOF
}

if [[ $# -lt 1 || $# -gt 3 ]]; then usage; exit 2; fi
if ! command -v snakemake >/dev/null 2>&1; then
    echo 'ОШИБКА: snakemake не найден. Активируйте livestock-snakemake.' >&2
    exit 1
fi
if ! command -v dot >/dev/null 2>&1; then
    echo 'ОШИБКА: dot (Graphviz) не найден. Установите Graphviz, например conda install -c conda-forge graphviz.' >&2
    exit 1
fi

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_file() {
    if [[ ! -f "$1" ]]; then
        echo "ОШИБКА: файл не найден: $1" >&2
        exit 1
    fi
    realpath "$1"
}

config="$(resolve_file "$1")"
overrides=()
if [[ $# -ge 2 ]]; then
    samples="$(resolve_file "$2")"
    overrides+=("samples=$samples")
fi
if [[ $# -eq 3 ]]; then
    metadata="$(resolve_file "$3")"
    overrides+=("metadata=$metadata")
fi

cd "$repo"
mkdir -p docs/images
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT

args=(--snakefile workflow/Snakefile --configfile "$config" --cores 1 --forceall)
if (( ${#overrides[@]} > 0 )); then
    args+=(--config "${overrides[@]}")
fi

# Вывод DOT направлен в файл. Ошибки остаются в отдельном журнале.
for graph_type in rulegraph dag; do
    echo "Создание $graph_type ..."
    if ! snakemake "${args[@]}" "--$graph_type" > "$scratch/$graph_type.dot" 2> "$scratch/$graph_type.err"; then
        cat "$scratch/$graph_type.err" >&2
        echo "ОШИБКА: Snakemake не смог построить $graph_type. Файлы проекта не менялись." >&2
        exit 1
    fi
    if ! grep -qE '^[[:space:]]*(strict[[:space:]]+)?digraph[[:space:]]' "$scratch/$graph_type.dot"; then
        echo "ОШИБКА: Snakemake вернул не DOT для $graph_type." >&2
        head -n 20 "$scratch/$graph_type.dot" >&2
        exit 1
    fi
    if ! dot -Tsvg -Grankdir=LR -Gnodesep=0.25 -Granksep=0.55 \
        "$scratch/$graph_type.dot" -o "$scratch/$graph_type.svg"; then
        echo "ОШИБКА: Graphviz не смог создать SVG для $graph_type." >&2
        exit 1
    fi
done

# Заменяем изображения только после успешной генерации обоих файлов.
for graph_type in rulegraph dag; do
    mv -f -- "$scratch/$graph_type.svg" "docs/images/snakemake_${graph_type}.svg"
    echo "СОЗДАН: docs/images/snakemake_${graph_type}.svg"
done

echo 'Готово. Перед git add убедитесь, что SVG не содержат непубличные идентификаторы образцов.'
