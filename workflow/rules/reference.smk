"""Modular livestock workflow: reference.smk."""

rule prepare_reference:
    input:
        fasta=lambda w: REFERENCES[w.species]['fasta']
    output:
        fasta=f"{CACHE}/{{species}}/{{assembly}}/genome.fa",
        fai=f"{CACHE}/{{species}}/{{assembly}}/genome.fa.fai",
        sha256=f"{CACHE}/{{species}}/{{assembly}}/genome.fa.sha256"
    wildcard_constraints:
        species='|'.join(REFERENCES),
    threads: 2
    resources: mem_mb=limit('prepare_ref_mem_mb', 8000), runtime=limit('prepare_ref_runtime', 180)

    params:
        declared_assembly=lambda w: REFERENCES[w.species]['assembly'],
        chroms=lambda w: ' '.join(REFERENCES[w.species]['contigs'])
    shell:
        r"""
        test '{wildcards.assembly}' = '{params.declared_assembly}'
        mkdir -p $(dirname {output.fasta:q})
        cp -L {input.fasta:q} {output.fasta:q}
        samtools faidx {output.fasta:q}
        python scripts/validate_reference_fai.py {output.fai:q} {params.chroms}
        sha256sum {output.fasta:q} > {output.sha256:q}
        """

if ALIGNER == 'bwa':
    rule index_reference:
        input:
            fasta=f"{CACHE}/{{species}}/{{assembly}}/genome.fa",
            fai=f"{CACHE}/{{species}}/{{assembly}}/genome.fa.fai"
        output:
            idx=[f"{CACHE}/{{species}}/{{assembly}}/bwa/genome{s}" for s in SUFFIXES]
        threads: 2
        resources: mem_mb=limit('bwa_index_mem_mb', 16000), runtime=limit('bwa_index_runtime', 480)

        params:
            prefix=lambda w: f"{CACHE}/{w.species}/{w.assembly}/bwa/genome"
        shell:
            'mkdir -p $(dirname {params.prefix:q}); bwa index -a bwtsw -p {params.prefix:q} {input.fasta:q}'
else:
    rule index_reference:
        input:
            fasta=f"{CACHE}/{{species}}/{{assembly}}/genome.fa",
            fai=f"{CACHE}/{{species}}/{{assembly}}/genome.fa.fai"
        output:
            idx=[f"{CACHE}/{{species}}/{{assembly}}/bwa-mem2/genome{s}" for s in SUFFIXES]
        threads: 4
        resources: mem_mb=limit('mem2_index_mem_mb', 60000), runtime=limit('mem2_index_runtime', 720)

        params:
            prefix=lambda w: f"{CACHE}/{w.species}/{w.assembly}/bwa-mem2/genome"
        shell:
            'mkdir -p $(dirname {params.prefix:q}); bwa-mem2 index -p {params.prefix:q} {input.fasta:q}'
