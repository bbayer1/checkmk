#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.ra32e import DETECT_RA32E


def inventory_ra32e_switch(info):
    for index, _ in enumerate(info[0], start=1):
        yield "Sensor %02d" % index, None


def check_ra32e_switch(item, params, info):
    index = int(item.split()[-1].lstrip("0")) - 1  # e.g. 'Sensor 08'
    switch_state = {"0": "open", "1": "closed"}.get(info[0][index])
    if not switch_state:
        return 3, "unknown status"

    state, infotext = 0, switch_state
    if params and params.get("state", "") != "ignore" and switch_state != params.get("state"):
        state = 2
        infotext += " (expected %s)" % params["state"]

    return state, infotext


check_info["ra32e_switch"] = LegacyCheckDefinition(
    detect=DETECT_RA32E,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.8.1.3",
        oids=[
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
        ],
    ),
    service_name="Switch %s",
    discovery_function=inventory_ra32e_switch,
    check_function=check_ra32e_switch,
    check_ruleset_name="switch_contact",
)
