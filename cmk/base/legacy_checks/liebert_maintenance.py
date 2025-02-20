#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import time

from cmk.base.check_api import check_levels, get_age_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.liebert import DETECT_LIEBERT, parse_liebert_int_without_unit

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4868 Calculated Next Maintenance Month
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4868 5
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4869 Calculated Next Maintenance Year
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4869 2017


def inventory_liebert_maintenance(parsed):
    return [(None, {})]


def check_liebert_maintenance(_no_item, params, parsed):
    month, year = None, None
    for key, value in parsed.items():
        if "month" in key.lower():
            month = value
        elif "year" in key.lower():
            year = value

    if None in (month, year):
        return

    yield 0, f"Next maintenance: {month}/{year}"

    time_left_seconds = time.mktime((year, month, 0, 0, 0, 0, 0, 0, 0)) - time.time()

    warn_days, crit_days = params["levels"]
    levels = (None, None, warn_days * 86400, crit_days * 86400)
    yield check_levels(time_left_seconds, None, levels, human_readable_func=get_age_human_readable)


check_info["liebert_maintenance"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.4868", "20.1.2.1.4868", "10.1.2.1.4869", "20.1.2.1.4869"],
    ),
    parse_function=parse_liebert_int_without_unit,
    service_name="Maintenance",
    discovery_function=inventory_liebert_maintenance,
    check_function=check_liebert_maintenance,
    check_default_parameters={"levels": (10, 5)},  # Remaining days until next maintenance,
)
