#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import check_levels, get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info

import cmk.plugins.lib.docker as docker


def parse_docker_node_disk_usage(string_table):
    disk_usage = docker.parse_multiline(string_table).data
    return {r.get("type"): r for r in disk_usage if r is not None}


def check_docker_node_disk_usage(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    for key, human_readable_func in (
        ("size", get_bytes_human_readable),
        ("reclaimable", get_bytes_human_readable),
        ("count", lambda x: x),
        ("active", lambda x: x),
    ):
        value = data[key]

        yield check_levels(
            value,
            key,
            params.get(key),
            human_readable_func=human_readable_func,
            infoname=key.title(),
        )


def discover_docker_node_disk_usage(section):
    yield from ((item, {}) for item in section)


check_info["docker_node_disk_usage"] = LegacyCheckDefinition(
    parse_function=parse_docker_node_disk_usage,
    service_name="Docker disk usage - %s",
    discovery_function=discover_docker_node_disk_usage,
    check_function=check_docker_node_disk_usage,
    check_ruleset_name="docker_node_disk_usage",
)
