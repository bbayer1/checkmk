#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.sophos import DETECT_SOPHOS


def parse_sophos_disk(string_table):
    try:
        return int(string_table[0][0])
    except (ValueError, IndexError):
        return None


def check_sophos_disk(item, params, parsed):
    return check_levels(
        parsed,
        "disk_utilization",
        params.get("disk_levels", (None, None)),
        unit="%",
        infoname="Disk percentage usage",
        human_readable_func=lambda x: "%d" % x,
    )


check_info["sophos_disk"] = LegacyCheckDefinition(
    detect=DETECT_SOPHOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.3",
        oids=["2"],
    ),
    parse_function=parse_sophos_disk,
    service_name="Disk usage",
    discovery_function=lambda parsed: [(None, {})] if parsed is not None else None,
    check_function=check_sophos_disk,
    check_ruleset_name="sophos_disk",
)
