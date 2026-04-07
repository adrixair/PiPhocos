# Synology NAS deployment

PiPhocos can run on Synology through Container Manager or `docker compose` over SSH, but USB serial passthrough depends on your NAS model and DSM version.

If your NAS cannot expose the inverter serial adapter reliably, run PiPhocos on a Raspberry Pi or another Linux host instead.

## Requirements

- DSM with Container Manager or Docker support
- SSH access to the NAS
- A USB-to-RS232 adapter recognized by the NAS

## 1. Confirm the serial adapter exists on the NAS

After connecting the adapter, check over SSH:

```bash
ls -l /dev/serial/by-id/
```

or:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

If no serial device appears, DSM is not exposing the adapter and PiPhocos will not be able to poll the inverter from this host.

## 2. Prepare the project files

Create a working directory on the NAS, then:

```bash
mkdir -p data
cp templates/config.yml data/config.yml
```

Update `data/config.yml`:

- set `phocos.serial_port`
- set `device.start_date`
- optionally set `instance.name`

## 3. Compose example

Use [`templates/docker-compose.yml`](../templates/docker-compose.yml) as the base and make sure the device path matches the host:

```yaml
services:
  piphocos:
    image: piphocos:latest
    build:
      context: .
      dockerfile: dockerfile
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/data
    devices:
      - ${PIPHOCOS_SERIAL_PORT:-/dev/ttyUSB0}:${PIPHOCOS_SERIAL_PORT:-/dev/ttyUSB0}
```

Start it with:

```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/your-adapter
docker compose up --build -d piphocos
```

## 4. Open the dashboard

Open `http://<nas-ip>:5000`.

## Notes

- Some Synology models require extra USB serial support not available by default.
- Stable `/dev/serial/by-id/...` paths are preferred over `/dev/ttyUSB0`.
- If you do not need the NAS specifically, the Raspberry Pi setup is usually simpler and more predictable.
