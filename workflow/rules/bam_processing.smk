"""Modular livestock workflow: bam_processing.smk."""

rule canonical_bam:
    input:
        files=canonical_inputs,
        ref=lambda w: cached_fasta(sample(w).species),
        fai=lambda w: cached_fasta(sample(w).species) + '.fai'
    output:
        bam=f"{WORK}/bam/{{sample}}.bam",
        bai=f"{WORK}/bam/{{sample}}.bam.bai"
    params:
        mode=lambda w: sample(w).input_type
    threads: 8
    resources:
        mem_mb=lambda w: limit('canonical_mem_mb', 24000),
        runtime=lambda w: limit('canonical_highcov_runtime', 1440) if sample(w).coverage_type == 'highcov' else limit('canonical_lowpass_runtime', 360)
    benchmark: f"{RESULTS}/benchmarks/canonical/{{sample}}.tsv"

    shell:
        'bash scripts/create_bam.sh {params.mode:q} {input.ref:q} {wildcards.sample:q} '
        '{threads} {output.bam:q} {input.files:q}'
