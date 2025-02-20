#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<sansymphony_serverstatus>>>
# Online WritebackGlobal


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_sansymphony_serverstatus(info):
    if info:
        return [(None, None)]
    return []


def check_sansymphony_serverstatus(_no_item, _no_params, info):
    if not info:
        return None
    status, cachestate = info[0]
    if status == "Online" and cachestate == "WritebackGlobal":
        return 0, f"SANsymphony is {status} and its cache is in {cachestate} mode"
    if status == "Online" and cachestate != "WritebackGlobal":
        return 1, f"SANsymphony is {status} but its cache is in {cachestate} mode"
    return 2, "SANsymphony is %s" % status


check_info["sansymphony_serverstatus"] = LegacyCheckDefinition(
    service_name="sansymphony Serverstatus",
    discovery_function=inventory_sansymphony_serverstatus,
    check_function=check_sansymphony_serverstatus,
)
