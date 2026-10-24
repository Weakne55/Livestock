# Выходные файлы, QC и хранение данных

## Каталоги

В конфигурации разделены три места хранения: `workdir`, `results_dir`, `reference_cache_dir`. Ниже примеры путей относительно соответствующих корней.

### `workdir`: рабочие выравнивания и промежуточные вызовы

```text
workdir/
├── trimmed/<sample>/<library>.<lane>_R1.fastq.gz
├── trimmed/<sample>/<library>.<lane>_R2.fastq.gz
├── lanes/<sample>/<library>.<lane>.bam
├── bam/<sample>.bam
├── bam/<sample>.bam.bai
└── raw_calls/
    ├── Ovis_aries/highcov/<sample>/<contig>.bcf
    └── Ovis_aries/lowpass/<sample>/<contig>.bcf
```

`trimmed` и `lanes` удаляются Snakemake после успешного потребления, если `keep_trimmed_fastq: false` и `keep_lane_bam: false`. `bam` и `raw_calls` обычные outputs, которые Snakemake сам по этим флагам **не** удаляет.

**Критическое ограничение долговременного хранения:** финальные BAM находятся в `workdir`. Если это автоматически очищаемый scratch, внешняя политика кластера может удалить их, даже если Snakemake сам их сохраняет. Для дальнейшего SV/CNV, повторного variant calling или просмотра в IGV скопируйте BAM и индексы на постоянное хранилище после полного завершения.

### `results_dir`: финальные научные результаты

```text
results_dir/
├── vcf/
│   ├── Bos_taurus/highcov/<sample>.vcf.gz
│   ├── Bos_taurus/highcov/<sample>.vcf.gz.tbi
│   └── Ovis_aries/lowpass/<sample>.vcf.gz
├── qc/
│   ├── fastp/<sample>/<library>.<lane>.json
│   ├── fastp/<sample>/<library>.<lane>.html
│   ├── bam/<sample>.flagstat.txt
│   ├── bam/<sample>.stats.txt
│   ├── bam/<sample>.mosdepth.summary.txt
│   ├── bam/<sample>.regions.bed.gz
│   ├── bam/<sample>.thresholds.bed.gz
│   ├── vcf/<species>/highcov/<sample>.stats.txt
│   ├── vcf/<species>/lowpass/<sample>.stats.txt
│   └── multiqc/multiqc_report.html
└── benchmarks/
    ├── fastp/*.tsv
    ├── alignment/*.tsv
    ├── canonical/*.tsv
    ├── bam_qc/*.tsv
    ├── highcov/*.tsv
    ├── lowpass/*.tsv
    ├── final_highcov/*.tsv
    └── final_lowpass/*.tsv
```

**И highcov, и lowpass формируют один VCF на каждый образец**. Никакого общего `cohort.vcf.gz` этот workflow больше не создаёт. Для примеров с обоими видами также будут соответствующие папки в `vcf/`.

Порог highcov `QUAL < highcov_min_qual` **помечает** вариант фильтром `LowQual`, а не обязательно удаляет запись. У lowpass не применяется тот же порог, и гетерозиготы/гомозиготы нельзя считать импутированными. Не путайте число VCF-записей с числом достоверных генотипов.

## Проверка после окончания

Проверять следует только после полного завершения правила `all`:

```bash
RESULTS=/absolute/path/to/persistent/results/run001
WORK=/absolute/path/to/work/run001
find "$RESULTS/vcf" -type f -name '*.vcf.gz' -print
find "$RESULTS/vcf" -type f -name '*.vcf.gz.tbi' -print
find "$WORK/bam" -type f -name '*.bam' -print
find "$WORK/bam" -type f -name '*.bam.bai' -print
test -s "$RESULTS/qc/multiqc/multiqc_report.html"
```

Для каждого VCF используйте `bcftools index -n` и `bcftools query -l`, а для BAM `samtools quickcheck -v` и `samtools idxstats`. На целевой когорте потребуется отдельный биологический QC, не только техническое завершение Snakemake.

## Сохранение BAM

```bash
WORK=/absolute/path/to/work/run001
RESULTS=/absolute/path/to/persistent/results/run001
mkdir -p "$RESULTS/bam"
rsync -avh --progress "$WORK/bam/" "$RESULTS/bam/"

# Проверка размеров и контрольных сумм на обеих сторонах (может быть долгой):
find "$WORK/bam" -maxdepth 1 -type f -name '*.bam' -print0 | sort -z | xargs -0 -r sha256sum
find "$RESULTS/bam" -maxdepth 1 -type f -name '*.bam' -print0 | sort -z | xargs -0 -r sha256sum
```

Сравнивайте хеши по соответствующим именам, а не целые строки (пути разные). Файлы `.bai` следует сохранять рядом с BAM.
