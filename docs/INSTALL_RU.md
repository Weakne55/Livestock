# Установка и запуск Livestock

## Когда выполнять команды

Есть два разных сценария:

- **А. Первая установка на новом сервере** — один раз: скачать исходники, установить окружение, подготовить SIF и профиль Slurm.
- **Б. Новый анализ на уже настроенном сервере** — для **каждой новой партии образцов**: создать собственные YAML/TSV, проверить входы, сделать dry-run, запустить.

Если вы уже работаете на `vavilov0` в `~/livestock` и там завершились пилотные запуски, начинайте сразу со **сценария Б**. Команды ниже не нужно выполнять заново для уже завершённых пилотов.

## Сценарий А. Первая установка на новом сервере

### А1. Скачать код и установить окружение контроллера

```bash
git clone git@github.com:Weakne55/Livestock.git
cd Livestock
conda env create -f manager/environment.yaml
conda activate livestock-snakemake
python -m unittest discover -s tests -v
```

Если каталог уже существует с работающим проектом, **не клонируйте репозиторий поверх него**. Набор из 26 unit-тестов проверяет структуру и утилиты, а не точность вызванных вариантов.

### А2. Подготовить контейнер

В готовом репозитории есть `containers/livestock.def`, но большого бинарного SIF нет. Если есть права:

```bash
apptainer build --fakeroot containers/livestock-0.3.sif containers/livestock.def
apptainer exec --cleanenv containers/livestock-0.3.sif bcftools --version
sha256sum containers/livestock-0.3.sif
```

Если сборка запрещена, соберите SIF на другом разрешённом узле и перенесите его. На Vavilov уже имеется протестированный контейнер: **не пересобирайте его без причины**. Уточнения — в [требованиях](REQUIREMENTS_RU.md).

### А3. Настроить вычислительный профиль

Для другого Slurm-кластера используйте `profiles/slurm-example/config.yaml` и проверьте `slurm_partition`, `slurm_account` (если обязателен), `jobs`, лимиты памяти и `apptainer-args` с существующими bind-путями. Профили `vavilov*` не универсальны.

## Сценарий Б. Пайплайн уже установлен: запуск новых образцов

### Б1. Создать **новые** конфигурационные файлы

Эти команды выполняются **один раз при подготовке каждой новой партии**, а не при каждом восстановлении прерванного расчёта:

```bash
cd ~/livestock
conda activate livestock-snakemake
cp config/config.yaml config/herd2026.local.yaml
cp config/samples.tsv config/herd2026_samples.tsv
cp config/metadata.tsv config/herd2026_metadata.tsv
```

**Зачем `cp`?** Исходные файлы — шаблоны с фиктивными примерами и путями `/absolute/path/...`. Копирование позволяет сохранить шаблоны для коллег и не перезаписывать параметры других запусков. Можно создавать эти три файла вручную — смысл тот же. Файл YAML содержит пути к двум TSV: измените его поля `samples` и `metadata` соответственно.

**Что заполнить:**

- `config/herd2026_samples.tsv` — по строке на sequencing unit: `sample`, `species`, `breed`, `coverage_type`, `input_type`, `library`, `lane`, `r1`, `r2`, `bam`, `cram`. Для paired FASTQ заполняются `r1`/`r2`; для готового BAM — `bam`; остальные входные поля оставляют пустыми.
- `config/herd2026_metadata.tsv` — минимум `sample`, `species`, `breed`, по одной строке на животное. Нужен для отдельной проверки манифеста; **не используется автоматически в статистических моделях/variant calling**.
- `config/herd2026.local.yaml` — пути к TSV, референсам, контейнеру, отдельным `workdir` и `results_dir`, общему `reference_cache_dir`, нужные виды и список contigs.

Конкретный формат, таблицы и ограничения — [в описании конфигурации](CONFIGURATION_RU.md). Файлы с настоящими образцами не публикуйте в GitHub.

> Важно: ранее выполненные `real_sif_20261022` и `real_sif_perf_20261023` — самостоятельные пилоты. Не редактируйте их исходные YAML для нового анализа и не запускайте новый расчёт в их `workdir`.

### Б2. Проверить входные файлы (до Slurm)

```bash
python scripts/validate_manifest.py --config config/herd2026.local.yaml --lightweight
python scripts/check_config.py --config config/herd2026.local.yaml --require-image
```

Первая команда проверяет манифест, наличие входов, доступность референса и соответствие метаданных; `--lightweight` не сканирует всю многогигабайтную FASTA. Вторая проверяет контейнер, обязательные пути и запрет хранения финальных результатов в `/mnt/hot` на Vavilov. Эти команды **не выполняют секвенирование и variant calling**.

Если подключаете новую сборку, полезно повторить валидацию без `--lightweight` для проверки объявленных contigs:

```bash
python scripts/validate_manifest.py --config config/herd2026.local.yaml
```

### Б3. Dry-run — проверка графа задач без вычислений

На Vavilov:

```bash
snakemake -s workflow/Snakefile \
  --configfile config/herd2026.local.yaml \
  --profile profiles/vavilov-fast --dry-run
```

На другом Slurm-кластере замените профиль на настроенный `profiles/slurm-example`. **Dry-run ничего не выравнивает и не создаёт VCF**: он показывает план правил и зависимости, помогает обнаружить ошибки конфигурации до расходования ресурсов.

### Б4. Реальный запуск

На `vavilov0` (из обычного терминала, **не** из `srun`/`sbatch`):

```bash
LIVESTOCK_PROFILE=profiles/vavilov-fast \
  bash scripts/launch_vavilov.sh config/herd2026.local.yaml
```

Скрипт выдаст путь к `logs/controller-...log` и PID, контроллер останется работать после отключения SSH. Для больших когорт заранее пересмотрите консервативные настройки памяти: пилотный профиль `vavilov-fast` проверен только на 3 образцах.

На другом кластере после адаптации `profiles/slurm-example/config.yaml` используйте в устойчивой `tmux`-сессии:

```bash
snakemake -s workflow/Snakefile \
  --configfile config/herd2026.local.yaml \
  --profile profiles/slurm-example
```

Не запускайте одновременно второй Snakemake-контроллер для той же рабочей папки.

### Б5. Мониторинг и завершение

```bash
squeue -u "$USER"
# Подставьте путь к логу, показанный launch_vavilov.sh:
tail -n 40 logs/controller-YYYYMMDDTHHMMSSZ.log
```

Успех — `100% done` в журнале и наличие VCF/индексов/QC/MultiQC, а не только пустой `squeue`. Результаты и пути — [здесь](OUTPUTS_RU.md). Восстановление после сбоев — [здесь](MAINTENANCE_RU.md).

## Почему в кратком README нет длинного Quick start

Содержимое этого раздела применяют **только тогда, когда устанавливают пайплайн или готовят новую партию данных**. Для человека, который читает GitHub ради принципа работы пайплайна, достаточно основной схемы и ссылок. Запуск команд на уже готовых пилотных данных не требуется.
