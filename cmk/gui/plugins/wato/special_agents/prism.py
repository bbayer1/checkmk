#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, NetworkPort, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupDatasourceProgramsOS
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_special_agents_prism():
    return Dictionary(
        title=_("Nutanix Prism"),
        elements=[
            (
                "port",
                NetworkPort(
                    title=_("TCP port for connection"),
                    default_value=9440,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "username",
                TextInput(
                    title=_("User ID for web login"),
                ),
            ),
            (
                "password",
                MigrateToIndividualOrStoredPassword(title=_("Password for this user"), size=35),
            ),
        ],
        optional_keys=["port"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name=RuleGroup.SpecialAgents("prism"),
        valuespec=_valuespec_special_agents_prism,
    )
)
