# Требования к установке Livestock

## Где выполняются задачи

- **Управляющий узел / локальная машина:** Linux, Python 3.11, Conda/Miniforge, Snakemake 9.x, PyYAML. Для Slurm требуются `snakemake-executor-plugin-slurm` и `snakemake-executor-plugin-slurm-jobstep`; полный список — `manager/environment.yaml`.
- **Вычислительный узел:** доступный Apptainer/Singularity, настроенный Slurm (для кластера), чтение общих FASTQ, FASTA и SIF, запись результатов.
- **Контейнер:** `containers/livestock.def` содержит определение вычислительных программ. Файл `containers/livestock-0.3.sif` **не публикуется в Git** и собирается/переносится отдельно.
- **Референс:** полная распакованная FASTA для каждой используемой сборки, а в YAML — точные имена тех хромосом, по которым нужен variant calling.

## Пространство и память

Нужны каталоги с общим доступом из управляющего и вычислительного окружений:

| Назначение | Конфигурационный ключ | Что хранится |
|---|---|---|
| Исходные данные | пути в `samples.tsv` | FASTQ/BAM/CRAM, workflow их не удаляет |
| Рабочее пространство | `workdir` | Промежуточные FASTQ/BAM/BCF **и итоговые BAM/BAI** |
| Постоянные результаты | `results_dir` | VCF, QC, MultiQC, benchmarks |
| Постоянный кеш сборок | `reference_cache_dir` | FASTA, FAI, индексы BWA |

Во время пилота на трёх образцах промежуточные FASTQ и BAM занимали десятки гигабайт; один итоговый WGS BAM — около 17–18 ГБ. Нужный объём зависит от покрытия, длины прочтений и числа параллельных заданий. **Не используйте эти значения как гарантию для больших выборок.**

`results_dir` и `reference_cache_dir` должны быть на надёжном долговременном хранилище. Встроенный `check_config.py` запрещает размещать их в `/mnt/hot/` на Vavilov; итоговые BAM в `workdir` нужно архивировать отдельно при наличии политики очистки scratch.

## Slurm-профили

- `profiles/local/config.yaml` — локальное выполнение, если доступен контейнер.
- `profiles/slurm-example/config.yaml` — шаблон для другого кластера; обязательно изменить partition/account, ограничения памяти, bind-монтирования.
- `profiles/vavilov/config.yaml` — исходный профиль Vavilov.
- `profiles/vavilov-fast/config.yaml` — профиль для протестированного пилота из трёх образцов. Запросы RAM (в частности 4 ГБ для highcov calling) **проверены только на отдельных пилотных животных**; для массовой обработки нужно измерить I/O, производительность и предельное число Slurm-заданий.

Управляющий Snakemake на Vavilov запускают на `vavilov0`, а тяжёлые задания передаются Slurm на `vavilov1`. Не запускайте контроллер внутри `srun` или `sbatch`.

## Сборка SIF

Если на сервере нет готового совместимого образа и **есть права на сборку**:

```bash
apptainer build --fakeroot containers/livestock-0.3.sif containers/livestock.def
apptainer exec --cleanenv containers/livestock-0.3.sif samtools --version
```

При запрете `fakeroot` образ собирают на разрешённой машине и переносят на сервер. Команда `sbatch scripts/build_image.sbatch` специфична для Vavilov и требует корректных путей и разрешённого режима сборки. **Не заменяйте SIF во время выполняющегося анализа.**

Следующий шаг: [порядок установки и запуска](INSTALL_RU.md).
