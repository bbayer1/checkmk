#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# 2017 comNET GmbH, Bjoern Mueller

# Default levels from http://www.detectcarbonmonoxide.com/co-health-risks/

from collections.abc import Iterable

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.kentix import DETECT_KENTIX


def parse_kentix_co(string_table: list[list[str]]) -> int | None:
    for value in string_table[0]:
        try:
            return int(value)
        except ValueError:
            pass
    return None


def inventory_kentix_co(section: int) -> Iterable[tuple[None, dict]]:
    yield None, {}


def check_kentix_co(item: str, params: dict, section: int) -> Iterable:
    return check_levels(
        section,
        "parts_per_million",
        params["levels_ppm"],
        unit="ppm",
        human_readable_func=str,
        infoname="CO concentration",
    )


check_info["kentix_co"] = LegacyCheckDefinition(
    detect=DETECT_KENTIX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37954",
        oids=["2.1.4.1", "3.1.3.1"],
    ),
    parse_function=parse_kentix_co,
    service_name="Carbon Monoxide",
    discovery_function=inventory_kentix_co,
    check_function=check_kentix_co,
    check_ruleset_name="carbon_monoxide",
    check_default_parameters={
        "levels_ppm": (10, 25),
    },
)
