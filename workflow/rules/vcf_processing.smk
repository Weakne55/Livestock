"""Modular livestock workflow: vcf_processing.smk."""

rule highcov_vcf:
    input:
        bcfs=high_raw,
        indices=lambda w: [f"{WORK}/raw_calls/{w.species}/highcov/{w.sample}/{c}.bcf.csi" for c in CHROMS[w.species]],
        ref=lambda w: cached_fasta(w.species)
    output:
        vcf=f"{RESULTS}/vcf/{{species}}/highcov/{{sample}}.vcf.gz",
        idx=f"{RESULTS}/vcf/{{species}}/highcov/{{sample}}.vcf.gz.tbi"
    params:
        n=lambda w: len(CHROMS[w.species]),
        qual=int(CALL.get('highcov_min_qual', 30))
    threads: 2
    resources: mem_mb=limit('final_vcf_mem_mb', 12000), runtime=limit('final_vcf_runtime', 360)
    benchmark: f"{RESULTS}/benchmarks/final_highcov/{{species}}.{{sample}}.tsv"

    shell:
        '(if [ {params.n} -eq 1 ]; then bcftools view -Ou {input.bcfs:q}; '
        'else bcftools concat -Ou {input.bcfs:q}; fi) '
        '| bcftools norm -Ou -f {input.ref:q} -m -any '
        '| bcftools filter -s LowQual -e "QUAL<{params.qual}" -Oz -o {output.vcf:q}; '
        'bcftools index -f -t {output.vcf:q}'

rule lowpass_vcf:
    input:
        bcfs=low_raw,
        indices=lambda w: [f"{WORK}/raw_calls/{w.species}/lowpass/{w.sample}/{c}.bcf.csi" for c in CHROMS[w.species]],
        ref=lambda w: cached_fasta(w.species)
    output:
        vcf=f"{RESULTS}/vcf/{{species}}/lowpass/{{sample}}.vcf.gz",
        idx=f"{RESULTS}/vcf/{{species}}/lowpass/{{sample}}.vcf.gz.tbi"
    params:
        n=lambda w: len(CHROMS[w.species])
    threads: 2
    resources: mem_mb=limit('final_vcf_mem_mb', 12000), runtime=limit('final_vcf_runtime', 360)
    benchmark: f"{RESULTS}/benchmarks/final_lowpass/{{species}}.{{sample}}.tsv"

    shell:
        '(if [ {params.n} -eq 1 ]; then bcftools view -Ou {input.bcfs:q}; '
        'else bcftools concat -Ou {input.bcfs:q}; fi) '
        '| bcftools norm -f {input.ref:q} -m -any -Oz -o {output.vcf:q}; '
        'bcftools index -f -t {output.vcf:q}'

rule highcov_stats:
    input:
        vcf=f"{RESULTS}/vcf/{{species}}/highcov/{{sample}}.vcf.gz",
        idx=f"{RESULTS}/vcf/{{species}}/highcov/{{sample}}.vcf.gz.tbi"
    output:
        f"{RESULTS}/qc/vcf/{{species}}/highcov/{{sample}}.stats.txt"
    threads: 2
    resources: mem_mb=limit('vcf_stats_mem_mb', 6000), runtime=limit('vcf_stats_runtime', 180)

    shell:
        'bcftools stats -s - {input.vcf:q} > {output:q}'

rule lowpass_stats:
    input:
        vcf=f"{RESULTS}/vcf/{{species}}/lowpass/{{sample}}.vcf.gz",
        idx=f"{RESULTS}/vcf/{{species}}/lowpass/{{sample}}.vcf.gz.tbi"
    output:
        f"{RESULTS}/qc/vcf/{{species}}/lowpass/{{sample}}.stats.txt"
    threads: 2
    resources: mem_mb=limit('vcf_stats_mem_mb', 6000), runtime=limit('vcf_stats_runtime', 180)

    shell:
        'bcftools stats -s - {input.vcf:q} > {output:q}'
