def _clamp_non_negative(value):
    try:
        return max(float(value or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def percent_or_default(part, total, default):
    total = _clamp_non_negative(total)
    if total <= 0.0:
        return default
    return (_clamp_non_negative(part) / total) * 100.0


def estimate_site_flow(
    produced,
    consumed,
    fed_in,
    battery_charge=0.0,
    battery_discharge=0.0,
):
    produced = _clamp_non_negative(produced)
    consumed = _clamp_non_negative(consumed)
    fed_in = min(_clamp_non_negative(fed_in), produced)
    battery_charge = _clamp_non_negative(battery_charge)
    battery_discharge = _clamp_non_negative(battery_discharge)

    solar_used_on_site = max(produced - fed_in, 0.0)
    battery_to_load_estimate = min(battery_discharge, consumed)
    remaining_load = max(consumed - battery_to_load_estimate, 0.0)
    solar_to_load_estimate = min(remaining_load, solar_used_on_site)
    remaining_solar = max(solar_used_on_site - solar_to_load_estimate, 0.0)
    solar_to_battery_estimate = min(battery_charge, remaining_solar)
    grid_to_load_estimate = max(
        remaining_load - solar_to_load_estimate,
        0.0,
    )
    local_supply_estimate = solar_to_load_estimate + battery_to_load_estimate

    return {
        "produced": produced,
        "consumed": consumed,
        "fed_in": fed_in,
        "battery_charge": battery_charge,
        "battery_discharge": battery_discharge,
        "solar_used_on_site": solar_used_on_site,
        "solar_to_battery_estimate": solar_to_battery_estimate,
        "solar_to_load_estimate": solar_to_load_estimate,
        "battery_to_load_estimate": battery_to_load_estimate,
        "grid_to_load_estimate": grid_to_load_estimate,
        "local_supply_estimate": local_supply_estimate,
    }
