# Raspberry Pi setup

This is the only documented deployment path for now.

## Before you start

You need:

- a Raspberry Pi with Docker installed
- your Phocos inverter connected through a USB / RS232 adapter
- access to the Raspberry Pi terminal

## 1. Find the adapter path

On the Raspberry Pi, run:

```bash
ls -l /dev/serial/by-id/
```

If this folder is empty, run:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Keep the path you find. You will need it in the next step.

## 2. Download the project

```bash
git clone https://github.com/adrixair/PiPhocos.git
cd PiPhocos
mkdir -p data
cp templates/config.yml data/config.yml
```

## 3. Edit the config

Open `data/config.yml` and change only:

- `phocos.serial_port`
- `device.start_date`
- `prices.price_per_grid_kwh`
- `prices.revenue_per_fed_in_kwh`

If you are not sure about the app name, keep the default.

## 4. Start PiPhocos

```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/your-adapter
docker compose up --build -d piphocos
```

If your adapter is simply `/dev/ttyUSB0`, use that instead.

## 5. Open the dashboard

Open one of these addresses:

- `http://localhost:5000` on the Raspberry Pi itself
- `http://<your-raspberry-pi-ip>:5000` from another device on the same network

## If it does not work

- Check that the adapter path in `data/config.yml` is correct.
- Check that the `PIPHOCOS_SERIAL_PORT` value matches the same path.
- If the dashboard opens but stays empty, check `data/server.log` and `data/grabber.log`.
