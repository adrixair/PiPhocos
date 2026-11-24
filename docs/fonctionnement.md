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

La page **Stockage** affiche simplement l'espace libre et la taille des données,
avec des unités usuelles (Mo et Go). Elle se met à
jour automatiquement à l'ouverture puis chaque minute lorsqu'elle est visible.
Son API, `GET /api/storage`, conserve les détails techniques et lit des
métadonnées et les bornes indexées des bilans, sans parcourir toutes les mesures.

Sous 512 Mio libres (`database.min_free_space_mb`), le collecteur suspend les
nouvelles mesures et sa maintenance. Les bilans et courbes historiques restent
consultables en lecture seule ; aucune purge d'urgence ne supprime les anciennes
périodes. Une mesure d'espace impossible suspend aussi les écritures. L'interface
signale la pause seulement lorsqu'elle est effective. L'enregistrement reprend
automatiquement quand l'espace redevient suffisant ; les mesures de la pause
ne sont pas enregistrées ni reconstituées. Une erreur SQLite de saturation
annule l'opération en cours et déclenche une nouvelle tentative après 30 secondes.

La compression historique conserve un point moyen par tranche de 10 minutes
pour les courbes. Les kWh restent calculés et conservés séparément dans les
bilans d'énergie : compacter une courbe ne recalcule pas les kWh à partir de
ces seuls points moyens. L'archivage et le retrait des points bruts se font dans
une même transaction, pour éviter un historique partiellement compacté en cas
d'échec d'écriture.

Quand d'anciennes mesures sont supprimées, SQLite conserve généralement la
taille de son fichier et réutilise les pages libérées pour les données futures.
L'espace **réutilisable à l'intérieur de la base** est donc déjà compris dans
la taille du fichier ; ce n'est pas de l'espace libre supplémentaire sur le
disque. Réduire physiquement le fichier demande une maintenance distincte.

Les journées closes sont lues à partir de leurs bilans et de leurs courbes
compactées. Les bornes de la courbe sont calculées séparément dans chaque
source, avec des index sur le jour et l'horodatage, afin d'éviter de relire les
mesures récentes pour afficher une ancienne journée. L'interface conserve
jusqu'à 12 journées closes en mémoire pendant 5 minutes et limite les requêtes
de l'historique à 30 secondes avant de proposer de réessayer.

La maintenance évite la compression lorsqu'aucun point n'est à archiver et
limite l'optimisation des statistiques SQLite à une fois par heure. Ses logs
détaillent les durées de compression, agrégats, purge, optimisation et
checkpoint pour repérer les opérations qui retardent encore l'acquisition.

Les bilans courants ajoutent seulement les nouveaux intervalles depuis leur
dernier calcul validé. Le point de reprise est conservé avec les bilans et leur
qualité dans une même transaction. Une correction d'intervalles déjà résumés
invalide cette reprise ; le jour est recalculé lorsque ses détails sont encore
complets. Au changement de
jour, les derniers intervalles de la veille sont consolidés avant le nouveau
jour. Les bilans anciens restent conservés après la purge de leurs détails.

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

## Maintenance

L'application utilise directement sa base de mesures, sans système de copies
de précaution ni répertoire de sauvegardes. La protection contre la saturation
préserve l'historique en suspendant les nouvelles écritures.

Prévisualiser une purge des intervalles détaillés :

```bash
python3 scripts/prune_energy_intervals.py --db data/db.sqlite --retention-days 45 --max-days 14
```

Ajouter `--apply` seulement après contrôle du rapport. Si des
résumés de qualité manquent, les reconstruire hors de la boucle d'acquisition :

```bash
python3 scripts/rebuild_quality_summaries.py --db data/db.sqlite
```

Après une grosse purge, SQLite réutilise les pages libres. Ne lancer `VACUUM`
que pendant une maintenance, collecteur arrêté.

Revenir à la dernière configuration stable en cas de retards répétés, de base
verrouillée, de WAL incontrôlé, de redémarrage du conteneur ou de données live
figées. Vérifier l'intégrité de la base avant toute intervention sur celle-ci.
