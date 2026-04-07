import logging
from typing import Any

import serial

from phocos_protocol import (
    SUPPORTED_READ_COMMANDS,
    build_command_frame,
    decode_frame,
    parse_probe_payload,
    parse_qpgs_payload,
    utc_now_iso,
)


class Phocos:
    def __init__(self, config):
        phocos_config = config.config_data["phocos"]
        self.serial_port = phocos_config["serial_port"]
        self.unit = int(phocos_config["unit"])
        self.timeout_s = float(phocos_config["timeout_s"])
        self.enable_pi30_probe = bool(phocos_config["enable_pi30_probe"])
        self.verbose_protocol_logging = bool(
            phocos_config["verbose_protocol_logging"]
        )
        grabber_config = config.config_data.get("grabber", {})
        poll_interval_s = max(
            float(grabber_config.get("interval_s", 20.0) or 20.0),
            1.0,
        )
        self.poll_counter = 0
        # Keep warning refreshes on roughly the same cadence as before
        # switching the grabber to 1-second polling.
        self.warning_refresh_every_polls = max(
            int(round(240.0 / poll_interval_s)),
            1,
        )
        # QPGS is the lightweight base poll; keep QPIGS on a slower cadence
        # in 1-second mode so the serial link can stay close to real time.
        if poll_interval_s <= 1.0:
            self.live_extension_refresh_every_polls = max(
                int(round(3.0 / poll_interval_s)),
                1,
            )
        elif poll_interval_s <= 2.0:
            # Keep 2-second polling stable on the Pi by reusing the heavier
            # QPIGS extension payload every other cycle.
            self.live_extension_refresh_every_polls = 2
        else:
            self.live_extension_refresh_every_polls = 1
        self.capabilities: dict[str, dict[str, Any]] = {}
        self.cached_probe_payloads: dict[str, dict[str, Any]] = {}
        self.cached_live_payloads: dict[str, dict[str, Any]] = {}

    def _open_port(self):
        return serial.Serial(
            port=self.serial_port,
            baudrate=2400,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout_s,
            write_timeout=self.timeout_s,
        )

    def _read_command(self, ser, command: str) -> dict[str, Any]:
        request_frame = build_command_frame(command)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(request_frame)
        ser.flush()
        response = ser.read_until(b"\r", size=1024)
        if not response:
            raise TimeoutError(f"No response received for {command}")

        decoded = decode_frame(response)
        if not decoded["crc_ok"]:
            raise ValueError(f"CRC mismatch for {command}")

        if command == f"QPGS{self.unit}":
            parsed = parse_qpgs_payload(decoded["payload_ascii"])
            command_name = "QPGS0"
        else:
            parsed = parse_probe_payload(command, decoded["payload_ascii"])
            command_name = command

        result = {
            "command": command_name,
            "request_hex": request_frame.hex(" ").upper(),
            "response_hex": response.hex(" ").upper(),
            "payload_ascii": decoded["payload_ascii"],
            "crc_ok": decoded["crc_ok"],
            "parsed": parsed,
        }
        if self.verbose_protocol_logging:
            logging.debug(
                "Phocos protocol %s tx=%s rx=%s",
                command_name,
                result["request_hex"],
                result["response_hex"],
            )
        return result

    def _set_capability(self, command: str, supported: bool, result=None, error=None):
        parsed = (result or {}).get("parsed") if result else None
        payload_ascii = (result or {}).get("payload_ascii") if result else None
        protocol_id = None
        if parsed and command == "QPI":
            protocol_id = parsed.get("protocol_id")
        elif self.capabilities.get("QPI"):
            protocol_id = self.capabilities["QPI"].get("protocol_id")
        self.capabilities[command] = {
            "supported": supported,
            "checked_at": utc_now_iso(),
            "protocol_id": protocol_id,
            "field_count": parsed.get("field_count") if parsed else None,
            "crc_ok": (result or {}).get("crc_ok", False),
            "response_preview": (payload_ascii or "")[:160],
            "raw_payload": payload_ascii,
            "parsed": parsed if supported else {"error": str(error)} if error else None,
        }

    def _cache_probe_result(self, command: str, parsed: dict[str, Any]):
        if command == "QPI":
            self.cached_probe_payloads["QPI"] = parsed
        elif command == "QID":
            self.cached_probe_payloads["QID"] = parsed
        elif command == "QFLAG":
            self.cached_probe_payloads["QFLAG"] = parsed
        elif command == "QPIWS":
            self.cached_probe_payloads["QPIWS"] = parsed
        elif command == "QPIRI":
            self.cached_probe_payloads["QPIRI"] = parsed

    def probe_capabilities(self, ser):
        probe_order = ("QPI",) + SUPPORTED_READ_COMMANDS[1:]
        for command in probe_order:
            try:
                result = self._read_command(ser, command)
                parsed = result["parsed"]
                self._set_capability(command, True, result=result)
                self._cache_probe_result(command, parsed)
                if command == "QPI" and parsed.get("protocol_id") != "PI30":
                    break
            except Exception as exc:
                self._set_capability(command, False, error=exc)

    def _refresh_live_extensions(self, ser, frames, snapshot):
        if self.capabilities.get("QPIGS", {}).get("supported") and (
            "QPIGS" not in self.cached_live_payloads
            or self.poll_counter == 0
            or self.poll_counter % self.live_extension_refresh_every_polls == 0
        ):
            result = self._read_command(ser, "QPIGS")
            frames.append(result)
            self.cached_live_payloads["QPIGS"] = result["parsed"]

        qpigs_payload = self.cached_live_payloads.get("QPIGS")
        if qpigs_payload:
            for key, value in qpigs_payload.items():
                if key in {
                    "bus_voltage_v",
                    "inverter_temperature_c",
                    "battery_voltage_from_scc_v",
                    "pv_charging_power_w",
                    "pv_power_w",
                    "pv_power_semantics",
                    "qpigs_status_flags_raw",
                    "qpigs_status_flags",
                    "device_status2_raw",
                    "device_status2",
                    "solar_feed_to_grid_enabled",
                    "country_code",
                    "solar_feed_to_grid_power_w",
                    "line_status_code",
                    "unknown_status_code",
                } and key not in snapshot:
                    snapshot[key] = value

        if self.capabilities.get("QPIWS", {}).get("supported") and (
            self.poll_counter == 0
            or self.poll_counter % self.warning_refresh_every_polls == 0
        ):
            result = self._read_command(ser, "QPIWS")
            frames.append(result)
            self.cached_probe_payloads["QPIWS"] = result["parsed"]

        if self.capabilities.get("QID", {}).get("supported") and "QID" not in self.cached_probe_payloads:
            result = self._read_command(ser, "QID")
            frames.append(result)
            self.cached_probe_payloads["QID"] = result["parsed"]

        if self.capabilities.get("QPIRI", {}).get("supported") and "QPIRI" not in self.cached_probe_payloads:
            result = self._read_command(ser, "QPIRI")
            frames.append(result)
            self.cached_probe_payloads["QPIRI"] = result["parsed"]

        if self.capabilities.get("QFLAG", {}).get("supported") and "QFLAG" not in self.cached_probe_payloads:
            result = self._read_command(ser, "QFLAG")
            frames.append(result)
            self.cached_probe_payloads["QFLAG"] = result["parsed"]

    def poll(self) -> dict[str, Any]:
        frames = []
        recorded_at = utc_now_iso()
        with self._open_port() as ser:
            if not self.capabilities or self.enable_pi30_probe:
                if "QPI" not in self.capabilities:
                    self.probe_capabilities(ser)

            qpgs_result = self._read_command(ser, f"QPGS{self.unit}")
            frames.append(qpgs_result)
            self._set_capability("QPGS0", True, result=qpgs_result)

            snapshot = {
                "recorded_at": recorded_at,
                **qpgs_result["parsed"],
                "protocol_id": self.cached_probe_payloads.get("QPI", {}).get(
                    "protocol_id"
                ),
                "device_id": self.cached_probe_payloads.get("QID", {}).get(
                    "device_id"
                ),
                "metadata": {
                    "serial_port": self.serial_port,
                    "unit": self.unit,
                },
            }

            self._refresh_live_extensions(ser, frames, snapshot)

        if "QPIWS" in self.cached_probe_payloads:
            warning_data = self.cached_probe_payloads["QPIWS"]
            snapshot["warning_bitmap"] = warning_data.get("warning_bitmap")
            snapshot["warning_bits"] = warning_data.get("warning_bits")

        if "QFLAG" in self.cached_probe_payloads:
            flag_data = self.cached_probe_payloads["QFLAG"]
            snapshot["flag_blob"] = flag_data.get("flags")
            snapshot["flags"] = flag_data

        if "QPIRI" in self.cached_probe_payloads:
            snapshot["qpiri"] = self.cached_probe_payloads["QPIRI"]

        if "QID" in self.cached_probe_payloads and not snapshot.get("device_id"):
            snapshot["device_id"] = self.cached_probe_payloads["QID"].get("device_id")

        self.poll_counter += 1
        return {
            "snapshot": snapshot,
            "capabilities": self.capabilities,
            "raw_frames": frames,
        }
