#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith

# .1.3.6.1.4.1.5528.100.4.1.1.1.1.636159851 nbAlinkEnc_0_4_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.882181375 nbAlinkEnc_2_1_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1619732064 nbAlinkEnc_0_2_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1665932156 nbAlinkEnc_1_4_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1751899818 nbAlinkEnc_2_2_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1857547767 nbAlinkEnc_1_5_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.2370211927 nbAlinkEnc_1_6_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.2618588815 nbAlinkEnc_2_3_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.2628357572 nbAlinkEnc_0_1_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3031356659 nbAlinkEnc_0_5_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3056253200 nbAlinkEnc_0_6_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3103062985 nbAlinkEnc_2_4_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3328914949 nbAlinkEnc_1_3_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3406802758 nbAlinkEnc_0_3_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.636159851 252
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.882181375 222
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1619732064 222
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1665932156 216
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1751899818 245
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1857547767 234
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.2370211927 240
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.2618588815 220
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.2628357572 229
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3031356659 0
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3056253200 0
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3103062985 215
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3328914949 234
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3406802758 238
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.636159851 25.200000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.882181375 22.200000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1619732064 22.200000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1665932156 21.600000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1751899818 24.500000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1857547767 23.400000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.2370211927 24.000000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.2618588815 22.000000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.2628357572 22.900000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3031356659
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3056253200
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3103062985 21.500000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3328914949 23.400000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3406802758 23.800000

# .1.3.6.1.4.1.5528.100.4.1.2.1.1.421607638 nbAlinkEnc_1_5_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.581338442 nbAlinkEnc_1_3_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.1121716336 nbAlinkEnc_0_6_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.3273299739 nbAlinkEnc_0_3_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.4181308384 nbAlinkEnc_0_5_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.421607638 370
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.581338442 320
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.1121716336 0
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.3273299739 320
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.4181308384 0
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.421607638 37.000000
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.581338442 32.000000
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.1121716336
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.3273299739 32.000000
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.4181308384

# .1.3.6.1.4.1.5528.100.4.1.3.1.1.1000015730 nbAlinkEnc_0_5_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.1490079962 nbAlinkEnc_0_3_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.2228353183 nbAlinkEnc_0_6_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.2428087247 nbAlinkEnc_1_3_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.3329736831 nbAlinkEnc_1_5_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.1000015730 0
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.1490079962 61
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.2228353183 0
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.2428087247 57
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.3329736831 78
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.1000015730
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.1490079962 6.100000
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.2228353183
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.2428087247 5.700000
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.3329736831 7.800000

#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                               main check                             |
#   '----------------------------------------------------------------------'

# Suggested by customer


def parse_apc_netbotz_sensors(string_table):
    parsed = {}
    for item_type, block in zip(("temp", "humidity", "dewpoint"), string_table):
        for item_name, reading_str, label, plugged_in_state in block:
            if not plugged_in_state:
                continue
            parsed.setdefault(item_type, {}).setdefault(
                item_name, {"reading": float(reading_str) / 10, "label": label}
            )
    return parsed


def inventory_apc_netbotz_sensors_temp(parsed, what):
    return [(item, {}) for item in parsed.get(what, [])]


def check_apc_netbotz_sensors_temp(item, params, parsed, what):
    if item in parsed.get(what, []):
        data = parsed[what][item]
        state, infotext, perf = check_temperature(
            data["reading"], params, f"apc_netbotz_sensors_{what}_{item}"
        )
        return state, "[{}] {}".format(data["label"], infotext), perf
    return None


_OIDS = [
    "1",  # NETBOTZV2-MIB::*SensorId
    "2",  # NETBOTZV2-MIB::*SensorValue
    "4",  # NETBOTZV2-MIB::*SensorLabel
    "7",  # NETBOTZV2-MIB::*ValueStr; empty if sensor is not plugged in
]

check_info["apc_netbotz_sensors"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5528.100.20.10"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5528.100.4.1.1.1",
            oids=["1", "2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5528.100.4.1.2.1",
            oids=["1", "2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5528.100.4.1.3.1",
            oids=["1", "2", "4", "7"],
        ),
    ],
    parse_function=parse_apc_netbotz_sensors,
    service_name="Temperature %s",
    discovery_function=lambda parsed: inventory_apc_netbotz_sensors_temp(parsed, "temp"),
    check_function=lambda item, params, parsed: check_apc_netbotz_sensors_temp(
        item, params, parsed, "temp"
    ),
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
        "levels_lower": (25.0, 20.0),
    },
)

# .
#   .--dewpoint------------------------------------------------------------.
#   |                 _                           _       _                |
#   |              __| | _____      ___ __   ___ (_)_ __ | |_              |
#   |             / _` |/ _ \ \ /\ / / '_ \ / _ \| | '_ \| __|             |
#   |            | (_| |  __/\ V  V /| |_) | (_) | | | | | |_              |
#   |             \__,_|\___| \_/\_/ | .__/ \___/|_|_| |_|\__|             |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'

# Suggested by customer

check_info["apc_netbotz_sensors.dewpoint"] = LegacyCheckDefinition(
    service_name="Dew point %s",
    sections=["apc_netbotz_sensors"],
    discovery_function=lambda parsed: inventory_apc_netbotz_sensors_temp(parsed, "dewpoint"),
    check_function=lambda item, params, info: check_apc_netbotz_sensors_temp(
        item, params, info, "dewpoint"
    ),
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (18.0, 25.0),
        "levels_lower": (-4.0, -6.0),
    },
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

# Suggested by customer
apc_netbotz_sensors_humidity_default_levels = (30, 35, 60, 65)


def inventory_apc_netbotz_sensors_humidity(parsed):
    return [
        (item, apc_netbotz_sensors_humidity_default_levels) for item in parsed.get("humidity", [])
    ]


def check_apc_netbotz_sensors_humidity(item, params, parsed):
    if item in parsed.get("humidity", []):
        data = parsed["humidity"][item]
        state, infotext, perf = check_humidity(data["reading"], params)
        return state, "[{}] {}".format(data["label"], infotext), perf
    return None


check_info["apc_netbotz_sensors.humidity"] = LegacyCheckDefinition(
    service_name="Humidity %s",
    sections=["apc_netbotz_sensors"],
    discovery_function=inventory_apc_netbotz_sensors_humidity,
    check_function=check_apc_netbotz_sensors_humidity,
    check_ruleset_name="humidity",
)
