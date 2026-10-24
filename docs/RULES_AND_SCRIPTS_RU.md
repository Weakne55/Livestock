# Правила Snakemake и вспомогательные скрипты

Документ описывает **реальные файлы текущей версии**, чтобы можно было быстро найти нужную стадию и понять, какую часть программы изменять. Для запуска обычной партии вручную вызывать `.smk` не нужно — их подключает `workflow/Snakefile`.

## 1. Управление workflow

- `workflow/Snakefile` — читает YAML, загружает референсы и манифест, формирует группы highcov/lowpass, подключает девять модулей, определяет `rule all`, пути `WORK`, `RESULTS`, `CACHE`, общий SIF и ограничения ресурсов.
- `workflow/lib/manifest.py` — преобразует `samples.tsv` в sequencing units и образцы; проверяет обязательные поля, уникальность, согласованность формата входа, принадлежность к виду/референсу, запрет разных библиотек одного образца.

## 2. Правила `workflow/rules/`

| Файл | Правила | Что делают |
|---|---|---|
| `reference.smk` | `prepare_reference`, `index_reference` | Копируют FASTA в кеш, строят `.fai`, проверяют contigs, создают индексы `bwa` или `bwa-mem2` |
| `preprocessing.smk` | `trim_fastq` | `fastp`: парные очищенные FASTQ и отчёты QC |
| `alignment.smk` | `align_lane` | Однократное выравнивание каждой lane, `@RG`, поток `bwa mem | samtools view` в BAM |
| `bam_processing.smk` | `canonical_bam` | FASTQ-ветка: `merge/collate/fixmate/sort/markdup`; BAM/CRAM-ветка: проверка и импорт; всегда BAM+BAI |
| `bam_qc.smk` | `bam_qc` | `samtools flagstat`, `samtools stats`, `mosdepth` по окнам 1 Мб и порогам 1/5/10/20× |
| `calling_highcov.smk` | `call_highcov_contig` | `bcftools mpileup/call` независимо для каждого highcov-образца и каждой хромосомы; BCF+CSI |
| `calling_lowpass.smk` | `call_lowpass_contig` | То же по хромосомам, но отдельно для каждого lowpass-образца |
| `vcf_processing.smk` | `highcov_vcf`, `lowpass_vcf`, `highcov_stats`, `lowpass_stats` | concat, norm, highcov `LowQual`, VCF/TBI, `bcftools stats` |
| `reporting.smk` | `multiqc` | Сводный HTML из QC-отчётов |

## 3. `scripts/`: что и когда используется

### Нужны при обычном анализе

| Скрипт | Назначение | Кто вызывает |
|---|---|---|
| `create_bam.sh` | Построение итогового BAM/BAI, импорт BAM/CRAM | `canonical_bam` |
| `check_alignment.py` | Проверка заголовков готового BAM/CRAM | `create_bam.sh` |
| `validate_reference_fai.py` | Сверка списка хромосом с индексом FASTA | `prepare_reference` |
| `validate_manifest.py` | Проверяет YAML/TSV, наличие входов и метаданных | Пользователь до запуска; также `run_vavilov.sh` |
| `check_config.py` | Проверяет наличие контейнера и правила хранения данных | Пользователь или `run_vavilov.sh` |
| `check_slurm_limits.py` | Сверяет времена задач с ограничением Slurm | Пользователь / `run_vavilov.sh` на Vavilov |
| `run_vavilov.sh` | Запускает Snakemake-контроллер на Vavilov с `flock` | `launch_vavilov.sh` |
| `launch_vavilov.sh` | Запускает контроллер через `nohup`, сообщает PID и файл лога | Пользователь на `vavilov0` |

### Для установки, диагностики и тестирования

| Скрипт | Когда нужен |
|---|---|
| `build_image.sbatch` | Сборка SIF на настроенном Slurm-кластере (в текущем виде — Vavilov) |
| `check_image.sh` | Проверка доступности SIF и инструментов внутри него |
| `benchmark_report.py` | Сводка времени/RSS завершённых правил по `--run-id` или `--results-dir` |
| `generate_positive_demo.py` | Создание синтетического теста с заранее известными вариантами |
| `check_positive_demo.py` | Проверка VCF после завершения синтетического теста |
| `download_manifest.py` | Скачивание публичных ENA/NCBI файлов по TSV с MD5-проверкой |
| `downloads.sbatch` | Запуск скачивания данных через Slurm |
| `prepare_ena_real_run.py` | Специализированная подготовка пилота на 3 публичных SRR, **не** универсальный конструктор новых образцов |
| `prepare_perf_run.py` | Экспериментальный запуск v0.5 из другой конфигурации; подменяет каталоги и выставляет пилотные лимиты RAM, **не** рекомендован для больших когорт |
| `diagnose_slurm.sh` | Короткая диагностика конфигурации Slurm, если файл ещё присутствует в репозитории |
| `create_layout.sh`, `generate_demo.py` | Устаревшие демонстрационные утилиты; если удалены при очистке, восстанавливать не требуется |

## 4. Профили

- `profiles/local/` — локальный Snakemake.
- `profiles/slurm-example/` — переносимый *шаблон* для нового кластера; его нужно адаптировать.
- `profiles/vavilov/` — исходный рабочий Slurm-профиль.
- `profiles/vavilov-fast/` — протестированный более параллельный профиль, но лимиты памяти для больших когорт не проверены.

## 5. Тесты

В каталоге `tests/` находятся `test_manifest.py`, `test_modular.py`, `test_performance_profile.py`, `test_project_structure.py`, `test_real_production.py`. Они проверяют API манифеста, структуру правил, профили ресурсов, скрипты запуска, ограничения и настройки сборки. Запуск:

```bash
python -m unittest discover -s tests -v
```

**26 unit-тестов** успешно выполнялись в публикационной копии, но полноценный end-to-end тест на новом HPC — отдельный шаг.
