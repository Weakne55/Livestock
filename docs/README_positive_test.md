# Синтетический положительный тест

Это **дополнительная** проверка пайплайна на искусственно сгенерированных FASTQ с заранее известными SNP. Она не требуется для обычного запуска на реальных животных и не измеряет чувствительность lpWGS на настоящем низком покрытии.

В окружении `livestock-snakemake` из корня репозитория:

```bash
python scripts/generate_positive_demo.py
python scripts/validate_manifest.py --config config/demo_positive.yaml
```

Генератор создаёт `tests/positive_data/`, `config/demo_positive.yaml`, `tests/positive_data/truth.tsv` и примеры овцы/КРС. **Он может перезаписать ранее созданные синтетические файлы**, не запускайте его в каталоге с нужными ручными модификациями теста.

После доступности SIF и настройки подходящего профиля сначала проверьте DAG:

```bash
snakemake -s workflow/Snakefile \
  --configfile config/demo_positive.yaml \
  --profile profiles/local --dry-run
```

Затем запустите такую же команду без `--dry-run` в подходящей среде. По окончании проверьте варианты (в окружении, где есть `bcftools`):

```bash
python scripts/check_positive_demo.py --bcftools bcftools
```

Файл `config/demo_positive.yaml` **не хранится в Git**: его создаёт скрипт. Если положительный тест не запускали, отсутствие этого файла нормально.

Теперь синтетический набор включает **два highcov-образца овцы** (`SH_HC`, `SH_HC2`), один highcov-образец КРС (`CA_HC`) и lowpass-овцу (`SH_LP`). Checker проверяет, что каждый highcov VCF содержит **ровно один правильный идентификатор образца**.
