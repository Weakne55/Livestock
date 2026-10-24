"""Modular livestock workflow: preprocessing.smk."""

rule trim_fastq:
    input:
        r1=lambda w: unit(w).r1,
        r2=lambda w: unit(w).r2
    output:
        r1=ephemeral(f"{WORK}/trimmed/{{sample}}/{{library}}.{{lane}}_R1.fastq.gz", KEEP_TRIMMED),
        r2=ephemeral(f"{WORK}/trimmed/{{sample}}/{{library}}.{{lane}}_R2.fastq.gz", KEEP_TRIMMED),
        json=f"{RESULTS}/qc/fastp/{{sample}}/{{library}}.{{lane}}.json",
        html=f"{RESULTS}/qc/fastp/{{sample}}/{{library}}.{{lane}}.html"
    threads: 4
    resources:
        mem_mb=lambda w: limit('fastp_mem_mb', 32000),
        runtime=lambda w: limit('fastp_highcov_runtime', 240) if sample(w).coverage_type == 'highcov' else limit('fastp_lowpass_runtime', 120)
    benchmark: f"{RESULTS}/benchmarks/fastp/{{sample}}.{{library}}.{{lane}}.tsv"

    shell:
        'fastp -i {input.r1:q} -I {input.r2:q} -o {output.r1:q} -O {output.r2:q} '
        '-j {output.json:q} -h {output.html:q} -w {threads} --detect_adapter_for_pe'
