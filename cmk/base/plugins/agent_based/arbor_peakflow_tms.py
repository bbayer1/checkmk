#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.lib.arbor import DETECT_PEAKFLOW_TMS, parse_arbor_cpu_load

from .agent_based_api.v1 import register, SNMPTree

register.snmp_section(
    name="arbor_peakflow_tms_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_arbor_cpu_load,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.5.2",
        oids=[
            "3.0",  # deviceCpuLoadAvg1min
            "4.0",  # deviceCpuLoadAvg5min
            "5.0",  # deviceCpuLoadAvg15min
        ],
    ),
    detect=DETECT_PEAKFLOW_TMS,
)
