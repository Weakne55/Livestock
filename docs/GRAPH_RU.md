# Граф зависимостей Snakemake

В основном `README.md` размещены **две разные визуализации**:

- **Mermaid** — нарисованная в Markdown схема, объясняющая общий алгоритм обработки FASTQ/BAM/CRAM.
- **Snakemake rulegraph и DAG** — графы, построенные автоматически по `workflow/Snakefile`, `.smk`-правилам и выбранным образцам.

## Чем отличаются rulegraph и DAG

`--rulegraph` показывает виды правил и зависимости между ними; его удобно читать на GitHub. `--dag` разворачивает каждое правило по конкретным wildcards (вид, образец, библиотека, lane, хромосома). Такой граф гораздо подробнее, поэтому в README дана ссылка на полный SVG.

Графы **зависят от конкретной YAML-конфигурации и TSV-манифеста**. Они не фиксированы для всех возможных видов, хромосом и образцов.

## Требования

Нужно активное окружение `livestock-snakemake`, Snakemake 9 и утилита `dot` из Graphviz:

```bash
conda activate livestock-snakemake
command -v snakemake
command -v dot
```

Если `dot` отсутствует, установите Graphviz в подходящее окружение (или используйте системный модуль кластера):

```bash
conda install -c conda-forge graphviz
```

На Vavilov команду запускают из `~/livestock`, **без `srun`/`sbatch`**: граф вычисляется на управляющем узле, тяжёлые задания не отправляются в Slurm.

## Создать граф для любого собственного запуска

Сначала подготовьте валидный `config/my_run.local.yaml` и TSV, как описано в [инструкции по запуску](INSTALL_RU.md). Затем:

```bash
cd ~/livestock
bash scripts/generate_snakemake_graphs.sh config/my_run.local.yaml
```

Для одного и того же YAML можно явно передать другие TSV (не изменяя YAML):

```bash
bash scripts/generate_snakemake_graphs.sh \
  config/my_run.local.yaml \
  /path/to/samples.tsv \
  /path/to/metadata.tsv
```

### Граф для завершённого пилота октября 2026 года

После очистки GitHub-репозитория пилотные YAML и TSV **перенесены в резервную копию**. Чтобы воспроизвести DAG по трём публичным образцам, выполните:

```bash
cd ~/livestock
conda activate livestock-snakemake

BACKUP="$HOME/livestock_github_backup_20261024T080358Z"

bash scripts/generate_snakemake_graphs.sh \
  "$BACKUP/config/real_sif_perf_20261023.yaml" \
  "$BACKUP/config/real_sif_20261022_samples.tsv" \
  "$BACKUP/config/real_sif_20261022_metadata.tsv"
```

Скрипт использует `--config` для временного переопределения архивированных путей к TSV. Исходные конфигурации, реальные BAM/VCF и вычислительные правила не меняются. Если резервная копия называется иначе, замените `BACKUP`.

## Результаты

```text
docs/images/
├── snakemake_rulegraph.svg   # компактный граф правил, показан в README
└── snakemake_dag.svg         # подробный DAG заданий, ссылка из README
```

**Важно:** изображений не будет в GitHub, пока вы не выполните генерацию и не добавите оба SVG в Git. Это не заранее нарисованный граф: он должен быть построен Snakemake из рабочего репозитория.

```bash
git add README.md docs/GRAPH_RU.md scripts/generate_snakemake_graphs.sh \
  docs/images/snakemake_rulegraph.svg docs/images/snakemake_dag.svg

git diff --cached --check
```

Перед публикацией проверьте, что графы построены на **публичных** образцах: подписи wildcards могут содержать ID реальных образцов и другие элементы конфигурации, которые нельзя раскрывать.

## Что делают ключи генерации

- `--dag`: печатает в стандартный вывод полный граф конкретных заданий в формате DOT.
- `--rulegraph`: печатает более компактный граф правил.
- `--forceall`: включает в граф уже выполненные стадии, даже если выходы существуют.
- `dot -Tsvg`: переводит текстовый DOT в изображение SVG для GitHub.

`--dag` и `--rulegraph` **не запускают вычислительные задания**, в том числе при использовании `--forceall`: здесь это только построение графа.
