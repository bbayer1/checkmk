#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.detection import DETECT_NEVER

# targetstate is 1 (up)

ifoperstatus_monitor_unused = False
ifoperstatus_inventory_porttypes = ["6"]


def inventory_ifoperstatus(info):
    inventory = []
    for name, hwtype, operstatus in info:
        if hwtype in ifoperstatus_inventory_porttypes and (
            ifoperstatus_monitor_unused or operstatus == "1"
        ):
            inventory.append((name, operstatus))
    return inventory


def ifoperstatus_statename(st):
    names = {"1": "up", "2": "down"}
    return names.get(st, st)


def check_ifoperstatus(item, targetstate, info):
    for name, _hwtype, operstatus in info:
        if item == name:
            operstatus = ifoperstatus_statename(operstatus)
            if not isinstance(targetstate, list):
                targetstate = ifoperstatus_statename(targetstate)
            if operstatus == targetstate or (
                isinstance(targetstate, list) and operstatus in targetstate
            ):
                return (0, "status is %s" % operstatus)
            if operstatus == "up":
                return (1, "port used, but should not be")
            return (2, "status is %s" % operstatus)

    return (3, "interface %s missing" % item)


# Never inventorize automatically. let if/if64 be the default

check_info["ifoperstatus"] = LegacyCheckDefinition(
    detect=DETECT_NEVER,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=["2", "3", "8"],
    ),
    service_name="Interface %s",
    discovery_function=inventory_ifoperstatus,
    check_function=check_ifoperstatus,
)
