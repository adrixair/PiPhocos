import logging
from typing import Any, Optional

import serial

from phocos_protocol import (
    SEMANTICS_CACHED,
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
        poll_interval_s = max(float(grabber_config.get("interval_s", 20.0) or 20.0), 0.1)
        self.poll_counter = 0
        self.poll_interval_s = poll_interval_s
        self.warning_refresh_every_polls = max(
            int(round(float(phocos_config.get("warning_interval_s", 240.0)) / poll_interval_s)),
            1,
        )
        self.live_extension_refresh_every_polls = max(
            int(round(float(phocos_config.get("qpigs_interval_s", 5.0)) / poll_interval_s)),
            1,
        )
        self.static_refresh_every_polls = max(
            int(round(float(phocos_config.get("static_refresh_interval_s", 86400.0)) / poll_interval_s)),
            1,
        )
        self.max_cached_power_age_s = max(
            float(phocos_config.get("max_cached_power_age_s", 12.0) or 12.0),
            poll_interval_s,
        )
        self.capabilities: dict[str, dict[str, Any]] = {}
        self.cached_probe_payloads: dict[str, dict[str, Any]] = {}
        self.cached_live_payloads: dict[str, dict[str, Any]] = {}
        self.cached_payload_timestamps: dict[str, str] = {}
        self.cached_payload_poll_ids: dict[str, int] = {}
        self.capabilities_dirty = False
        self._serial = None

    def close(self):
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def _get_port(self):
        if self._serial is None or not getattr(self._serial, "is_open", True):
            self._serial = self._open_port()
        return self._serial

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

    def _read_optional_command(self, ser, command: str):
        try:
            return self._read_command(ser, command)
        except Exception as exc:
            logging.warning("Phocos optional command %s failed: %s", command, exc)
            return None

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
        self.capabilities_dirty = True

    def _cache_probe_result(self, command: str, parsed: dict[str, Any]):
        self.cached_payload_timestamps[command] = utc_now_iso()
        self.cached_payload_poll_ids[command] = self.poll_counter
        if command == "QPI":
            self.cached_probe_payloads["QPI"] = parsed
        elif command == "QID":
            self.cached_probe_payloads["QID"] = parsed
        elif command == "QFLAG":
            self.cached_probe_payloads["QFLAG"] = parsed
        elif command == "QPIWS":
            self.cached_probe_payloads["QPIWS"] = parsed
        elif command == "QPIGS":
            self.cached_live_payloads["QPIGS"] = parsed
        elif command == "QPIRI":
            self.cached_probe_payloads["QPIRI"] = parsed

    def probe_capabilities(self, ser):
        probe_order = tuple(
            command
            for command in SUPPORTED_READ_COMMANDS
            if command != "QMOD"
        )
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

    @staticmethod
    def _age_seconds(timestamp: Optional[str], now_iso: str) -> Optional[float]:
        if not timestamp:
            return None
        try:
            from datetime import datetime

            now = datetime.fromisoformat(now_iso)
            then = datetime.fromisoformat(timestamp)
            return max((now - then).total_seconds(), 0.0)
        except Exception:
            return None

    def _refresh_live_extensions(self, ser, frames, snapshot):
        if self.capabilities.get("QPIGS", {}).get("supported") and (
            "QPIGS" not in self.cached_live_payloads
            or (
                self.poll_counter > 0
                and self.poll_counter % self.live_extension_refresh_every_polls == 0
            )
        ):
            result = self._read_optional_command(ser, "QPIGS")
            if result is not None:
                frames.append(result)
                self.cached_live_payloads["QPIGS"] = result["parsed"]
                self.cached_payload_timestamps["QPIGS"] = utc_now_iso()
                self.cached_payload_poll_ids["QPIGS"] = self.poll_counter

        qpigs_payload = self.cached_live_payloads.get("QPIGS")
        if qpigs_payload:
            qpigs_at = self.cached_payload_timestamps.get("QPIGS")
            qpigs_age_s = self._age_seconds(qpigs_at, snapshot["recorded_at"])
            qpigs_current_poll = (
                self.cached_payload_poll_ids.get("QPIGS") == self.poll_counter
            )
            qpigs_fresh_for_power = (
                qpigs_age_s is not None
                and qpigs_age_s <= self.max_cached_power_age_s
            )
            qpigs_power_keys = {
                "pv_charging_power_w",
                "solar_feed_to_grid_power_w",
            }
            qpigs_diagnostic_keys = {
                "bus_voltage_v",
                "inverter_temperature_c",
                "battery_voltage_from_scc_v",
                "qpigs_status_flags_raw",
                "qpigs_status_flags",
                "device_status2_raw",
                "device_status2",
                "solar_feed_to_grid_enabled",
                "country_code",
                "line_status_code",
                "unknown_status_code",
            }
            if "pv_power_w" in qpigs_payload and qpigs_fresh_for_power:
                snapshot["pv_power_derived_w"] = snapshot.get("pv_power_w")
                snapshot["pv_power_exact_w"] = qpigs_payload["pv_power_w"]
                snapshot["pv_power_w"] = qpigs_payload["pv_power_w"]
                snapshot["pv_power_semantics"] = (
                    qpigs_payload.get(
                        "pv_power_semantics",
                        snapshot.get("pv_power_semantics"),
                    )
                    if qpigs_current_poll
                    else SEMANTICS_CACHED
                )
            for key, value in qpigs_payload.items():
                if (
                    key in qpigs_power_keys
                    and qpigs_fresh_for_power
                    and key not in snapshot
                ):
                    snapshot[key] = value
                elif key in qpigs_diagnostic_keys and key not in snapshot:
                    snapshot[key] = value
            snapshot.setdefault("source_timestamps", {})["QPIGS"] = qpigs_at
            snapshot.setdefault("source_ages_s", {})["QPIGS"] = qpigs_age_s
            snapshot.setdefault("source_freshness", {})["QPIGS"] = (
                "fresh"
                if qpigs_current_poll
                else "cached"
                if qpigs_fresh_for_power
                else "stale"
            )

        if self.capabilities.get("QPIWS", {}).get("supported") and (
            "QPIWS" not in self.cached_probe_payloads
            or (
                self.poll_counter > 0
                and self.poll_counter % self.warning_refresh_every_polls == 0
            )
        ):
            result = self._read_optional_command(ser, "QPIWS")
            if result is not None:
                frames.append(result)
                self.cached_probe_payloads["QPIWS"] = result["parsed"]
                self.cached_payload_timestamps["QPIWS"] = utc_now_iso()
                self.cached_payload_poll_ids["QPIWS"] = self.poll_counter

        should_refresh_static = (
            self.poll_counter > 0
            and self.poll_counter % self.static_refresh_every_polls == 0
        )

        if self.capabilities.get("QID", {}).get("supported") and (
            "QID" not in self.cached_probe_payloads or should_refresh_static
        ):
            result = self._read_optional_command(ser, "QID")
            if result is not None:
                frames.append(result)
                self.cached_probe_payloads["QID"] = result["parsed"]
                self.cached_payload_timestamps["QID"] = utc_now_iso()
                self.cached_payload_poll_ids["QID"] = self.poll_counter

        if self.capabilities.get("QPIRI", {}).get("supported") and (
            "QPIRI" not in self.cached_probe_payloads or should_refresh_static
        ):
            result = self._read_optional_command(ser, "QPIRI")
            if result is not None:
                frames.append(result)
                self.cached_probe_payloads["QPIRI"] = result["parsed"]
                self.cached_payload_timestamps["QPIRI"] = utc_now_iso()
                self.cached_payload_poll_ids["QPIRI"] = self.poll_counter

        if self.capabilities.get("QFLAG", {}).get("supported") and (
            "QFLAG" not in self.cached_probe_payloads or should_refresh_static
        ):
            result = self._read_optional_command(ser, "QFLAG")
            if result is not None:
                frames.append(result)
                self.cached_probe_payloads["QFLAG"] = result["parsed"]
                self.cached_payload_timestamps["QFLAG"] = utc_now_iso()
                self.cached_payload_poll_ids["QFLAG"] = self.poll_counter

    def poll(self) -> dict[str, Any]:
        frames = []
        try:
            ser = self._get_port()
            if not self.capabilities or self.enable_pi30_probe:
                if "QPI" not in self.capabilities:
                    self.probe_capabilities(ser)

            qpgs_result = self._read_command(ser, f"QPGS{self.unit}")
            recorded_at = utc_now_iso()
            frames.append(qpgs_result)
            if "QPGS0" not in self.capabilities:
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
                    "poll_interval_s": self.poll_interval_s,
                    "qpigs_interval_s": self.live_extension_refresh_every_polls
                    * self.poll_interval_s,
                    "warning_interval_s": self.warning_refresh_every_polls
                    * self.poll_interval_s,
                    "max_cached_power_age_s": self.max_cached_power_age_s,
                },
                "source_timestamps": {"QPGS0": recorded_at},
                "source_ages_s": {"QPGS0": 0.0},
                "source_freshness": {"QPGS0": "fresh"},
            }

            self._refresh_live_extensions(ser, frames, snapshot)
        except Exception:
            self.close()
            raise

        if "QPIWS" in self.cached_probe_payloads:
            warning_data = self.cached_probe_payloads["QPIWS"]
            snapshot["warning_bitmap"] = warning_data.get("warning_bitmap")
            snapshot["warning_bits"] = warning_data.get("warning_bits")
            snapshot.setdefault("source_timestamps", {})["QPIWS"] = (
                self.cached_payload_timestamps.get("QPIWS")
            )

        if "QFLAG" in self.cached_probe_payloads:
            flag_data = self.cached_probe_payloads["QFLAG"]
            snapshot["flag_blob"] = flag_data.get("flags")
            snapshot["flags"] = flag_data

        if "QPIRI" in self.cached_probe_payloads:
            snapshot["qpiri"] = self.cached_probe_payloads["QPIRI"]

        if "QID" in self.cached_probe_payloads and not snapshot.get("device_id"):
            snapshot["device_id"] = self.cached_probe_payloads["QID"].get("device_id")

        self.poll_counter += 1
        capabilities_changed = self.capabilities_dirty
        self.capabilities_dirty = False
        return {
            "snapshot": snapshot,
            "capabilities": self.capabilities,
            "capabilities_changed": capabilities_changed,
            "raw_frames": frames,
        }
