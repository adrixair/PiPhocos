<div align="center">

# PiPhocos

**Tableau de bord et enregistreur local pour Phocos Any-Grid sur Raspberry Pi.**

[![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-Compatible-C51A4A?style=for-the-badge&logo=raspberry-pi&logoColor=white)](https://www.raspberrypi.org/)
[![Accessibilité](https://img.shields.io/badge/Accessibilit%C3%A9-WCAG_2.1_AA-4CAF50?style=for-the-badge&logo=w3c&logoColor=white)](https://www.w3.org/WAI/)
[![Licence MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br>

<img src="doc/phocos-dashboard.webp" alt="Vue du tableau de bord PiPhocos avec des données de démonstration" width="90%">

<br>

PiPhocos collecte localement les données d'un onduleur Phocos Any-Grid,
calcule les kWh produits, consommés, chargés ou injectés, puis les expose dans
une application web locale. La priorité est la régularité de l'acquisition et
la précision énergétique ; l'interface peut volontairement se rafraîchir moins
souvent que le collecteur.

</div>

---

## Fonctionnalités

- **Acquisition locale** : communication USB/RS232 avec le Phocos, sans cloud.
- **Flux énergétique en direct** : solaire, maison, batterie et réseau avec sens
  des échanges et puissances instantanées.
- **Courbes interactives** : vue glissante sur 2 h, 4 h, 12 h ou 24 h avec
  séries activables séparément.
- **Historique énergétique** : bilans par jour, mois, année et depuis l'origine,
  avec production, consommation, autonomie, facture et économies estimées.
- **Priorité kWh** : boucle rapide centrée sur les puissances utiles aux calculs.
- **Qualité des intervalles** : distinction entre données exactes, dérivées,
  cachées, intégrées avec gap ou ignorées.
- **Interface responsive et accessible** : tableau de bord en français, adapté
  à l'ordinateur, à la tablette et au mobile, avec état de la dernière mesure.
- **Exports CSV** : récupération des données pour analyse externe.
- **PWA locale** : installation possible depuis un navigateur compatible.

---

## Captures

Toutes les valeurs visibles ci-dessous sont générées localement à partir d'un
scénario solaire fictif. Elles ne proviennent d'aucune installation réelle et
ne contiennent ni identifiant matériel ni donnée privée.

<div align="center">
  <table style="border-collapse: collapse; border: none;">
    <tr style="border: none;">
      <td width="50%" align="center" style="border: none;">
        <img src="doc/phocos-chart.webp" alt="Courbe de puissance PiPhocos avec des données de démonstration" width="100%">
        <br><i>Courbes de puissance sur 24 heures</i>
      </td>
      <td width="50%" align="center" style="border: none;">
        <img src="doc/phocos-daily.webp" alt="Bilan journalier PiPhocos avec des données de démonstration" width="100%">
        <br><i>Bilan énergétique journalier</i>
      </td>
    </tr>
  </table>
</div>

---

## Installation rapide

Prérequis :

- un **Raspberry Pi** avec Docker et Docker Compose ;
- l'adaptateur **USB / RS232 Phocos** connecté au Pi ;
- un accès terminal au Raspberry Pi.

### 1. Identifier l'adaptateur

```bash
ls -l /dev/serial/by-id/
```

### 2. Préparer la configuration

```bash
git clone <url-du-depot-git>
cd PiPhocos
mkdir -p data
cp templates/config.yml data/config.yml
```

Modifier `data/config.yml`, notamment :

- `phocos.serial_port`
- `device.start_date`
- `prices.tariff` : `auto`, `flat`, `standard` ou `zen_weekend`.
- `prices.price_per_grid_kwh`
- `prices.revenue_per_fed_in_kwh`
- `prices.zen_weekend` si votre contrat distingue les heures semaine et les
  heures week-end/jours fériés.
- `prices.standard` si vous voulez simuler le Tarif Bleu option Base.
- `privacy.expose_device_identifiers` uniquement si vous acceptez d'afficher
  les identifiants matériels dans l'API et l'interface.
- `database.store_sample_raw_snapshot_json` doit rester `false` sauf diagnostic
  local ponctuel ; les colonnes structurées suffisent au calcul kWh.
- `database.raw_history_retention_hours` et
  `database.energy_interval_retention_days` pilotent la compression des points
  bruts et des intervalles kWh détaillés.

### 3. Démarrer

```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/votre-adaptateur
docker compose up --build -d piphocos
```

Par défaut, le service HTTP est publié sur `localhost` uniquement. Pour une
exposition sur un réseau local de confiance :

```bash
export PIPHOCOS_HTTP_BIND=<ip-lan-du-raspberry-pi>
docker compose up --build -d piphocos
```

### 4. Ouvrir le tableau de bord

- `http://localhost:5000` par défaut ;
- `http://<ip-du-raspberry-pi>:5000` si `PIPHOCOS_HTTP_BIND` pointe vers l'IP LAN ;
- une route locale ou un reverse proxy privé peut aussi exposer un nom local choisi
  par l'administrateur.

PiPhocos n'intègre pas d'authentification. Ne pas l'exposer directement sur
Internet ; utiliser un LAN de confiance, un VPN ou un proxy privé authentifié.

---

## Précision et performance

PiPhocos se concentre sur les mesures qui changent tout le temps : watts maison,
production solaire, charge/décharge batterie et import/export réseau. Les
commandes Phocos secondaires sont lues plus lentement pour ne pas ralentir la
boucle d'acquisition.

L'interface peut se rafraîchir moins vite que le collecteur. C'est volontaire :
la priorité est d'enregistrer les watts à une cadence stable pour réduire
l'écart kWh avec les compteurs ou factures.

Sur l'installation locale validée, le réglage retenu est `QPGS0` toutes les
1 seconde et `QPIGS` toutes les 30 secondes. La cadence 0,5 seconde reste un
stress test : elle provoque trop de retards sur le lien série 2400 bauds.

Le stockage est compressé par niveaux : points bruts récents pour le direct,
buckets de 10 minutes pour les graphes longs, intervalles kWh détaillés pour le
recalcul récent, puis résumés journaliers, mensuels et annuels conservés durablement.
Les intervalles anciens ne sont purgés qu'après création des résumés d'énergie et
de qualité, afin que les rapprochements avec les factures restent disponibles.

Documentation technique :

- [Performance d'acquisition](docs/performance-acquisition.md)
- [Précision énergétique et réconciliation kWh](docs/energy-accuracy.md)
- [Tarifs, factures et API compteur](docs/tarifs-facturation-api.md)
- [Compression et rétention des données](docs/storage-compression.md)
- [Plan de test performance](docs/operations/performance-test-plan.md)

---

## Ressources incluses

- [Guide Raspberry Pi](doc/install_raspberrypi.md)
- [Guide Synology NAS](doc/install_synology.md)
- [Modèle de configuration](templates/config.yml)
- [Rapport performance acquisition](scripts/acquisition_report.py)
- [Benchmark stockage local](scripts/storage_benchmark.py)
- [Rapport compression SQLite](scripts/compression_report.py)
- [Purge contrôlée des intervalles kWh](scripts/prune_energy_intervals.py)
- [Benchmark série Phocos](scripts/phocos_serial_benchmark.py)
- [Reconstruction des résumés de qualité](scripts/rebuild_quality_summaries.py)
- [Scan anonymisation](scripts/privacy_scan.py)
- [Scan langue publique](scripts/public_language_scan.py)
- Documentation protocole : utiliser la documentation officielle Phocos adaptée
  à votre modèle d'onduleur.

---

## Crédits

Ce projet descend du projet **Sunalyzer** de **Boris Brock (VanKurt)**. La base
initiale a été adaptée, réduite et optimisée pour un usage Phocos Any-Grid local
sur Raspberry Pi.

---

<div align="center">
  Publié sous <a href="LICENSE">licence MIT</a>
</div>
