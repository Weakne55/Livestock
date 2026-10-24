"""Modular livestock workflow: calling_lowpass.smk."""

rule call_lowpass_contig:
    input:
        bam=f"{WORK}/bam/{{sample}}.bam",
        bai=f"{WORK}/bam/{{sample}}.bam.bai",
        ref=lambda w: cached_fasta(w.species),
        fai=lambda w: cached_fasta(w.species) + '.fai'
    output:
        bcf=f"{WORK}/raw_calls/{{species}}/lowpass/{{sample}}/{{contig}}.bcf",
        csi=f"{WORK}/raw_calls/{{species}}/lowpass/{{sample}}/{{contig}}.bcf.csi"
    params:
        min_mapq=int(CALL.get('min_mapq', 20)),
        min_baseq=int(CALL.get('min_baseq', 20)),
        max_depth=int(CALL.get('max_depth_per_bam', 10000))
    threads: 2
    resources: mem_mb=limit('call_lowpass_mem_mb', 8000), runtime=limit('call_lowpass_runtime', 480)
    benchmark: f"{RESULTS}/benchmarks/lowpass/{{species}}.{{sample}}.{{contig}}.tsv"

    shell:
        'bcftools mpileup -Ou -f {input.ref:q} -r {wildcards.contig:q} '
        '-q {params.min_mapq} -Q {params.min_baseq} -d {params.max_depth} '
        '-a FORMAT/DP,FORMAT/AD {input.bam:q} '
        '| bcftools call -m -v -Ob -o {output.bcf:q}; '
        'bcftools index -f {output.bcf:q}'
