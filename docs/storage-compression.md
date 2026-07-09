# Compression et retention des donnees

PiPhocos separe la precision kWh de la finesse graphique. Les kWh sont
conserves durablement dans des rollups energetiques, tandis que les donnees de
graphe sont compressees par niveaux.

## Objectif

- garder les points bruts recents pour le live et les exports fins;
- garder une courbe historique lisible sans stocker une ligne par seconde
  indefiniment;
- conserver les totaux et la qualite necessaires aux rapprochements facture;
- eviter les purges qui modifieraient les kWh deja valides.

## Niveaux de stockage

| Table | Role | Retention par defaut |
| --- | --- | --- |
| `current_snapshot` | Derniere mesure et cumul courant | 1 ligne |
| `samples` | Points bruts recents a la cadence du collecteur | 6 h |
| `minute_samples` | Dernier point par minute pour graphes recents | Jusqu'a compaction 10 min |
| `compressed_samples_10m` | Points moyens pour historique long | Durable |
| `derived_energy_intervals` | Intervalles kWh detailles pour recalcul/audit recent | 45 jours |
| `energy_summary_days` | Totaux kWh par jour | Durable |
| `energy_summary_months` | Totaux kWh par mois | Durable |
| `energy_summary_years` | Totaux kWh par an | Durable |
| `energy_quality_summary_days` | Couverture et qualite par jour | Durable |

## Regles de purge

La compaction des graphes transforme les anciens `samples` en buckets
`compressed_samples_10m`.

La purge des intervalles detailles est plus stricte :

1. le jour doit etre plus ancien que `database.energy_interval_retention_days`;
2. le resume energetique journalier doit exister;
3. le resume qualite journalier doit exister;
4. le jour doit etre finalise;
5. la purge se fait par lots de `database.energy_interval_prune_max_days`.

Si une condition manque, le jour est saute et les intervalles restent en base.

## Parametres

```yaml
database:
  raw_history_retention_hours: 6
  energy_interval_retention_days: 45
  energy_interval_prune_interval_s: 3600
  energy_interval_prune_max_days: 14
```

Une retention plus courte reduit la croissance SQLite, mais raccourcit la
fenetre de recalcul detaille. Pour une installation domestique, 45 jours garde
un mois facture complet plus une marge.

## Mesurer avant de changer

```bash
python3 scripts/compression_report.py --db data/db.sqlite --interval-retention-days 45
```

Verifier principalement :

- les plus gros objets dans `dbstat_top`;
- le nombre de jours candidats;
- le nombre de jours deja prets a la purge;
- la taille du WAL.

## Maintenance

La maintenance legere reste reguliere pour les rollups et le WAL. La purge des
intervalles detailles est separee par `energy_interval_prune_interval_s` afin de
ne pas ralentir la boucle d'acquisition.

Pour lancer une purge controlee hors cycle automatique :

```bash
python3 scripts/prune_energy_intervals.py --db data/db.sqlite --retention-days 45 --max-days 14 --apply
```

Sans `--apply`, le script ne modifie pas la base.

Apres une grosse purge, SQLite reutilise les pages libres. Pour reduire la
taille du fichier sur disque, faire un `VACUUM` seulement pendant une fenetre de
maintenance avec sauvegarde prealable et collecteur arrete.
