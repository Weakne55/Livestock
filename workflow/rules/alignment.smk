"""Modular livestock workflow: alignment.smk."""

rule align_lane:
    input:
        r1=f"{WORK}/trimmed/{{sample}}/{{library}}.{{lane}}_R1.fastq.gz",
        r2=f"{WORK}/trimmed/{{sample}}/{{library}}.{{lane}}_R2.fastq.gz",
        ref=lambda w: cached_fasta(sample(w).species),
        idx=lambda w: index_files(sample(w).species)
    output:
        bam=ephemeral(f"{WORK}/lanes/{{sample}}/{{library}}.{{lane}}.bam", KEEP_LANES)
    params:
        rg=lambda w: f"@RG\\tID:{w.sample}.{w.library}.{w.lane}\\tSM:{w.sample}\\tLB:{w.library}\\tPL:ILLUMINA\\tPU:{w.library}.{w.lane}",
        prefix=lambda w: idx_prefix(sample(w).species),
        aligner=ALIGNER,
        aln_threads=lambda w, threads: max(1, threads-2),
        view_threads=1
    threads: 12
    # The legacy real-WGS jobs hit the previous 360-minute limit.
    # These values are deliberately configurable via Snakemake --set-resources.
    resources:
        mem_mb=lambda w: limit('align_mem_mb_mem2', 56000) if ALIGNER == 'bwa-mem2' else limit('align_mem_mb_bwa', 24000),
        runtime=lambda w: limit('align_highcov_runtime', 1440) if sample(w).coverage_type == 'highcov' else limit('align_lowpass_runtime', 360)
    benchmark: f"{RESULTS}/benchmarks/alignment/{{sample}}.{{library}}.{{lane}}.tsv"

    shell:
        "{params.aligner} mem -t {params.aln_threads} -R '{params.rg}' "
        "{params.prefix:q} {input.r1:q} {input.r2:q} "
        "| samtools view -b -@ {params.view_threads} -o {output.bam:q} -"
