# Конфигурация и входные данные

## 1. YAML-конфигурация

Рабочую конфигурацию следует создавать копированием `config/config.yaml`. Не редактируйте и не переиспользуйте конфигурацию уже выполняющегося расчёта.

| Поле | Что означает |
|---|---|
| `samples` | Путь к TSV с sequencing units |
| `metadata` | Путь к TSV метаданных животных |
| `container_image` | Абсолютный путь или путь относительно корня репозитория к SIF |
| `workdir` | Папка рабочей обработки: BAM, BCF, временные FASTQ |
| `results_dir` | Постоянная папка финальных VCF, QC и benchmark |
| `reference_cache_dir` | Постоянная папка FASTA и индексов выравнивателя |
| `aligner` | `bwa` или `bwa-mem2` |
| `keep_trimmed_fastq` | Сохранять промежуточные trimmed FASTQ при `true` |
| `keep_lane_bam` | Сохранять промежуточные per-lane BAM при `true` |
| `references.<species>.assembly` | Название референсной сборки (используется как часть ключа кеша) |
| `references.<species>.fasta` | Исходная полная FASTA (не `.fna.gz`) |
| `references.<species>.contigs` | Названия хромосом, по которым выполняется variant calling |
| `variant_calling.min_mapq` | Минимальный MAPQ для mpileup; в пилоте 20 |
| `variant_calling.min_baseq` | Минимальный BaseQ; в пилоте 20 |
| `variant_calling.max_depth_per_bam` | Максимальная глубина на BAM для mpileup; в пилоте 10000 |
| `variant_calling.highcov_min_qual` | Порог, ниже которого запись highcov VCF помечается `LowQual` |
| `resource_limits` | Запросы RAM/длительности правил; подробнее в шаблоне YAML |

`references` — отображение вида в `assembly`, `fasta`, `contigs`. Можно использовать и другие виды, если полностью задан подходящий референс и согласованы имена вида во входных TSV. Однако тесты были только на овце и КРС.

**Важно:** `workdir`, `results_dir` и `reference_cache_dir` должны иметь доступное место и быть смонтированы в SIF. Контроллер не обязан видеть те же *локальные* пути, что и compute node, если это не общая файловая система; текущая реализация предполагает общие доступные пути.

## 2. Структура `samples.tsv`

Первая строка должна содержать **в точности** следующие заголовки:

| sample | species | breed | coverage_type | input_type | library | lane | r1 | r2 | bam | cram |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |


В таблице ниже поля показаны визуально; реальный `samples.tsv` — **TSV**, между полями используются символы табуляции. Для создания файла копируйте `config/samples.tsv` и редактируйте его: символ `—` в документации означает пустое поле, **в TSV его нужно оставлять пустым**, а не записывать как текст. Пример FASTQ с двумя lanes одного животного:

| sample | species | breed | coverage_type | input_type | library | lane | r1 | r2 | bam | cram |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SHEEP001 | Ovis_aries | Askanian | highcov | fastq | LIB1 | L001 | /shared/raw/SHEEP001_L001_R1.fastq.gz | /shared/raw/SHEEP001_L001_R2.fastq.gz | — | — |
| SHEEP001 | Ovis_aries | Askanian | highcov | fastq | LIB1 | L002 | /shared/raw/SHEEP001_L002_R1.fastq.gz | /shared/raw/SHEEP001_L002_R2.fastq.gz | — | — |

Пара BAM-входов и lowpass FASTQ другого животного:

| sample | species | breed | coverage_type | input_type | library | lane | r1 | r2 | bam | cram |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CATTLE001 | Bos_taurus | Kalmyk | highcov | bam | LIB_C1 | L001 | — | — | /shared/aligned/CATTLE001.sorted.bam | — |
| SHEEP002 | Ovis_aries | Tsigai | lowpass | fastq | LIB_S2 | L001 | /shared/raw/SHEEP002_R1.fastq.gz | /shared/raw/SHEEP002_R2.fastq.gz | — | — |

Требования и проверки из `workflow/lib/manifest.py`:

- `sample`, `species`, `library`, `lane` — идентификаторы ASCII из букв/цифр/`_`/`-`/`.`; `breed` обязательно.
- `coverage_type`: `highcov`/`lowpass`. Это **режим обработки**, а не измеренная глубина покрытия.
- `input_type`: `fastq`, `bam`, `cram`. Для `fastq` заполнены **только** `r1` и `r2`; для `bam` — только `bam`; для `cram` — только `cram`.
- Сочетание `(sample, library, lane)` должно быть уникальным. Несколько lanes одного sample разрешены только в пределах **одной** библиотеки.
- Несколько разных библиотек одного sample отклоняются: duplicate marking для независимых библиотек ещё не реализован корректно.
- Для импортированного BAM/CRAM разрешён один файл на образец. Требуются `@HD SO:coordinate`, `@RG SM` с правильным sample, согласованные `@SQ SN/LN` с референсом. Импортированный BAM не маркируется повторно по дубликатам.
- Пути к input-файлам могут быть абсолютными или относительно **текущей рабочей директории запуска** (а не папки самого TSV). Для HPC безопаснее абсолютные.

## 3. Структура `metadata.tsv`

Строго необходимы столбцы `sample`, `species`, `breed`; остальные можно добавлять по необходимости. В примере:

| sample | species | breed | population | country | sex | collection_year | source_accession | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SHEEP001 | Ovis_aries | Askanian | Askanian_meat_wool | — | F | — | — | Example |

`validate_manifest.py` проверяет уникальность `sample`, соответствие `species` и `breed`, наличие метаданных для всех образцов. Файл метаданных не меняет режим variant calling: каждый образец независимо обрабатывается по своему BAM, а `species` определяет референс и набор хромосом.

Указывайте истинную таксономию и породу животного в метаданных. Например, для образца индийского КРС, выравненного на `Bos_taurus` референс, технический ключ `species` описывает группу референса, а не доказывает принадлежность к Bos taurus taurus.

## 4. Референсы и хромосомы

В `config/config.yaml` записаны примеры списков для:

- *Ovis aries*, `GCF_016772045.1`, 26 аутосом с идентификаторами `NC_056054.1`–`NC_056079.1`;
- *Bos taurus*, `GCF_002263795.1`, 29 аутосом `NC_037328.1`–`NC_037356.1`.

Используйте полную FASTA соответствующей сборки для выравнивания, а `contigs` — как явное подмножество для variant calling. При сборке другого происхождения не копируйте без проверки эти accession-списки. Текущий calling предполагает диплоидность выбранных contigs.

Кеш выглядит так:

```text
reference_cache_dir/
  Ovis_aries/GCF_016772045.1/genome.fa
  Ovis_aries/GCF_016772045.1/genome.fa.fai
  Ovis_aries/GCF_016772045.1/bwa-mem2/genome.*
  Bos_taurus/GCF_002263795.1/...
```

## 5. Параметры для разных масштабов

Начинайте с консервативных ресурсов из `config/config.yaml`. Оба режима выполняют variant calling **по каждому образцу отдельно**: число независимых заданий примерно пропорционально числу образцов и хромосом, а память одного задания зависит от данных конкретного образца. Для тысяч животных особенно важны лимиты Slurm, файловый I/O и управление промежуточными результатами.

В Slurm `jobs` ограничивает одновременно отправленные jobs, а `resources.mem_mb` при `set-resource-scopes: mem_mb: global` — бюджет контроллера; это **не** выделенный узлу резерв RAM. Slurm проверяет запросы каждого job отдельно. Сумма `threads` удалённых jobs может быть выше `cores` в профиле, поэтому оценивайте фактический параллелизм командой `squeue`.
