"""Modular livestock workflow: bam_qc.smk."""

rule bam_qc:
    input:
        bam=f"{WORK}/bam/{{sample}}.bam",
        bai=f"{WORK}/bam/{{sample}}.bam.bai"
    output:
        flagstat=f"{RESULTS}/qc/bam/{{sample}}.flagstat.txt",
        stats=f"{RESULTS}/qc/bam/{{sample}}.stats.txt",
        summary=f"{RESULTS}/qc/bam/{{sample}}.mosdepth.summary.txt",
        regions=f"{RESULTS}/qc/bam/{{sample}}.regions.bed.gz",
        thresholds=f"{RESULTS}/qc/bam/{{sample}}.thresholds.bed.gz"
    params:
        prefix=lambda w: f"{RESULTS}/qc/bam/{w.sample}"
    threads: 4
    resources:
        mem_mb=lambda w: limit('bam_qc_mem_mb', 12000),
        runtime=lambda w: limit('bam_qc_highcov_runtime', 720) if sample(w).coverage_type == 'highcov' else limit('bam_qc_lowpass_runtime', 360)
    benchmark: f"{RESULTS}/benchmarks/bam_qc/{{sample}}.tsv"

    shell:
        'samtools flagstat -@ 2 {input.bam:q} > {output.flagstat:q}; '
        'samtools stats -@ 2 {input.bam:q} > {output.stats:q}; '
        'mosdepth --threads 2 --mapq 20 -n --by 1000000 '
        '--thresholds 1,5,10,20 {params.prefix:q} {input.bam:q}'
