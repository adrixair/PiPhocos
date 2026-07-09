# Tarifs, factures et API compteur

PiPhocos calcule d'abord des kWh physiques. Le tarif sert ensuite a convertir
certains kWh en euros et a estimer une facture. Il ne faut pas confondre :

- les kWh import reseau, comparables aux index Enedis/EDF;
- les economies variables, calculees avec le prix du kWh evite;
- l'abonnement, qui est ajoute a la facture estimee avec un prorata journalier
  mais n'est pas evite par chaque kWh solaire ou batterie.

## Modes tarifaires disponibles

`prices.tariff: auto`

: conserve le comportement historique : Tempo si l'API Tempo configuree repond,
sinon `prices.price_per_grid_kwh`.

`prices.tariff: flat`

: applique un prix fixe a tous les kWh evites.

`prices.tariff: standard`

: applique le Tarif Bleu option Base. La grille officielle EDF applicable au
1er fevrier 2026 indique pour 9 kVA un abonnement mensuel de 19,56 EUR TTC et un
prix de 19,27 cts EUR TTC/kWh. Les puissances 9 a 36 kVA de l'option Base sont
indiquees comme mises en extinction pour les nouvelles souscriptions.

`prices.tariff: zen_weekend`

: applique l'offre Zen Week-End. La grille officielle EDF applicable aux
nouvelles souscriptions a compter du 16 mars 2026 indique pour 9 kVA un
abonnement mensuel de 19,56 EUR TTC, 21,80 cts EUR TTC/kWh en heures semaine et
16,37 cts EUR TTC/kWh en heures week-end. Si une facture expose les prix HT et
l'accise, `zen_weekend` peut etre calibre avec les lignes HT de la facture.

## Facture et economies

Les vues jour, mois, annee et total exposent :

- `bill_grid_import_kwh` : import reseau facture, incluant la maison et la
  charge batterie depuis le reseau;
- `bill_variable_eur` : cout estime des kWh importes;
- `bill_subscription_eur` : abonnement prorate sur la periode affichee;
- `bill_estimated_total_eur` : facture estimee avant revenu d'injection;
- `bill_net_after_injection_eur` : cout net estime apres revenu d'injection;
- `earned_savings` : economie variable grace a l'autoconsommation.

L'abonnement est donc bien dans la facture estimee, mais pas dans les economies.

## Sources de prix

Les prix changent dans le temps. Les valeurs par defaut sont des reperes de
configuration, pas une garantie permanente. Avant un recalcul historique long,
verifier :

- la grille officielle EDF Tarif Bleu;
- la grille officielle EDF Zen Week-End;
- la facture EDF, qui fait foi pour la periode facturee;
- les taxes applicables, notamment l'accise et la TVA.

## API et donnees compteur

EDF ne fournit pas une API publique simple pour recuperer les factures des
particuliers et recalculer automatiquement le contrat dans PiPhocos.

Enedis est la source officielle pour les donnees compteur Linky :

- l'espace client Enedis permet de consulter l'historique de consommation, la
  production, et les informations techniques et contractuelles du compteur;
- Data Connect est la plateforme API officielle pour des fournisseurs de
  services avec consentement client;
- pour un particulier, l'acces API direct n'est generalement pas ouvert comme
  une simple cle personnelle. Il faut passer par l'espace client ou par un
  intermediaire certifie/bridge.

Des passerelles comme Conso API ou certaines integrations domotiques donnent un
acces pratique aux donnees Linky apres consentement Enedis. Elles sont utiles
pour une reconciliation quotidienne, mais les donnees ne sont pas temps reel :
elles arrivent typiquement le lendemain.

## Recalcul historique

Si le contrat etait deja Zen Week-End depuis le debut de l'enregistrement,
recalculer les euros historiques est possible sans modifier les kWh :

```bash
python3 scripts/reprice_energy_history.py --db data/db.sqlite --config data/config.yml
python3 scripts/reprice_energy_history.py --db data/db.sqlite --config data/config.yml --apply
```

Le mode apercu affiche les jours et les prix qui seraient appliques. Le mode
`--apply` met a jour :

- les prix des intervalles detailles encore conserves;
- `earned_savings_eur` et `earned_feed_in_eur` dans les resumes journaliers;
- les resumes mensuels et annuels.

Les anciennes donnees detaillees deja purgees restent recalculables pour les
tarifs a prix journalier entier (`standard`, `flat`, `zen_weekend` sans heures
creuses) parce que les resumes journaliers gardent les kWh necessaires.
