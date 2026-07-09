# Installation Synology NAS

PiPhocos peut fonctionner sur Synology via Container Manager ou `docker compose`
en SSH. Le point sensible est le passage USB/RS232 : il depend fortement du
modele de NAS et de la version DSM.

Si le NAS n'expose pas l'adaptateur serie de maniere fiable, utiliser plutot un
Raspberry Pi ou un autre hote Linux proche de l'onduleur.

## Prerequis

- DSM avec Container Manager ou Docker.
- Acces SSH au NAS.
- Adaptateur USB/RS232 reconnu par le NAS.

## 1. Verifier l'adaptateur serie

```bash
ls -l /dev/serial/by-id/
```

ou :

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Si aucun peripherique serie n'apparait, DSM ne l'expose probablement pas au
conteneur.

## 2. Preparer les fichiers

Depuis le dossier du projet :

```bash
mkdir -p data
cp templates/config.yml data/config.yml
```

Modifier `data/config.yml` :

- `phocos.serial_port`
- `device.start_date`
- `instance.name` si necessaire

Conserver `privacy.expose_device_identifiers: false` pour masquer les
identifiants materiels dans les reponses HTTP.

## 3. Exemple Compose

Utiliser [`templates/docker-compose.yml`](../templates/docker-compose.yml) comme
base et verifier que le chemin du peripherique correspond au NAS :

```yaml
services:
  piphocos:
    image: piphocos:latest
    build:
      context: .
      dockerfile: dockerfile
    restart: unless-stopped
    ports:
      - "${PIPHOCOS_HTTP_BIND:-127.0.0.1}:5000:5000"
    volumes:
      - ./data:/data
    devices:
      - ${PIPHOCOS_SERIAL_PORT:-/dev/ttyUSB0}:${PIPHOCOS_SERIAL_PORT:-/dev/ttyUSB0}
```

Demarrer :

```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/votre-adaptateur
docker compose up --build -d piphocos
```

Pour ouvrir le tableau de bord sur un LAN de confiance :

```bash
export PIPHOCOS_HTTP_BIND=<ip-lan-du-nas>
docker compose up --build -d piphocos
```

PiPhocos n'integre pas d'authentification. Ne pas exposer le port HTTP sur
Internet; utiliser un VPN ou un reverse proxy authentifie.

## 4. Ouvrir

- `http://localhost:5000` depuis le NAS.
- `http://<ip-lan-du-nas>:5000` depuis le LAN si `PIPHOCOS_HTTP_BIND` pointe
  vers cette adresse.

## Notes

- Les chemins stables `/dev/serial/by-id/...` sont preferables a `/dev/ttyUSB0`.
- Certains modeles Synology demandent des modules USB serie non disponibles par
  defaut.
- Pour une acquisition energetique precise, un Raspberry Pi dedie reste souvent
  plus previsible qu'un NAS partage.
