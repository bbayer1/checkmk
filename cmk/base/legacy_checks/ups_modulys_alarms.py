#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree

from cmk.plugins.lib.ups_modulys import DETECT_UPS_MODULYS


def inventory_ups_modulys_alarms(info):
    if info:
        return [(None, None)]
    return []


def check_ups_modulys_alarms(_no_item, _no_params, info):
    oiddef = {
        "1": (2, "Disconnect"),
        "2": (2, "Input power failure"),
        "3": (2, "Low batteries"),
        "4": (1, "High load"),
        "5": (2, "Severley high load"),
        "6": (2, "On bypass"),
        "7": (2, "General failure"),
        "8": (2, "Battery ground fault"),
        "9": (0, "UPS test in progress"),
        "10": (2, "UPS test failure"),
        "11": (2, "Fuse failure"),
        "12": (2, "Output overload"),
        "13": (2, "Output overcurrent"),
        "14": (2, "Inverter abnormal"),
        "15": (2, "Rectifier abnormal"),
        "16": (2, "Reserve abnormal"),
        "17": (1, "On reserve"),
        "18": (2, "Overheating"),
        "19": (2, "Output abnormal"),
        "20": (2, "Bypass bad"),
        "21": (0, "In standby mode"),
        "22": (2, "Charger failure"),
        "23": (2, "Fan failure"),
        "24": (0, "In economic mode"),
        "25": (1, "Output turned off"),
        "26": (1, "Smart shutdown in progress"),
        "27": (2, "Emergency power off"),
        "28": (1, "Shutdown"),
        "29": (2, "Output breaker open"),
    }

    result = False
    for oidend, flag in info:
        if flag and flag != "NULL" and int(flag):
            result = True
            yield oiddef[oidend]

    if not result:
        yield 0, "No alarms"


check_info["ups_modulys_alarms"] = LegacyCheckDefinition(
    detect=DETECT_UPS_MODULYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2254.2.4",
        oids=[OIDEnd(), "9"],
    ),
    service_name="UPS Alarms",
    discovery_function=inventory_ups_modulys_alarms,
    check_function=check_ups_modulys_alarms,
)
