"""Read and validate the per-sequencing-unit manifest (no third-party deps)."""
from __future__ import annotations
import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

FIELDS = ("sample", "species", "breed", "coverage_type", "input_type", "library", "lane", "r1", "r2", "bam", "cram")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

@dataclass(frozen=True)
class Unit:
    sample: str
    species: str
    breed: str
    coverage_type: str
    input_type: str
    library: str
    lane: str
    r1: str = ""
    r2: str = ""
    bam: str = ""
    cram: str = ""

    @property
    def key(self):
        return (self.sample, self.library, self.lane)

    @property
    def source(self):
        return self.bam or self.cram


def load_manifest(path: str, references: dict, *, require_files: bool = False):
    base = Path(path).expanduser().resolve()
    if not base.is_file():
        raise ValueError(f"Missing manifest: {base}")
    with base.open(newline="", encoding="utf8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError(f"TSV requires columns: {', '.join(FIELDS)}")
        rows = list(reader)
    if not rows:
        raise ValueError("samples.tsv is empty")
    units = {}
    samples = {}
    seen_names = {}
    for line, raw in enumerate(rows, 2):
        values = {col: (raw.get(col) or "").strip() for col in FIELDS}
        u = Unit(**values)
        for k in ("sample", "species", "library", "lane"):
            if not ID.fullmatch(getattr(u, k)):
                raise ValueError(f"Line {line}: invalid {k}={getattr(u,k)!r}; use ASCII letters, digits, _, -, .")
        if not u.breed:
            raise ValueError(f"Line {line}: breed is required")
        if u.coverage_type not in ("highcov", "lowpass"):
            raise ValueError(f"Line {line}: coverage_type must be highcov or lowpass")
        if u.input_type not in ("fastq", "bam", "cram"):
            raise ValueError(f"Line {line}: input_type must be fastq, bam, or cram")
        if u.species not in references:
            raise ValueError(f"Line {line}: no reference configured for {u.species}")
        expected = {"fastq": ("r1", "r2"), "bam": ("bam",), "cram": ("cram",)}[u.input_type]
        present = tuple(x for x in ("r1", "r2", "bam", "cram") if getattr(u, x))
        if present != expected:
            raise ValueError(f"Line {line}: {u.input_type} requires exactly {expected}, got {present}")
        if u.key in units:
            raise ValueError(f"Line {line}: duplicated sequencing unit {u.key}")
        if u.sample in samples:
            old = samples[u.sample]
            if (old.species, old.coverage_type, old.breed, old.input_type) != (u.species, u.coverage_type, u.breed, u.input_type):
                raise ValueError(f"Line {line}: contradictory species/coverage/breed/input_type for sample {u.sample}")
            if u.input_type != "fastq":
                raise ValueError(f"Line {line}: BAM/CRAM supports one file per sample; multiple FASTQ lanes are supported")
        for source_field in expected:
            value = getattr(u, source_field)
            # Paths are interpreted relative to project root, never to the manifest directory.
            p = Path(value).expanduser()
            if not p.is_absolute():
                p = (Path.cwd() / p)
            p = p.resolve()
            if require_files and not p.is_file():
                raise ValueError(f"Line {line}: file not found: {p}")
            values[source_field] = str(p)
        u = Unit(**values)
        units[u.key] = u
        samples[u.sample] = u
    groups = defaultdict(list)
    # Do not silently deduplicate across physically independent libraries.
    # markdup can safely combine sequencing lanes within one library, but a
    # separate library requires library-aware duplicate marking.
    for sid in samples:
        libraries = {unit.library for unit in units.values() if unit.sample == sid}
        if len(libraries) > 1:
            raise ValueError(f"Sample {sid}: multiple independent libraries {sorted(libraries)} are not yet supported for FASTQ duplicate marking; split or add library-aware processing")
    for sample, u in samples.items():
        groups[(u.species, u.coverage_type)].append(sample)
    return units, samples, {k: sorted(v) for k, v in groups.items()}


def verify_references(references: dict, *, require_files: bool = False):
    if not isinstance(references, dict) or not references:
        raise ValueError("config.references must be a nonempty mapping")
    for species, entry in references.items():
        if not ID.fullmatch(species):
            raise ValueError(f"Invalid species key: {species}")
        if not isinstance(entry, dict) or not entry.get("fasta") or not entry.get("contigs") or not entry.get("assembly"):
            raise ValueError(f"Reference {species}: specify assembly, fasta and nonempty contigs array")
        if not ID.fullmatch(str(entry["assembly"])):
            raise ValueError(f"Invalid assembly identifier for {species}")
        if not isinstance(entry["contigs"], list) or any(not ID.fullmatch(c) for c in entry["contigs"]):
            raise ValueError(f"Reference {species}: contigs must be a list of valid names")
        if len(entry["contigs"]) != len(set(entry["contigs"])):
            raise ValueError(f"Reference {species}: duplicate contigs")
        ref = Path(entry["fasta"]).expanduser()
        if not ref.is_absolute():
            ref = Path.cwd() / ref
        ref = ref.resolve()
        if require_files:
            if not ref.is_file():
                raise ValueError(f"Reference FASTA not found: {ref}")
            # The FASTA will be indexed/copied by Snakemake, no external .fai is needed.
            chroms = set()
            with ref.open("rt") as handle:
                for line in handle:
                    if line.startswith(">"):
                        chroms.add(line[1:].split()[0])
            missing = set(entry["contigs"]) - chroms
            if missing:
                raise ValueError(f"Reference {species}: contigs missing from FASTA: {sorted(missing)}")
        entry["fasta"] = str(ref)
