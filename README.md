<div align="center">

# ⚡ PiPhocos

**High-performance, local-first dashboard & monitor for Phocos Any-Grid on Raspberry Pi.**

[![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-Ready-C51A4A?style=for-the-badge&logo=raspberry-pi&logoColor=white)](https://www.raspberrypi.org/)
[![A11y](https://img.shields.io/badge/Accessibility-WCAG_2.1_AA-4CAF50?style=for-the-badge&logo=w3c&logoColor=white)](https://www.w3.org/WAI/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br>

<img src="doc/phocos-dashboard.webp" alt="PiPhocos dashboard overview" width="90%">

<br>

Live telemetry, battery status, energy history, and CSV export in one lightning-fast local web app. Designed as a Progressive Web App (PWA) compatible with both desktop and mobile devices.

</div>

---

## ✨ Features

- **📊 Real-time Monitoring:** Instant live telemetry for voltage, load, and battery metrics.
- **🔋 Battery Management:** Precise battery status tracking.
- **📈 Historical Data:** Comprehensive energy history over time.
- **⬇️ CSV Exports:** Easily export your data for external analysis.
- **🏠 Local First:** No reliance on cloud services. Your data stays entirely on your machine.
- **♿ Fully Accessible:** Built with accessibility (a11y) in mind, adhering to modern standards for an inclusive UI.

---

## 📸 Screenshots

<div align="center">
  <table style="border-collapse: collapse; border: none;">
    <tr style="border: none;">
      <td width="50%" align="center" style="border: none;">
        <img src="doc/phocos-chart.webp" alt="PiPhocos live chart view" width="100%">
        <br><i>Live Chart telemetry</i>
      </td>
      <td width="50%" align="center" style="border: none;">
        <img src="doc/phocos-daily.webp" alt="PiPhocos daily data view" width="100%">
        <br><i>Daily data breakdown</i>
      </td>
    </tr>
  </table>
</div>

---

## 🚀 Quick Start

You need:
- A **Raspberry Pi** with Docker and Docker Compose installed.
- The **Phocos USB / RS232 adapter** connected to the Pi.
- Terminal access to the Raspberry Pi.

### 1. Locate the adapter
Find the exact path of your connected adapter:
```bash
ls -l /dev/serial/by-id/
```

### 2. Download and configure
Clone the repository and prepare your config file:
```bash
git clone https://github.com/adrixair/PiPhocos.git
cd PiPhocos
mkdir -p data
cp templates/config.yml data/config.yml
```

Edit `data/config.yml` and explicitly update the core attributes:
- `phocos.serial_port`
- `device.start_date`
- `prices.price_per_grid_kwh`
- `prices.revenue_per_fed_in_kwh`

### 3. Deploy
Start the application using Docker Compose, passing the adapter path:
```bash
export PIPHOCOS_SERIAL_PORT=/dev/serial/by-id/your-adapter
docker compose up --build -d piphocos
```

By default, Docker publishes the dashboard on localhost only. To expose it on a trusted LAN, bind it to a specific LAN address:
```bash
export PIPHOCOS_HTTP_BIND=<your-raspberry-pi-lan-ip>
docker compose up --build -d piphocos
```

### 4. Access the Dashboard
Open your favorite browser and head to:
- `http://localhost:5000` by default
- `http://<your-raspberry-pi-ip>:5000` only when `PIPHOCOS_HTTP_BIND` is set to that LAN address

Security note: PiPhocos has no built-in authentication. Keep it on localhost, a trusted LAN address, or behind a private VPN/reverse proxy with authentication. Do not expose it directly to the public Internet. Leave `diagnostics.enabled` set to `false` in `data/config.yml` unless you need it temporarily.

---

## 🎯 Use Cases & Search Tags

This project is specifically tailored for **Off-Grid Solar** architectures using the **Phocos Any-Grid** series. It empowers solar enthusiasts, DIY engineers, and homeowners to monitor their energy infrastructure intuitively and privately.

**Keywords & Discoverability:** `Phocos Any-Grid PSW-H`, `Solar Inverter Dashboard`, `Off-Grid Solar Monitor`, `Raspberry Pi Solar Logger`, `MPPT Tracker Data`, `DIY Solar Telemetry`, `Battery Voltage Monitor`, `RS232 Inverter Communication`, `Local Solar Smart Home Framework`.

---

## 📚 Included Resources

- **Raspberry Pi setup guide:** [`doc/install_raspberrypi.md`](doc/install_raspberrypi.md)
- **Synology NAS setup guide:** [`doc/install_synology.md`](doc/install_synology.md)
- **Config template:** [`templates/config.yml`](templates/config.yml)
- **Protocol reference:** use the official Phocos protocol documentation for your inverter model.

---

## 🙏 Credits & Acknowledgements

This project was originally a fork of the **Sunalyzer** project by **Boris Brock (VanKurt)**. The initial codebase descends from his work, while this repository has been heavily narrowed, optimized, and standalone-refactored into a sleek Phocos Any-Grid monitoring path for Raspberry Pi. We thank Boris for the groundwork that made this project possible.

---

<div align="center">
  Released under the <a href="LICENSE">MIT License</a>
</div>
