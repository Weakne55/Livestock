"""Modular livestock workflow: reporting.smk."""

rule multiqc:
    input:
        [f"{RESULTS}/qc/bam/{sid}.{suffix}" for sid in SAMPLES for suffix in
         ('flagstat.txt', 'stats.txt', 'mosdepth.summary.txt')],
        [f"{RESULTS}/qc/fastp/{u.sample}/{u.library}.{u.lane}.json"
         for u in UNITS.values() if u.input_type == 'fastq'],
        [f"{RESULTS}/qc/vcf/{sp}/highcov/{sid}.stats.txt" for sp, sid in HIGH],
        [f"{RESULTS}/qc/vcf/{sp}/lowpass/{sid}.stats.txt" for sp, sid in LOW]
    output:
        html=f"{RESULTS}/qc/multiqc/multiqc_report.html"
    params:
        outdir=f"{RESULTS}/qc/multiqc",
        indir=f"{RESULTS}/qc"
    threads: 2
    resources: mem_mb=limit('multiqc_mem_mb', 12000), runtime=limit('multiqc_runtime', 240)

    shell:
        'multiqc -f --outdir {params.outdir:q} --filename multiqc_report.html {params.indir:q}'
