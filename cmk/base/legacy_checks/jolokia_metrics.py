#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import time

from cmk.base.check_api import check_levels, LegacyCheckDefinition, saveint
from cmk.base.check_legacy_includes.jolokia import (
    get_inventory_jolokia_metrics_apps,
    jolokia_metrics_parse,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResultsError,
)

# Example output from agent:
# <<<jolokia_metrics>>>
# 8080 NonHeapMemoryUsage 101078952
# 8080 NonHeapMemoryMax 184549376
# 8080 HeapMemoryUsage 2362781664
# 8080 HeapMemoryMax 9544663040
# 8080 ThreadCount 78
# 8080 DeamonThreadCount 72
# 8080 PeakThreadCount 191
# 8080 TotalStartedThreadCount 941
# 8080 Uptime 572011375
# 8080,java.lang:name=PS_MarkSweep,type=GarbageCollector CollectionCount 0

# Number of sessions low crit, low warn, high warn, high crit
jolokia_metrics_app_sess_default_levels = (-1, -1, 800, 1000)


# .
#   .--Arcane helpers------------------------------------------------------.
#   |                     _                                                |
#   |                    / \   _ __ ___ __ _ _ __   ___                    |
#   |                   / _ \ | '__/ __/ _` | '_ \ / _ \                   |
#   |                  / ___ \| | | (_| (_| | | | |  __/                   |
#   |                 /_/   \_\_|  \___\__,_|_| |_|\___|                   |
#   |                                                                      |
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | TODO: See if these can be removed altogether                         |
#   '----------------------------------------------------------------------'


# This bisects the app server and its values
def jolokia_metrics_app(info, split_item):
    inst, app = split_item
    parsed = jolokia_metrics_parse(info)
    if parsed.get(inst, "") is None:
        raise IgnoreResultsError("No information from Jolokia agent")
    if inst not in parsed or app not in parsed[inst].get("apps", {}):
        return None
    return parsed[inst]["apps"][app]


# This bisects info from BEA and passes on to jolokia_metrics_app
def jolokia_metrics_serv(info, split_item):
    inst, app, serv = split_item
    app = jolokia_metrics_app(info, (inst, app))
    if not app or serv not in app.get("servlets", {}):
        return None
    return app["servlets"][serv]


# .
#   .--Number of Requests--------------------------------------------------.
#   |               ____                            _                      |
#   |              |  _ \ ___  __ _ _   _  ___  ___| |_ ___                |
#   |              | |_) / _ \/ _` | | | |/ _ \/ __| __/ __|               |
#   |              |  _ <  __/ (_| | |_| |  __/\__ \ |_\__ \               |
#   |              |_| \_\___|\__, |\__,_|\___||___/\__|___/               |
#   |                            |_|                                       |
#   '----------------------------------------------------------------------'


def inventory_jolokia_metrics_serv(info):
    parsed = jolokia_metrics_parse(info)
    needed_key = "Requests"
    for inst, vals in parsed.items():
        if vals is None:
            continue  # no data from agent
        for app, val in vals.get("apps", {}).items():
            for serv, servinfo in val.get("servlets", {}).items():
                if needed_key in servinfo:
                    yield f"{inst} {app} {serv}", {}


def check_jolokia_metrics_serv_req(item, params, info):
    serv = jolokia_metrics_serv(info, item.split())
    if not serv or "Requests" not in serv:
        return

    req = saveint(serv["Requests"])

    yield check_levels(
        req,
        "Requests",
        (params["levels_upper"] or (None, None)) + (params["levels_lower"] or (None, None)),
        human_readable_func=str,
        infoname="Requests",
    )

    try:
        request_rate = get_rate(get_value_store(), "rate", time.time(), req, raise_overflow=True)
    except GetRateError:
        return

    yield check_levels(
        request_rate,
        "RequestRate",
        None,
        human_readable_func=lambda x: f"{x:.2f}",
        infoname="Request rate",
    )


check_info["jolokia_metrics.serv_req"] = LegacyCheckDefinition(
    service_name="JVM %s Requests",
    sections=["jolokia_metrics"],
    discovery_function=inventory_jolokia_metrics_serv,
    check_function=check_jolokia_metrics_serv_req,
    check_ruleset_name="jvm_requests",
    check_default_parameters={
        "levels_lower": (-1, -1),
        "levels_upper": (5000, 6000),
    },
)

# .
#   .--App state-----------------------------------------------------------.
#   |                _                      _        _                     |
#   |               / \   _ __  _ __    ___| |_ __ _| |_ ___               |
#   |              / _ \ | '_ \| '_ \  / __| __/ _` | __/ _ \              |
#   |             / ___ \| |_) | |_) | \__ \ || (_| | ||  __/              |
#   |            /_/   \_\ .__/| .__/  |___/\__\__,_|\__\___|              |
#   |                    |_|   |_|                                         |
#   '----------------------------------------------------------------------'


def check_jolokia_metrics_app_state(item, _no_params, info):
    app_state = 3
    app = jolokia_metrics_app(info, item.split())

    # FIXME: this could be nicer.
    if app and "Running" in app:
        if app["Running"] == "1":
            app_state = 0
        else:
            app_state = 2
    # wenn in app statename steht
    elif app and "stateName" in app:
        if app["stateName"] == "STARTED":
            app_state = 0
        else:
            app_state = 2
    if app_state == 3:
        return 3, "data not found in agent output"
    if app_state == 0:
        return 0, "application is running"
    if app_state == 2:
        return 2, "application is not running (Running: %s)"

    return 3, "error in agent output"


check_info["jolokia_metrics.app_state"] = LegacyCheckDefinition(
    service_name="JVM %s State",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "app_state", needed_keys={"Running", "stateName"}
    ),
    check_function=check_jolokia_metrics_app_state,
)

# .
#   .--Unsorted------------------------------------------------------------.
#   |              _   _                      _           _                |
#   |             | | | |_ __  ___  ___  _ __| |_ ___  __| |               |
#   |             | | | | '_ \/ __|/ _ \| '__| __/ _ \/ _` |               |
#   |             | |_| | | | \__ \ (_) | |  | ||  __/ (_| |               |
#   |              \___/|_| |_|___/\___/|_|   \__\___|\__,_|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_jolokia_metrics_app_sess(item, params, info):
    if len(item.split()) == 3:
        app = jolokia_metrics_serv(info, item.split())
    elif len(item.split()) == 2:
        app = jolokia_metrics_app(info, item.split())
    if not app:
        return

    sessions = app.get("Sessions", app.get("activeSessions", app.get("OpenSessionsCurrentCount")))
    if sessions is None:
        return

    sess = saveint(sessions)
    maxActive = saveint(
        app.get("Sessions", app.get("maxActiveSessions", app.get("OpenSessionsCurrentCount")))
    )

    yield check_levels(
        sess,
        "sessions",
        (params["levels_upper"] or (None, None)) + (params["levels_lower"] or (None, None)),
        human_readable_func=str,
        infoname="Sessions",
    )

    if maxActive and maxActive > 0:
        yield 0, f"Maximum active sessions: {maxActive}"


def check_jolokia_metrics_bea_queue(item, params, info):
    app = jolokia_metrics_app(info, item.split())
    if not app:
        yield 3, "application not found"
        return

    if (length := app.get("QueueLength")) is None:
        return

    yield check_levels(
        int(length),
        "length",
        params["levels"],
        human_readable_func=str,
        infoname="Queue length",
    )


# FIXME: This check could work with any JVM
# It has no levels
# A candidate for 1.2.1 overhaul
def check_jolokia_metrics_bea_requests(item, _no_params, info):
    app = jolokia_metrics_app(info, item.split())
    if not app:
        return

    for nk in ["CompletedRequestCount", "requestCount"]:
        if nk in app:
            requests = int(app[nk])
            rate = get_rate(
                get_value_store(),
                "j4p.bea.requests.%s" % item,
                time.time(),
                requests,
                raise_overflow=True,
            )
            yield 0, "%.2f requests/sec" % rate, [("rate", rate)]
            return


def check_jolokia_metrics_bea_threads(item, _no_params, info):
    app = jolokia_metrics_app(info, item.split())
    if not app:
        return (3, "data not found in agent output")

    perfdata = []
    infos = []
    for varname, title in [
        ("ExecuteThreadTotalCount", "total"),
        ("ExecuteThreadIdleCount", "idle"),
        ("StandbyThreadCount", "standby"),
        ("HoggingThreadCount", "hogging"),
    ]:
        value = int(app[varname])
        perfdata.append((varname, value))
        infos.append("%s: %d" % (title, value))

    return (0, ", ".join(infos), perfdata)


check_info["jolokia_metrics.app_sess"] = LegacyCheckDefinition(
    service_name="JVM %s Sessions",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "app_sess",
        needed_keys={"Sessions", "activeSessions"},
        default_params=jolokia_metrics_app_sess_default_levels,
    ),
    check_function=check_jolokia_metrics_app_sess,
    check_ruleset_name="jvm_sessions",
    check_default_parameters={
        "levels_lower": None,
        "levels_upper": None,
    },
)

check_info["jolokia_metrics.requests"] = LegacyCheckDefinition(
    service_name="JVM %s Requests",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps("requests", needed_keys={"requestCount"}),
    check_function=check_jolokia_metrics_bea_requests,
)

# Stuff found on BEA Weblogic
check_info["jolokia_metrics.bea_queue"] = LegacyCheckDefinition(
    service_name="JVM %s Queue",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "queue", needed_keys={"QueueLength"}, default_params={}
    ),
    check_function=check_jolokia_metrics_bea_queue,
    check_ruleset_name="jvm_queue",
    check_default_parameters={
        "levels": (20, 50),
    },
)

check_info["jolokia_metrics.bea_requests"] = LegacyCheckDefinition(
    service_name="JVM %s Requests",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "bea_requests", needed_keys={"CompletedRequestCount"}
    ),
    check_function=check_jolokia_metrics_bea_requests,
)

check_info["jolokia_metrics.bea_threads"] = LegacyCheckDefinition(
    service_name="JVM %s Threads",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "threads", needed_keys={"StandbyThreadCount"}
    ),
    check_function=check_jolokia_metrics_bea_threads,
)

check_info["jolokia_metrics.bea_sess"] = LegacyCheckDefinition(
    service_name="JVM %s Sessions",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "bea_app_sess",
        needed_keys={"OpenSessionsCurrentCount"},
        default_params=jolokia_metrics_app_sess_default_levels,
    ),
    check_function=check_jolokia_metrics_app_sess,
    check_ruleset_name="jvm_sessions",
    check_default_parameters={
        "levels_lower": None,
        "levels_upper": None,
    },
)


def inventory_jolokia_metrics_cache(metrics, info):
    parsed = jolokia_metrics_parse(info)
    metrics_set = set(metrics)
    for inst, vals in [x for x in parsed.items() if x[1] is not None]:
        for cache, cache_vars in vals.get("CacheStatistics", {}).items():
            if metrics_set.intersection(cache_vars) == metrics_set:
                yield f"{inst} {cache}", {}


def check_jolokia_metrics_cache(metrics, totals, item, info):
    type_map = {
        "CacheHitPercentage": (float, 100.0, "%.1f%%"),
        "InMemoryHitPercentage": (float, 100.0, "%.1f%%"),
        "OnDiskHitPercentage": (float, 100.0, "%.1f%%"),
        "OffHeapHitPercentage": (float, 100.0, "%.1f%%"),
    }

    parsed = jolokia_metrics_parse(info)
    try:
        inst, cache = item.split(" ")

        # we display the "metrics" first, totals after, but to "fix" metrics based on zero-totals
        # we need to go over the totals once
        for total in totals:
            val: float | int = int(parsed[inst]["CacheStatistics"][cache][total])
            if val != 0:
                break

        for metric in metrics:
            type_, scale, format_str = type_map.get(metric, (int, 1, "%d"))

            val = type_(parsed[inst]["CacheStatistics"][cache][metric]) * scale
            if isinstance(val, float) and val == 0.0:
                # what a hack! we assume the float is based on the totals (all of them) and if they
                # were all 0, so this float is 0/0, we want to display it as 1 as to not cause
                # an alert
                val = 1.0 * scale
            yield 0, ("%s: " + format_str) % (metric, val), [(metric, val)]

        for total in totals:
            type_, scale, format_str = type_map.get(total, (int, 1, "%d"))
            val = type_(parsed[inst]["CacheStatistics"][cache][total]) * scale
            yield 0, ("%s: " + format_str) % (total, val), []
    except KeyError:
        # some element of the item was missing
        pass


check_info["jolokia_metrics.cache_hits"] = LegacyCheckDefinition(
    service_name="JVM %s Cache Usage",
    sections=["jolokia_metrics"],
    discovery_function=lambda info: inventory_jolokia_metrics_cache(
        ["CacheHitPercentage", "ObjectCount", "CacheHits", "CacheMisses"], info
    ),
    check_function=lambda item, _no_params, parsed: check_jolokia_metrics_cache(
        ["CacheHitPercentage", "ObjectCount"], ["CacheHits", "CacheMisses"], item, parsed
    ),
)

check_info["jolokia_metrics.in_memory"] = LegacyCheckDefinition(
    service_name="JVM %s In Memory",
    sections=["jolokia_metrics"],
    discovery_function=lambda info: inventory_jolokia_metrics_cache(
        ["InMemoryHitPercentage", "MemoryStoreObjectCount", "InMemoryHits", "InMemoryMisses"],
        info,
    ),
    check_function=lambda item, _no_params, parsed: check_jolokia_metrics_cache(
        ["InMemoryHitPercentage", "MemoryStoreObjectCount"],
        ["InMemoryHits", "InMemoryMisses"],
        item,
        parsed,
    ),
)

check_info["jolokia_metrics.on_disk"] = LegacyCheckDefinition(
    service_name="JVM %s On Disk",
    sections=["jolokia_metrics"],
    discovery_function=lambda info: inventory_jolokia_metrics_cache(
        ["OnDiskHitPercentage", "DiskStoreObjectCount", "OnDiskHits", "OnDiskMisses"],
        info,
    ),
    check_function=lambda item, _no_params, parsed: check_jolokia_metrics_cache(
        ["OnDiskHitPercentage", "DiskStoreObjectCount"],
        ["OnDiskHits", "OnDiskMisses"],
        item,
        parsed,
    ),
)

check_info["jolokia_metrics.off_heap"] = LegacyCheckDefinition(
    service_name="JVM %s Off Heap",
    sections=["jolokia_metrics"],
    discovery_function=lambda info: inventory_jolokia_metrics_cache(
        ["OffHeapHitPercentage", "OffHeapStoreObjectCount", "OffHeapHits", "OffHeapMisses"],
        info,
    ),
    check_function=lambda item, _no_params, parsed: check_jolokia_metrics_cache(
        ["OffHeapHitPercentage", "OffHeapStoreObjectCount"],
        ["OffHeapHits", "OffHeapMisses"],
        item,
        parsed,
    ),
)

check_info["jolokia_metrics.writer"] = LegacyCheckDefinition(
    service_name="JVM %s Cache Writer",
    sections=["jolokia_metrics"],
    discovery_function=lambda info: inventory_jolokia_metrics_cache(
        ["WriterQueueLength", "WriterMaxQueueSize"], info
    ),
    check_function=lambda item, _no_params, parsed: check_jolokia_metrics_cache(
        ["WriterQueueLength", "WriterMaxQueueSize"], [], item, parsed
    ),
)
