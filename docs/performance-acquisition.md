# Performance d'acquisition Phocos

Ce document decrit la strategie d'acquisition rapide de PiPhocos. L'objectif
principal est la qualite des kWh enregistres, pas la frequence de rafraichissement
de l'interface.

## Principe

Le protocole Phocos expose des commandes completes. Dans le code actuel,
`QPGS0` n'est pas decomposable champ par champ : `parse_qpgs_payload()` attend
un paquet fixe de 27 champs. L'optimisation consiste donc a choisir quelles
commandes completes envoyer souvent, et lesquelles garder lentes.

## Cadences recommandees

| Commande | Role | Utilite kWh | Cadence |
| --- | --- | --- | --- |
| `QPGS0` | Paquet live principal : charge maison, batterie, PV V/A, modes, defauts | Critique | A chaque poll, cible 1 s apres validation |
| `QPIGS` | Live complementaire : PV exact, injection reseau, temperature, bus | Critique si injection/export utilisee | 2-5 s si export actif; 30 s valide sur l'installation actuelle sans export actif |
| `QPIWS` | Alertes et warnings | Non critique pour kWh | 60-240 s |
| `QPIRI` | Parametres et limites de l'onduleur | Contexte uniquement | Demarrage, puis refresh manuel ou journalier |
| `QID` | Identite appareil | Non critique | Demarrage |
| `QFLAG` | Flags appareil | Diagnostic | Demarrage, puis lent |
| `QPI` | Protocole supporte | Demarrage | Demarrage |
| `QMOD` | Mode seul | Redondant avec `QPGS0` | Non requis en poll regulier |

## Points d'implementation

- Le port serie reste ouvert entre deux polls pour eviter le cout open/close.
- `QPGS0` est la boucle rapide obligatoire.
- `QPIGS` est cache et horodate; ses champs de puissance ne doivent pas etre
  traites comme frais au-dela de `phocos.max_cached_power_age_s`.
- Les donnees lentes restent disponibles dans le snapshot courant, mais leur
  fraicheur est exposee via `source_timestamps`, `source_ages_s` et
  `source_freshness`.
- Les capacites Phocos ne sont reecrites en base que lorsqu'elles changent.

## Stockage et API

- Le collecteur garde une connexion SQLite persistante.
- Chaque sample est ecrit dans une seule transaction.
- `ensure_schema()`, backfills lourds, compaction et rollups sont hors chemin
  d'acquisition rapide.
- Les backfills automatiques sont bornes. Si une ancienne base depasse le seuil,
  le demarrage continue et une reconstruction manuelle est requise.
- SQLite tourne en WAL avec checkpoint planifie; le WAL est tronque seulement
  s'il depasse le seuil configure.
- La copie JSON brute par sample est desactivee par defaut avec
  `database.store_sample_raw_snapshot_json: false`. Les colonnes structurees et
  `current_snapshot` suffisent au fonctionnement courant; activer cette option
  seulement pour un diagnostic local ponctuel.
- `derived_energy_intervals.quality` est une colonne materialisee pour eviter
  de parser `derived_json` dans les rapports.
- Les buckets de compaction sont materialises dans `archive_bucket_local` pour
  eviter les filtres sur expression non indexee.
- L'API `/api/period` peut exclure `high_res` avec `include_high_res=0`; le
  front l'utilise pendant les refreshs live.
- L'API `/api/reconciliation` est limitee a 400 jours. Pour les plages de jours
  complets, elle additionne les jours deja resumes dans
  `energy_quality_summary_days` et les intervalles detailles restants. Une
  compression ancienne ne doit donc pas retirer des kWh d'un rapport facture.
- Les exports CSV bruts exigent `start` et `end`, sont bornes avant reponse,
  puis diffuses en streaming pour eviter de materialiser tout le fichier en
  memoire. Les exports larges doivent utiliser les buckets agreges.
- `scripts/acquisition_report.py` donne un etat rapide des gaps, de la qualite
  des intervalles et de la taille WAL.
- `scripts/phocos_serial_benchmark.py` mesure directement la latence des
  commandes serie, sans serveur web ni stockage.
- `scripts/storage_benchmark.py` mesure le cout SQLite par sample sur une base
  temporaire. L'option `--store-raw-snapshot` sert a mesurer le surcout du JSON
  brut par sample avant de l'activer.
- `scripts/compression_report.py` mesure en lecture seule les tables, index et
  jours candidats a la purge des intervalles detailles.
- `scripts/rebuild_quality_summaries.py` reconstruit
  `energy_quality_summary_days` hors boucle d'acquisition et hors requete web.
- `scripts/privacy_scan.py` bloque les fuites d'environnement dans les surfaces
  publiques du depot.
- `scripts/public_language_scan.py` bloque le retour des anciennes phrases
  anglaises visibles dans la documentation et l'interface statique.

## Confidentialite par defaut

Les numeros de serie, IDs appareil et payloads bruts de capacites ne sont pas
exposes par les reponses HTTP tant que
`privacy.expose_device_identifiers: false`. Les valeurs restent dans le snapshot
courant local. L'historique par sample evite de dupliquer le JSON complet, sauf
si `database.store_sample_raw_snapshot_json` est active volontairement.

## Limites physiques

L'adaptateur RS232 fonctionne a 2400 bauds. Lire `QPGS0` et `QPIGS` a chaque
seconde peut etre trop serre selon le temps de reponse de l'onduleur. La cible
realiste est d'abord `QPGS0` stable a 1 s, puis `QPIGS` a une cadence separee.

Mesure reelle sur l'installation locale apres optimisation : `QPGS0` a 1 s et
`QPIGS` toutes les 30 s donnent un p95 de gap sample autour de 1,17 s et un
maximum inferieur a 2 s sur la fenetre de test. La cible 0,5 s provoque des
retards continus et n'est pas retenue en production.

Source produit : manuel officiel Phocos Any-Grid PSW-H
<https://www.phocos.com/wp-content/uploads/2019/10/Any-Grid_PSW-H_EN-manual_2022-02-21.pdf>.
