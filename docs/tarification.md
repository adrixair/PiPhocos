# Tarification facultative

PiPhocos mesure d'abord des kWh physiques. La tarification sert uniquement à
produire des estimations en euros ; elle est facultative et doit être adaptée au
contrat de chaque installation.

Les prix changent selon le fournisseur, l'offre, la puissance souscrite, les
taxes et la période. Le modèle de configuration ne constitue donc pas une grille
tarifaire de référence. La facture de l'utilisateur fait foi.

## Modes disponibles

- `auto` conserve le comportement historique et utilise la source configurée
  lorsqu'elle est disponible ;
- `flat` applique un prix fixe au kWh ;
- `standard` permet une tarification de base avec abonnement ;
- `zen_weekend` distingue les périodes de semaine et de week-end.

Les champs correspondants sont décrits dans
[`templates/config.yml`](../templates/config.yml). Il faut remplacer les valeurs
d'exemple par celles du contrat concerné. Tant que ce n'est pas fait, les
montants affichés restent de simples exemples et ne doivent pas être considérés
comme une facture fiable.

Le revenu d'injection est lui aussi propre au contrat. Ne pas utiliser une
valeur générique pour recalculer un historique réel.

## Facture et économies

Les vues énergétiques distinguent :

- les kWh importés depuis le réseau ;
- le coût variable de ces kWh ;
- l'abonnement proratisé sur la période ;
- le revenu éventuel de l'injection ;
- les économies variables liées à l'autoconsommation.

L'abonnement peut entrer dans l'estimation de facture, mais il ne représente
pas une économie pour chaque kWh solaire ou batterie utilisé.

## Recalcul d'un historique

Une correction tarifaire ne modifie pas les kWh déjà enregistrés. Prévisualiser
d'abord le recalcul :

```bash
python3 scripts/reprice_energy_history.py --db data/db.sqlite --config data/config.yml
```

Après vérification et sauvegarde, appliquer les nouveaux montants :

```bash
python3 scripts/reprice_energy_history.py --db data/db.sqlite --config data/config.yml --apply
```

Les résumés journaliers conservent les grandeurs nécessaires aux tarifs simples,
même lorsque les anciens intervalles détaillés ont été purgés.

## Comparaison avec un compteur

Un relevé Enedis ou une facture peut être comparé aux kWh de PiPhocos avec
`/api/reconciliation`. Les données compteur ne sont pas toujours disponibles en
temps réel et leur période doit correspondre exactement à celle demandée à
PiPhocos.

Pour comprendre les grandeurs comparées et la qualité des intervalles, consulter
[Fonctionnement, précision et maintenance](fonctionnement.md).
