# Plan de test performance acquisition

Ce plan sert a valider progressivement une cadence d'acquisition plus rapide
sans degrader la precision kWh ni la stabilite du Raspberry Pi.

## Phase 0 - Sauvegarde et reference initiale

Sur le Pi :

```bash
cd <dossier-piphocos>
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p data/backups data/measurements/$TS
cp data/config.yml data/backups/config.$TS.yml
sqlite3 data/db.sqlite ".backup 'data/backups/db.$TS.sqlite'"
du -h data/db.sqlite data/db.sqlite-wal data/db.sqlite-shm
```

Mesures avant changement :

```bash
python3 scripts/acquisition_report.py --db data/db.sqlite --minutes 30 --days 1
```

Equivalent SQL manuel pour les gaps :

```sql
WITH ordered AS (
  SELECT
    recorded_at,
    unixepoch(recorded_at) -
      unixepoch(lag(recorded_at) OVER (ORDER BY recorded_at)) AS dt
  FROM samples
  WHERE recorded_at >= datetime('now', '-30 minutes')
)
SELECT
  count(*) samples,
  round(avg(dt), 2) avg_s,
  min(dt) min_s,
  max(dt) max_s,
  sum(dt > 12) gaps_over_12s,
  sum(dt > 30) gaps_over_30s
FROM ordered
WHERE dt IS NOT NULL;
```

Capturer aussi :

```bash
vmstat 1 120
tail -n 500 data/grabber.log
curl -fsS http://127.0.0.1:5000/api/live
sqlite3 data/db.sqlite "PRAGMA integrity_check; PRAGMA wal_checkpoint(PASSIVE);"
```

## Phase 1 - Validation locale

Avant tout deploiement :

```bash
python3 -m pytest -q
```

Seuils attendus sur copie de base :

- demarrage schema sans migration lourde : moins de 5 s;
- persistance d'un sample : p95 inferieur a 150 ms;
- WAL checkpointable;
- WAL inferieur au seuil `database.wal_truncate_threshold_mb` apres maintenance;
- `/api/period?...&include_high_res=0` ne renvoie pas de courbe high-res;
- `/api/reconciliation` indique `coverage.source=daily_quality_summary` pour les
  plages de jours complets deja resumees. `coverage.source=intervals` reste
  attendu pour les plages partielles ou si les resumes qualite doivent etre
  reconstruits hors requete;
- `/api/live` ne renvoie pas d'identifiants materiels quand
  `privacy.expose_device_identifiers: false`;
- pas de regression des rollups et deltas energetiques.

## Phase 2 - Retour a une acquisition stable a 10 s

Garder `grabber.interval_s: 10` et mesurer 30 minutes.

Avant de descendre la cadence du collecteur complet, mesurer la limite physique
du lien serie seul :

```bash
python3 scripts/phocos_serial_benchmark.py \
  --port /dev/serial/by-id/<adaptateur-serie> \
  --samples 120 \
  --interval 0 \
  --qpigs-every 5 \
  --qpiws-every 120
```

Verifier aussi le cout SQLite hors liaison serie et les surfaces publiques :

```bash
python3 scripts/storage_benchmark.py --samples 1000 --interval 1
python3 scripts/storage_benchmark.py --samples 1000 --interval 1 --store-raw-snapshot
python3 scripts/compression_report.py --db data/db.sqlite --interval-retention-days 45
python3 scripts/prune_energy_intervals.py --db data/db.sqlite --retention-days 45 --max-days 14
python3 scripts/rebuild_quality_summaries.py --db data/db.sqlite --start-day 2026-06-01 --end-day 2026-07-01
python3 scripts/privacy_scan.py
```

Passage attendu :

- p95 du gap sample `<= 12 s`;
- max gap `<= 20 s`;
- pas de repetition de `polling is behind schedule`;
- pas d'erreur SQLite;
- `store_sample_raw_snapshot_json` reste `false` sauf diagnostic ponctuel;
- `compression_report.py` montre que les plus gros objets SQLite sont connus et
  que les jours candidats aux purges ont bien un resume energie et qualite;
- pas de swap soutenu;
- iowait idealement `< 10%`.

## Phase 3 - Descente progressive

| Etape | Cadence | Duree | Seuil de passage |
| --- | ---: | ---: | --- |
| A | 10 s | 30 min | p95 `<= 12 s`, pas de retard repete |
| B | 2 s | 30 min | p95 `<= 2.5 s`, max `<= 5 s` |
| C | 1 s | 60 min | p95 `<= 1.3 s`, max `<= 3 s` |
| D | 0.5 s | 10-15 min | stress test seulement |

La cadence `0.5 s` n'est pas un objectif de production tant que la limite serie
2400 bauds n'est pas prouvee stable.

## Resultats mesures sur installation locale

Mesures realisees sur le Raspberry Pi avec la base existante et l'onduleur
Phocos connecte. Les premiers polls apres redemarrage sont exclus des decisions
car ils incluent les probes et migrations de demarrage.

| Reglage teste | Resultat | Decision |
| --- | --- | --- |
| `interval_s=10` | Fenetre stable : moyenne `10.001 s`, p95 `10.009 s`, max `10.014 s` | OK |
| `interval_s=2` | Fenetre stable : moyenne `2.000 s`, p95 `2.000 s`, max `2.015 s` | OK |
| `interval_s=1`, `qpigs_interval_s` par defaut | moyenne `1.202 s`, p95 `1.839 s`, retards repetes | Non retenu |
| `interval_s=1`, `qpigs_interval_s=30` | moyenne `1.035 s`, p95 `1.167 s`, max `1.840 s`, aucun gap > `3 s` | Reglage production |
| `interval_s=0.5`, `qpigs_interval_s=30` | moyenne `0.773 s`, p95 `0.944 s`, retards quasi continus | Stress test seulement |

Reglage retenu pour l'installation actuelle :

```yaml
phocos:
  qpigs_interval_s: 30
grabber:
  interval_s: 1
```

Si l'injection reseau ou la puissance PV exacte issue de `QPIGS` devient une
donnee de facturation prioritaire, retester `qpigs_interval_s` a 5-10 s et
revalider les seuils avant de conserver `interval_s=1`.

## Retour arriere immediat

Revenir au dernier commit/config valide si :

- p95 sample gap > `2 * interval_s` pendant 5 minutes;
- un gap sample > 60 s;
- 3 warnings `polling is behind schedule` consecutifs;
- iowait > 20% pendant 60 s;
- swap-in/swap-out soutenu;
- WAL > 128 MB ou checkpoint impossible;
- `database is locked`, corruption ou integrity check non `ok`;
- redemarrage conteneur, OOM ou service de surveillance;
- `/api/live` stale plus de 30 s.

Retour arriere :

```bash
cd <dossier-piphocos>
cp data/backups/config.<last-good>.yml data/config.yml
git checkout <last-good-commit>
docker compose up --build -d piphocos
```

Ne restaurer la base que si une migration a corrompu les donnees ou si
`PRAGMA integrity_check` echoue.
