#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.emc import DETECT_DATADOMAIN


def format_emc_datadomain_temp(descr, encid, index, new_format):
    if new_format:
        return descr + " Enclosure " + encid
    return encid + "-" + index


def inventory_emc_datadomain_temps(info):
    for encid, index, descr, _reading, status in info:
        if status != "2":
            yield format_emc_datadomain_temp(descr, encid, index, True), {}


def check_emc_datadomain_temps(item, params, info):
    state_table = {
        "0": (2, "Failed"),
        "1": (0, "OK"),
        "2": (2, "Not found"),
        "3": (1, "Overheat Warning"),
        "4": (2, "Overheat Critical"),
    }
    for encid, index, descr, reading, status in info:
        name = format_emc_datadomain_temp(descr, encid, index, "Enclosure" in item)
        if item == name:
            dev_status, state_name = state_table[status]
            return check_temperature(
                float(reading),
                params,
                "emc_datadomain_temps_%s" % item,
                dev_status=int(dev_status),
                dev_status_name=state_name,
            )
    return None


check_info["emc_datadomain_temps"] = LegacyCheckDefinition(
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.1.2.1.1.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_emc_datadomain_temps,
    check_function=check_emc_datadomain_temps,
    check_ruleset_name="temperature",
)
