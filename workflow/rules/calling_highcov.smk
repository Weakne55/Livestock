"""Modular livestock workflow: calling_highcov.smk."""

rule call_highcov_contig:
    input:
        bam=high_bam,
        bai=lambda w: high_bam(w) + '.bai',
        ref=lambda w: cached_fasta(w.species),
        fai=lambda w: cached_fasta(w.species) + '.fai'
    output:
        bcf=f"{WORK}/raw_calls/{{species}}/highcov/{{sample}}/{{contig}}.bcf",
        csi=f"{WORK}/raw_calls/{{species}}/highcov/{{sample}}/{{contig}}.bcf.csi"
    params:
        min_mapq=int(CALL.get('min_mapq', 20)),
        min_baseq=int(CALL.get('min_baseq', 20)),
        max_depth=int(CALL.get('max_depth_per_bam', 10000))
    threads: 2
    resources: mem_mb=limit('call_highcov_mem_mb', 16000), runtime=limit('call_highcov_runtime', 900)
    benchmark: f"{RESULTS}/benchmarks/highcov/{{species}}.{{sample}}.{{contig}}.tsv"

    shell:
        'bcftools mpileup -Ou -f {input.ref:q} -r {wildcards.contig:q} '
        '-q {params.min_mapq} -Q {params.min_baseq} -d {params.max_depth} '
        '-a FORMAT/DP,FORMAT/AD {input.bam:q} '
        '| bcftools call -m -v -Ob -o {output.bcf:q}; '
        'bcftools index -f {output.bcf:q}'
