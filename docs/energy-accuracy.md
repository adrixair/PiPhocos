# Precision energetique et reconciliation kWh

PiPhocos calcule les kWh en integrant des puissances echantillonnees. Pour
reduire l'ecart avec les factures ou compteurs reels, il faut optimiser a la
fois la cadence d'acquisition et la qualite des intervalles integres.

## Chemin de calcul actuel

Les intervalles energetiques sont calcules par integration trapezoidale :

```text
kWh = moyenne(puissance precedente, puissance courante) * duree / 3 600 000
```

Les principales entrees sont :

- `ac_output_active_power_w` pour la charge de la maison ou des appareils.
- `pv_power_w` pour la production solaire.
- `battery_charge_power_w` et `battery_discharge_power_w` pour la batterie.
- `solar_feed_to_grid_power_w` pour l'injection reseau quand `QPIGS` est frais.

## Qualite d'intervalle

Chaque intervalle doit etre interprete avec sa qualite :

- `exact` : donnees de puissance directes et fraiches.
- `derived` : puissance derivee, par exemple tension * courant.
- `cached` : valeur issue d'une commande plus lente.
- `gap_integrated` : intervalle plus long que prevu mais encore integre.
- `gap_dropped` : intervalle trop long ou inversion temporelle, kWh non ajoutes.

La politique d'acquisition rapide utilise `grabber.max_integrated_gap_s`. Si la
valeur n'est pas configuree, le grabber utilise environ trois intervalles
d'acquisition. `grabber.max_gap_for_cumulative_s` reste utile pour classer une
coupure plus longue, mais ne doit pas signifier que l'energie du trou est fiable.

## Sources d'ecart possibles

- Le compteur officiel peut mesurer l'import/export reseau, alors que
  `load_energy_kwh` mesure la charge sortie onduleur.
- `QPGS0` fournit une puissance PV derivee de la tension et du courant.
- `QPIGS` peut fournir une puissance PV exacte et une injection reseau, mais a
  une cadence differente.
- Les courants batterie sont arrondis; les watts batterie sont donc derives.
- Des gaps longs reduisent fortement la precision si on les integre comme des
  valeurs stables.

## Reconciliation facture

Pour comparer correctement :

- Import compteur reseau : comparer a `grid_to_load_energy_kwh +
  grid_to_battery_energy_kwh`.
- Export/injection : comparer a `grid_export_energy_kwh`.
- Production solaire : comparer a un compteur/information PV, pas a la facture
  reseau si celle-ci ne mesure que l'import/export.
- Consommation maison : comparer a `load_energy_kwh`, en tenant compte de ce
  que le Phocos voit ou ne voit pas.

L'API expose le rapport a la demande :

```text
GET /api/reconciliation?start=2026-06-01&end=2026-06-30&meter_import_kwh=123.4&meter_export_kwh=5.6
```

`start` accepte aussi `from` ou `debut`; `end` accepte aussi `to` ou `fin`. Si
`end` est une date sans heure, elle est traitee comme une date incluse et la
borne technique devient le lendemain a 00:00 en fuseau local. Les compteurs
peuvent aussi etre passes avec `compteur_import_kwh` et
`compteur_export_kwh`. Une requete est limitee a 400 jours; comparer plusieurs
annees se fait par periodes separees.

Le rapport inclut :

- periode fermee comparee;
- kWh PiPhocos;
- kWh compteur ou facture;
- ecart absolu;
- ecart en pourcentage;
- secondes couvertes;
- secondes manquantes;
- nombre d'intervalles `gap_dropped` et `gap_integrated`.

Pour les factures ou releves sur jours complets, la reconciliation utilise le
rollup `energy_quality_summary_days` pour les jours deja resumes et relit les
intervalles detailles uniquement pour les jours qui ne sont pas encore resumes.
L'API reste en lecture seule pendant un `GET`, mais elle sait additionner les
deux sources sur une meme periode. Pour preparer une base ancienne, lancer hors
acquisition :

```bash
python3 scripts/rebuild_quality_summaries.py --db data/db.sqlite
```

## Compression des donnees

Les donnees sont conservees par niveaux :

- `samples` : points bruts recents a la seconde pour le graphe live et les
  exports tres detailles. Retention par defaut : 6 h.
- `compressed_samples_10m` : points moyens de graphe toutes les 10 minutes pour
  l'historique long.
- `derived_energy_intervals` : intervalles kWh detailles, utiles au recalcul
  recent et a l'audit fin. Retention par defaut : 45 jours.
- `energy_summary_days`, `energy_summary_months`, `energy_summary_years` :
  totaux energetiques conserves durablement.
- `energy_quality_summary_days` : couverture et qualite par jour, conservees
  durablement pour les rapprochements facture.

La purge des intervalles detailles est prudente : un jour n'est supprime de
`derived_energy_intervals` que si le resume energetique du jour et son resume
qualite existent deja. Les anciennes donnees restent donc exploitables pour les
totaux, les graphes et la reconciliation, mais elles ne gardent plus chaque
intervalle seconde.

Pour inspecter une base avant ou apres compression :

```bash
python3 scripts/compression_report.py --db data/db.sqlite --interval-retention-days 45
```

## Donnees a conserver

Les echantillons bruts recents doivent rester disponibles assez longtemps pour
recalculer les deltas apres correction d'algorithme. Les rollups long terme sont
la source durable pour l'interface et la facture; les intervalles detailles sont
une fenetre de recalcul recente, pas l'archive infinie.

La copie JSON complete de chaque sample n'est pas necessaire pour ce calcul :
les colonnes structurees et les intervalles derives suffisent. Elle reste
activable avec `database.store_sample_raw_snapshot_json: true` uniquement pour
un diagnostic prive, car elle augmente fortement le volume a haute cadence.
