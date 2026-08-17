# Fonctionnement, précision et maintenance

PiPhocos sépare la cadence d'acquisition, le rafraîchissement de l'interface et
la conservation des données. La priorité est d'enregistrer régulièrement les
puissances utiles au calcul des kWh sans saturer la liaison série.

## Acquisition Phocos

Le protocole expose des commandes complètes. `QPGS0` fournit le paquet principal
pour la charge, la batterie et le solaire ; il n'est pas lu champ par champ.
Les informations plus lentes ou plus lourdes sont mises en cache.

| Commande | Usage | Cadence indicative |
| --- | --- | --- |
| `QPGS0` | Puissances principales et états | Chaque cycle |
| `QPIGS` | PV complémentaire, injection, température | Cadence séparée |
| `QPIWS` | Alertes | Lente |
| `QPIRI`, `QID`, `QFLAG`, `QPI` | Configuration et identité | Démarrage ou ponctuel |

Le réglage validé sur l'installation de référence est un cycle `QPGS0` de
1 seconde et un `QPIGS` toutes les 30 secondes. Ce résultat dépend toutefois de
l'onduleur, de l'adaptateur et de l'hôte. Une cadence de 0,5 seconde est un test
de charge, pas une recommandation de production sur une liaison à 2400 bauds.

Les champs mis en cache sont horodatés. Leur fraîcheur est exposée dans le
snapshot courant afin qu'une valeur lente ne soit pas confondue avec une mesure
instantanée.

## Calcul des kWh

Les énergies sont calculées par intégration trapézoïdale des puissances :

```text
kWh = moyenne(puissance précédente, puissance courante) × durée / 3 600 000
```

Chaque intervalle porte une qualité :

- `exact` : puissance directe et fraîche ;
- `derived` : puissance calculée, par exemple tension × courant ;
- `cached` : valeur provenant d'une commande plus lente ;
- `gap_integrated` : intervalle plus long que prévu mais encore intégré ;
- `gap_dropped` : trou trop long, énergie non ajoutée.

Une comparaison avec un compteur doit porter sur la même grandeur : l'import
réseau correspond à l'énergie tirée du réseau, tandis que la consommation de la
maison représente la charge vue en sortie de l'onduleur.

L'API de rapprochement accepte une période et, facultativement, les index d'un
compteur :

```text
GET /api/reconciliation?start=2026-06-01&end=2026-06-30&meter_import_kwh=123.4&meter_export_kwh=5.6
```

Elle renvoie les kWh PiPhocos, l'écart, la couverture temporelle et les
intervalles dégradés. Une requête est limitée à 400 jours.

## Stockage

Le stockage est organisé par niveaux :

| Donnée | Rôle | Conservation par défaut |
| --- | --- | --- |
| `current_snapshot` | Dernière mesure | 1 ligne |
| `samples` | Points bruts du direct | 6 heures |
| `compressed_samples_10m` | Courbes historiques | Durable |
| `derived_energy_intervals` | Recalcul détaillé récent | 45 jours |
| résumés jour, mois et année | Totaux énergétiques | Durable |
| résumés de qualité journaliers | Couverture des rapprochements | Durable |

Un intervalle détaillé n'est purgé que lorsque ses résumés d'énergie et de
qualité existent. La copie JSON brute de chaque mesure reste désactivée par
défaut : les colonnes structurées suffisent au fonctionnement courant.

## Contrôles utiles

Lancer les tests avant un changement de cadence ou de stockage :

```bash
python3 -m pytest -q
```

Mesurer l'acquisition, la liaison série et SQLite :

```bash
python3 scripts/acquisition_report.py --db data/db.sqlite --minutes 30 --days 1
python3 scripts/phocos_serial_benchmark.py --port /dev/serial/by-id/<adaptateur> --samples 120 --interval 0 --qpigs-every 5 --qpiws-every 120
python3 scripts/storage_benchmark.py --samples 1000 --interval 1
python3 scripts/compression_report.py --db data/db.sqlite --interval-retention-days 45
```

Contrôler les surfaces publiques et l'état du service :

```bash
python3 scripts/privacy_scan.py
python3 scripts/public_language_scan.py
curl -fsS http://127.0.0.1:5000/api/live
sqlite3 data/db.sqlite "PRAGMA integrity_check; PRAGMA wal_checkpoint(PASSIVE);"
```

## Maintenance prudente

Créer une sauvegarde SQLite avant toute maintenance qui modifie les données :

```bash
mkdir -p data/backups
sqlite3 data/db.sqlite ".backup 'data/backups/db-before-maintenance.sqlite'"
```

Prévisualiser une purge des intervalles détaillés :

```bash
python3 scripts/prune_energy_intervals.py --db data/db.sqlite --retention-days 45 --max-days 14
```

Ajouter `--apply` seulement après sauvegarde et contrôle du rapport. Si des
résumés de qualité manquent, les reconstruire hors de la boucle d'acquisition :

```bash
python3 scripts/rebuild_quality_summaries.py --db data/db.sqlite
```

Après une grosse purge, SQLite réutilise les pages libres. Ne lancer `VACUUM`
que pendant une maintenance, collecteur arrêté et sauvegarde effectuée.

Revenir à la dernière configuration stable en cas de retards répétés, de base
verrouillée, de WAL incontrôlé, de redémarrage du conteneur ou de données live
figées. Ne restaurer la base que si son contrôle d'intégrité échoue.
