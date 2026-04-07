import datetime as _dt
from typing import Any


SUPPORTED_READ_COMMANDS = (
    "QPI",
    "QMOD",
    "QPIGS",
    "QPIRI",
    "QPIWS",
    "QFLAG",
    "QID",
)

SEMANTICS_EXACT = "exact"
SEMANTICS_DERIVED = "derived"
SEMANTICS_UNSUPPORTED = "unsupported"

MODE_MAP = {
    "P": "Powered on",
    "S": "Stand-By",
    "L": "Grid / Line mode",
    "B": "Off-grid / Battery mode",
    "F": "Fault mode",
    "D": "Shutdown mode",
}

FAULT_MAP = {
    "00": "No fault",
    "01": "Fan locked while inverter off",
    "02": "Over-temperature",
    "03": "Battery voltage too high",
    "04": "Battery voltage too low",
    "05": "AC output short-circuit",
    "06": "AC output voltage too high",
    "07": "AC output overload",
    "08": "Internal bus voltage too high",
    "09": "Internal bus soft-start failed",
    "10": "PV over-current",
    "11": "PV over-voltage",
    "12": "Internal DC converter over-current",
    "13": "Battery discharge over-current",
    "51": "Over-current",
    "52": "Internal bus voltage too low",
    "53": "Inverter soft-start failed",
    "55": "DC over-voltage at AC output",
    "57": "Current sensor failed",
    "58": "AC output voltage too low",
    "60": "Reverse-current protection active",
    "71": "Firmware version inconsistent",
    "72": "Current sharing fault",
    "80": "CAN communication fault",
    "81": "Host loss",
    "82": "Synchronization loss",
    "83": "Battery voltage detected inconsistent",
    "84": "AC in. voltage/frequency inconsistent",
    "85": "AC output current imbalance",
    "86": "AC output mode inconsistent",
}

CHARGER_PRIORITY_MAP = {
    "0": "Utility first",
    "1": "Solar first",
    "2": "Solar and Utility",
    "3": "Solar only",
}

OUTPUT_SOURCE_PRIORITY_MAP = {
    "0": "Utility first",
    "1": "Solar first",
    "2": "SBU",
    "3": "Battery first",
}

AC_OUTPUT_MODE_MAP = {
    "0": "Single Any-Grid unit",
    "1": "Parallel output",
    "2": "Phase 1 of 3-phase output",
    "3": "Phase 2 of 3-phase output",
    "4": "Phase 3 of 3-phase output",
}

BATTERY_STATE_MAP = {
    "00": "Battery voltage normal",
    "01": "Battery voltage low",
    "02": "Battery disconnected",
    "03": "Battery charging/discharging disabled by BMS",
}

BATTERY_TYPE_MAP = {
    "0": "AGM",
    "1": "Flooded",
    "2": "User defined",
    "3": "Lithium",
}

INPUT_VOLTAGE_RANGE_MAP = {
    "0": "Appliance",
    "1": "UPS",
}

MACHINE_TYPE_MAP = {
    "00": "Grid tie",
    "01": "Off-grid",
    "10": "Hybrid",
    "11": "Unknown hybrid variant",
}

TOPOLOGY_MAP = {
    "0": "Transformerless",
    "1": "Transformer",
}

PV_OK_CONDITION_MAP = {
    "0": "PV power at any level",
    "1": "PV power must exceed configured threshold",
}

PV_POWER_BALANCE_MAP = {
    "0": "PV power balance disabled",
    "1": "PV power balance enabled",
}


def utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def calculate_crc(payload: bytes) -> bytes:
    crc = 0
    crc_table = (
        0x0000, 0x1021, 0x2042, 0x3063,
        0x4084, 0x50A5, 0x60C6, 0x70E7,
        0x8108, 0x9129, 0xA14A, 0xB16B,
        0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    )

    for byte in payload:
        data = ((crc >> 8) >> 4) & 0xFF
        crc = ((crc << 4) & 0xFFFF) ^ crc_table[data ^ (byte >> 4)]
        data = ((crc >> 8) >> 4) & 0xFF
        crc = ((crc << 4) & 0xFFFF) ^ crc_table[data ^ (byte & 0x0F)]

    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    if crc_low in (0x28, 0x0D, 0x0A):
        crc_low = (crc_low + 1) & 0xFF
    if crc_high in (0x28, 0x0D, 0x0A):
        crc_high = (crc_high + 1) & 0xFF

    return bytes((crc_high, crc_low))


def build_command_frame(command: str) -> bytes:
    payload = command.encode("ascii")
    return payload + calculate_crc(payload) + b"\r"


def decode_frame(frame: bytes) -> dict[str, Any]:
    if len(frame) < 4:
        raise ValueError("frame too short")
    if not frame.endswith(b"\r"):
        raise ValueError("frame missing carriage return")

    payload = frame[:-3]
    recv_crc = frame[-3:-1]
    calc_crc = calculate_crc(payload)
    return {
        "payload_bytes": payload,
        "payload_ascii": payload.decode("ascii", "replace"),
        "crc_ok": recv_crc == calc_crc,
        "recv_crc_hex": recv_crc.hex().upper(),
        "calc_crc_hex": calc_crc.hex().upper(),
        "frame_hex": frame.hex(" ").upper(),
    }


def _parse_bitfield(bit_string: str) -> dict[str, Any]:
    bits = [bit == "1" for bit in bit_string]
    active_bits = [index for index, bit in enumerate(bit_string) if bit == "1"]
    return {
        "raw": bit_string,
        "length": len(bit_string),
        "bits": bits,
        "active_bits": active_bits,
    }


def parse_qpgs_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QPGS payload does not start with '('")

    parts = payload_ascii[1:].split(" ")
    if len(parts) != 27:
        raise ValueError(f"Unexpected QPGS field count: {len(parts)}")

    (
        other_units_connected_code,
        serial_number,
        operation_mode_code,
        fault_code,
        ac_input_voltage_v,
        ac_input_frequency_hz,
        ac_output_voltage_v,
        ac_output_frequency_hz,
        ac_output_apparent_power_va,
        ac_output_active_power_w,
        ac_output_load_percent,
        battery_voltage_v,
        battery_charge_current_a,
        battery_state_of_charge_percent,
        pv_input_voltage_v,
        total_charging_current_a,
        total_ac_output_apparent_power_va,
        total_output_active_power_w,
        total_output_load_percent,
        inverter_status_raw,
        ac_output_mode_code,
        battery_charger_source_priority_code,
        max_charging_current_set_a,
        max_charging_current_possible_a,
        max_ac_charging_current_set_a,
        pv_input_current_a,
        battery_discharge_current_a,
    ) = parts

    battery_state_code = inverter_status_raw[3:5]
    status = {
        "raw": inverter_status_raw,
        "mppt_active": inverter_status_raw[0] == "1",
        "ac_charging_on": inverter_status_raw[1] == "1",
        "solar_charging_on": inverter_status_raw[2] == "1",
        "battery_state_code": battery_state_code,
        "battery_state": BATTERY_STATE_MAP.get(battery_state_code, "Unknown"),
        "ac_input_available": inverter_status_raw[5] == "0",
        "ac_output_on": inverter_status_raw[6] == "1",
        "reserved_bit_b0": inverter_status_raw[7],
    }

    pv_power_w = float(pv_input_voltage_v) * float(pv_input_current_a)
    battery_charge_power_w = float(battery_voltage_v) * float(
        battery_charge_current_a
    )
    battery_discharge_power_w = float(battery_voltage_v) * float(
        battery_discharge_current_a
    )

    return {
        "command": "QPGS",
        "field_count": len(parts),
        "other_units_connected_code": other_units_connected_code,
        "other_units_connected": (
            "Single unit only"
            if other_units_connected_code == "0"
            else "Multiple units connected"
        ),
        "serial_number": serial_number,
        "operation_mode_code": operation_mode_code,
        "operation_mode": MODE_MAP.get(operation_mode_code, "Unknown"),
        "fault_code": fault_code,
        "fault": FAULT_MAP.get(fault_code, "Unknown"),
        "ac_input_voltage_v": float(ac_input_voltage_v),
        "ac_input_frequency_hz": float(ac_input_frequency_hz),
        "ac_output_voltage_v": float(ac_output_voltage_v),
        "ac_output_frequency_hz": float(ac_output_frequency_hz),
        "ac_output_apparent_power_va": int(ac_output_apparent_power_va),
        "ac_output_active_power_w": int(ac_output_active_power_w),
        "ac_output_load_percent": int(ac_output_load_percent),
        "battery_voltage_v": float(battery_voltage_v),
        "battery_charge_current_a": int(battery_charge_current_a),
        "battery_state_of_charge_percent": int(battery_state_of_charge_percent),
        "pv_input_voltage_v": float(pv_input_voltage_v),
        "total_charging_current_a": int(total_charging_current_a),
        "total_ac_output_apparent_power_va": int(
            total_ac_output_apparent_power_va
        ),
        "total_output_active_power_w": int(total_output_active_power_w),
        "total_output_load_percent": int(total_output_load_percent),
        "inverter_status": status,
        "ac_output_mode_code": ac_output_mode_code,
        "ac_output_mode": AC_OUTPUT_MODE_MAP.get(
            ac_output_mode_code, "Unknown"
        ),
        "battery_charger_source_priority_code":
            battery_charger_source_priority_code,
        "battery_charger_source_priority": CHARGER_PRIORITY_MAP.get(
            battery_charger_source_priority_code, "Unknown"
        ),
        "max_charging_current_set_a": int(max_charging_current_set_a),
        "max_charging_current_possible_a": int(max_charging_current_possible_a),
        "max_ac_charging_current_set_a": int(max_ac_charging_current_set_a),
        "pv_input_current_a": float(pv_input_current_a),
        "pv_power_w": round(pv_power_w, 3),
        "pv_power_semantics": SEMANTICS_DERIVED,
        "battery_charge_power_w": round(battery_charge_power_w, 3),
        "battery_charge_power_semantics": SEMANTICS_DERIVED,
        "battery_discharge_power_w": round(battery_discharge_power_w, 3),
        "battery_discharge_power_semantics": SEMANTICS_DERIVED,
        "battery_discharge_current_a": int(battery_discharge_current_a),
    }


def parse_qpigs_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QPIGS payload does not start with '('")

    parts = payload_ascii[1:].split(" ")
    if len(parts) < 17:
        raise ValueError(f"Unexpected QPIGS field count: {len(parts)}")

    data: dict[str, Any] = {
        "command": "QPIGS",
        "payload_fields": parts,
        "field_count": len(parts),
        "ac_input_voltage_v": float(parts[0]),
        "ac_input_frequency_hz": float(parts[1]),
        "ac_output_voltage_v": float(parts[2]),
        "ac_output_frequency_hz": float(parts[3]),
        "ac_output_apparent_power_va": int(parts[4]),
        "ac_output_active_power_w": int(parts[5]),
        "ac_output_load_percent": int(parts[6]),
        "bus_voltage_v": float(parts[7]),
        "battery_voltage_v": float(parts[8]),
        "battery_charge_current_a": int(parts[9]),
        "battery_state_of_charge_percent": int(parts[10]),
        "inverter_temperature_c": int(parts[11]),
        "pv_input_current_a": float(parts[12]),
        "pv_input_voltage_v": float(parts[13]),
        "battery_voltage_from_scc_v": float(parts[14]),
        "battery_discharge_current_a": int(parts[15]),
        "qpigs_status_flags_raw": parts[16],
        "qpigs_status_flags": _parse_bitfield(parts[16]),
    }

    if len(parts) > 17:
        data["line_status_code"] = parts[17]
    if len(parts) > 18:
        data["unknown_status_code"] = parts[18]
    if len(parts) > 19:
        data["pv_charging_power_w"] = int(parts[19])
        data["pv_power_w"] = int(parts[19])
        data["pv_power_semantics"] = SEMANTICS_EXACT
    if len(parts) > 20:
        data["device_status2_raw"] = parts[20]
        data["device_status2"] = _parse_bitfield(parts[20])
    if len(parts) > 21:
        data["solar_feed_to_grid_enabled"] = parts[21] == "1"
    if len(parts) > 22:
        data["country_code"] = parts[22]
    if len(parts) > 23:
        data["solar_feed_to_grid_power_w"] = int(parts[23])

    return data


def parse_qpiri_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QPIRI payload does not start with '('")

    parts = payload_ascii[1:].split(" ")
    if len(parts) < 23:
        raise ValueError(f"Unexpected QPIRI field count: {len(parts)}")

    data: dict[str, Any] = {
        "command": "QPIRI",
        "payload_fields": parts,
        "field_count": len(parts),
        "grid_rating_voltage_v": float(parts[0]),
        "grid_rating_current_a": float(parts[1]),
        "ac_output_rating_voltage_v": float(parts[2]),
        "ac_output_rating_frequency_hz": float(parts[3]),
        "ac_output_rating_current_a": float(parts[4]),
        "ac_output_rating_apparent_power_va": int(parts[5]),
        "ac_output_rating_active_power_w": int(parts[6]),
        "battery_rating_voltage_v": float(parts[7]),
        "battery_recharge_voltage_v": float(parts[8]),
        "battery_under_voltage_v": float(parts[9]),
        "battery_bulk_voltage_v": float(parts[10]),
        "battery_float_voltage_v": float(parts[11]),
        "battery_type_code": parts[12],
        "battery_type": BATTERY_TYPE_MAP.get(parts[12], "Unknown"),
        "max_ac_charging_current_a": int(parts[13]),
        "max_charging_current_a": int(parts[14]),
        "input_voltage_range_code": parts[15],
        "input_voltage_range": INPUT_VOLTAGE_RANGE_MAP.get(
            parts[15], "Unknown"
        ),
        "output_source_priority_code": parts[16],
        "output_source_priority": OUTPUT_SOURCE_PRIORITY_MAP.get(
            parts[16], "Unknown"
        ),
        "charger_source_priority_code": parts[17],
        "charger_source_priority": CHARGER_PRIORITY_MAP.get(
            parts[17], "Unknown"
        ),
        "max_parallel_units": int(parts[18]),
        "machine_type_code": parts[19],
        "machine_type": MACHINE_TYPE_MAP.get(parts[19], "Unknown"),
        "topology_code": parts[20],
        "topology": TOPOLOGY_MAP.get(parts[20], "Unknown"),
        "output_mode_code": parts[21],
        "output_mode": AC_OUTPUT_MODE_MAP.get(parts[21], "Unknown"),
        "battery_redischarge_voltage_v": float(parts[22]),
    }

    if len(parts) > 23:
        data["pv_ok_condition_code"] = parts[23]
        data["pv_ok_condition"] = PV_OK_CONDITION_MAP.get(
            parts[23], "Unknown"
        )
    if len(parts) > 24:
        data["pv_power_balance_code"] = parts[24]
        data["pv_power_balance"] = PV_POWER_BALANCE_MAP.get(
            parts[24], "Unknown"
        )
    if len(parts) > 25:
        data["cv_charge_time_minutes"] = int(parts[25])
    if len(parts) > 26:
        data["reserved_setting_26"] = parts[26]
    if len(parts) > 27:
        data["reserved_setting_27"] = parts[27]
    if len(parts) > 28:
        data["battery_redischarge_voltage_from_scc_v"] = float(parts[28])

    return data


def parse_qpiws_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QPIWS payload does not start with '('")
    raw = payload_ascii[1:]
    return {
        "command": "QPIWS",
        "warning_bitmap": raw,
        "warning_bits": _parse_bitfield(raw),
    }


def parse_qflag_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QFLAG payload does not start with '('")
    raw = payload_ascii[1:]
    return {
        "command": "QFLAG",
        "flags": raw,
        "flag_characters": list(raw),
    }


def parse_qid_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QID payload does not start with '('")
    return {
        "command": "QID",
        "device_id": payload_ascii[1:],
    }


def parse_qpi_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QPI payload does not start with '('")
    return {
        "command": "QPI",
        "protocol_id": payload_ascii[1:],
    }


def parse_qmod_payload(payload_ascii: str) -> dict[str, Any]:
    if not payload_ascii.startswith("("):
        raise ValueError("QMOD payload does not start with '('")
    mode_code = payload_ascii[1:2]
    return {
        "command": "QMOD",
        "mode_code": mode_code,
        "mode_label": MODE_MAP.get(mode_code, "Unknown"),
    }


def parse_probe_payload(command: str, payload_ascii: str) -> dict[str, Any]:
    if command == "QPI":
        return parse_qpi_payload(payload_ascii)
    if command == "QMOD":
        return parse_qmod_payload(payload_ascii)
    if command == "QPIGS":
        return parse_qpigs_payload(payload_ascii)
    if command == "QPIRI":
        return parse_qpiri_payload(payload_ascii)
    if command == "QPIWS":
        return parse_qpiws_payload(payload_ascii)
    if command == "QFLAG":
        return parse_qflag_payload(payload_ascii)
    if command == "QID":
        return parse_qid_payload(payload_ascii)

    return {
        "command": command,
        "raw": payload_ascii,
    }


def bucket_names(timestamp: _dt.datetime) -> dict[str, str]:
    local = timestamp.astimezone()
    return {
        "day": local.strftime("%Y-%m-%d"),
        "month": local.strftime("%Y-%m"),
        "year": local.strftime("%Y"),
        "all_time": "all_time",
    }
