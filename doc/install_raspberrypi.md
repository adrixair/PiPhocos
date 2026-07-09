# Installation Raspberry Pi

Le Raspberry Pi est le chemin de deploiement principal pour une acquisition
stable en USB/RS232.

## Prerequis

- Raspberry Pi avec Docker et Docker Compose.
- Adaptateur USB/RS232 relie au Phocos.
- Acces terminal au Raspberry Pi.

## 1. Identifier l'adaptateur serie

```bash
ls -l /dev/serial/by-id/
```

Si le dossier est vide :

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Preferer un chemin stable sous `/dev/serial/by-id/` quand il existe.

## 2. Recuperer le projet

```bash
git clone <url-du-repot-git>
cd PiPhocos
mkdir -p data
cp templates/config.yml data/config.yml
```

## 3. Configurer

Modifier `data/config.yml` :

- `phocos.serial_port`
- `device.start_date`
- `prices.price_per_grid_kwh`
- `prices.revenue_per_fed_in_kwh`

Laisser `privacy.expose_device_identifiers: false` pour ne pas exposer le
numero de serie ou l'ID appareil dans l'API et l'interface.

## 4. Demarrer

```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/votre-adaptateur
docker compose up --build -d piphocos
```

Si l'adaptateur est simplement `/dev/ttyUSB0`, utiliser cette valeur.

Par defaut, le service HTTP est publie sur `127.0.0.1`. Pour ouvrir le tableau
de bord sur un reseau local de confiance :

```bash
export PIPHOCOS_HTTP_BIND=<ip-lan-du-raspberry-pi>
docker compose up --build -d piphocos
```

PiPhocos n'integre pas d'authentification. Ne pas exposer le port HTTP sur
Internet; utiliser un VPN ou un reverse proxy authentifie.

## 5. Ouvrir le tableau de bord

- `http://localhost:5000` depuis le Raspberry Pi.
- `http://<ip-lan-du-raspberry-pi>:5000` depuis le LAN si
  `PIPHOCOS_HTTP_BIND` pointe vers cette adresse.

## Diagnostic rapide

- Verifier que `phocos.serial_port` et `PIPHOCOS_SERIAL_PORT` pointent vers le
  meme adaptateur.
- Si l'interface s'ouvre mais reste vide, lire `data/server.log` et
  `data/grabber.log`.
- En cas de doute base de donnees :

```bash
sqlite3 data/db.sqlite "PRAGMA integrity_check; PRAGMA wal_checkpoint(PASSIVE);"
```
