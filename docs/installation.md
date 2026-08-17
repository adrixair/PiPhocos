# Installation

PiPhocos est prévu en priorité pour un Raspberry Pi relié à l'onduleur par un
adaptateur USB/RS232. Un autre hôte Linux peut convenir si le port série est
accessible de façon stable.

## Prérequis

- Docker et Docker Compose ;
- un adaptateur USB/RS232 reconnu par l'hôte ;
- un accès terminal ;
- le dépôt PiPhocos.

## Préparer le projet

Copier l'URL proposée par le bouton **Code** de GitHub, puis :

```bash
git clone <URL-du-dépôt>
cd PiPhocos
mkdir -p data
cp templates/config.yml data/config.yml
```

## Identifier le port série

Préférer un chemin stable sous `/dev/serial/by-id/` :

```bash
ls -l /dev/serial/by-id/
```

Si ce dossier est vide :

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

## Configurer

Seuls le port série et la date de début de l'installation sont indispensables
dans `data/config.yml` :

```yaml
device:
  start_date: 2024-01-01
phocos:
  serial_port: /dev/serial/by-id/votre-adaptateur
```

Les autres réglages ont des valeurs par défaut. En particulier, la tarification
est facultative et dépend du contrat de chaque utilisateur. Voir
[Tarification](tarification.md) uniquement si les estimations en euros sont
utiles.

Conserver `privacy.expose_device_identifiers: false` pour ne pas publier les
identifiants matériels dans l'API et l'interface.

## Démarrer

```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/votre-adaptateur
docker compose up --build -d piphocos
```

Avec un port simple, utiliser par exemple `/dev/ttyUSB0` à la place du chemin
`/dev/serial/by-id/...`.

Par défaut, le service HTTP écoute sur `127.0.0.1:5000`. Pour l'ouvrir sur un
réseau local de confiance :

```bash
export PIPHOCOS_HTTP_BIND=<ip-lan-du-raspberry-pi>
docker compose up --build -d piphocos
```

Ouvrir ensuite `http://localhost:5000` depuis l'hôte ou
`http://<ip-lan-du-raspberry-pi>:5000` depuis le LAN.

PiPhocos n'intègre pas d'authentification. Ne pas exposer son port directement
sur Internet ; utiliser un VPN ou un reverse proxy authentifié.

## Synology

PiPhocos peut fonctionner avec Container Manager ou Docker Compose en SSH. Le
point déterminant est la prise en charge USB/RS232 par le modèle de NAS et sa
version de DSM.

Utiliser [`templates/docker-compose.yml`](../templates/docker-compose.yml) comme
base et vérifier que le périphérique déclaré dans `devices` existe réellement
sur le NAS. Si DSM n'expose pas l'adaptateur série de façon fiable, préférer un
Raspberry Pi ou un autre hôte Linux proche de l'onduleur.

## Diagnostic

État du conteneur et journaux :

```bash
docker compose ps
docker compose logs --tail=100 piphocos
tail -n 100 data/server.log
tail -n 100 data/grabber.log
```

Vérification de l'API et de SQLite :

```bash
curl -fsS http://127.0.0.1:5000/api/live
sqlite3 data/db.sqlite "PRAGMA integrity_check; PRAGMA wal_checkpoint(PASSIVE);"
```

Si l'interface est vide, vérifier d'abord que `phocos.serial_port` et
`PIPHOCOS_SERIAL_PORT` désignent le même adaptateur, puis consulter
`data/grabber.log`.
