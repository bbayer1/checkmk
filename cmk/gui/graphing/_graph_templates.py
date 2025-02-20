#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from re import Match
from typing import ClassVar, Literal

from livestatus import SiteId

from cmk.utils import pnp_cleanup, regex
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.i18n import _
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row

from ._expression import (
    Average,
    Constant,
    Difference,
    Fraction,
    Maximum,
    Merge,
    Metric,
    MetricDeclaration,
    MetricExpression,
    Minimum,
    parse_expression,
    Product,
    Sum,
)
from ._graph_specification import (
    GraphMetric,
    GraphRecipe,
    GraphRecipeBase,
    GraphSpecification,
    HorizontalRule,
    MetricOpConstant,
    MetricOpOperator,
    MetricOpRRDSource,
)
from ._type_defs import GraphConsoldiationFunction, TranslatedMetric
from ._utils import (
    get_graph_data_from_livestatus,
    get_graph_range,
    get_graph_templates,
    GraphTemplate,
    MetricDefinition,
    MetricUnitColor,
    ScalarDefinition,
    translated_metrics_from_row,
)


class TemplateGraphSpecification(GraphSpecification, frozen=True):
    # Overwritten in cmk/gui/graphing/cee/__init__.py
    TUNE_GRAPH_TEMPLATE: ClassVar[
        Callable[[GraphTemplate, TemplateGraphSpecification], GraphTemplate | None]
    ] = lambda graph_template, _spec: graph_template

    graph_type: Literal["template"] = "template"
    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None

    @staticmethod
    def name() -> str:
        return "template_graph_specification"

    def recipes(self) -> list[GraphRecipe]:
        row = get_graph_data_from_livestatus(self.site, self.host_name, self.service_description)
        translated_metrics = translated_metrics_from_row(row)
        return [
            recipe
            for index, graph_template in matching_graph_templates(
                graph_id=self.graph_id,
                graph_index=self.graph_index,
                translated_metrics=translated_metrics,
            )
            if (
                recipe := self._build_recipe_from_template(
                    graph_template=graph_template,
                    row=row,
                    translated_metrics=translated_metrics,
                    index=index,
                )
            )
        ]

    def _build_recipe_from_template(
        self,
        *,
        graph_template: GraphTemplate,
        row: Row,
        translated_metrics: Mapping[str, TranslatedMetric],
        index: int,
    ) -> GraphRecipe | None:
        if not (
            graph_template_tuned := TemplateGraphSpecification.TUNE_GRAPH_TEMPLATE(
                graph_template,
                self,
            )
        ):
            return None

        graph_recipe = create_graph_recipe_from_template(
            graph_template_tuned,
            translated_metrics,
            row,
        )

        return GraphRecipe(
            title=graph_recipe.title,
            metrics=graph_recipe.metrics,
            unit=graph_recipe.unit,
            explicit_vertical_range=graph_recipe.explicit_vertical_range,
            horizontal_rules=graph_recipe.horizontal_rules,
            omit_zero_metrics=graph_recipe.omit_zero_metrics,
            consolidation_function=graph_recipe.consolidation_function,
            specification=TemplateGraphSpecification(
                site=self.site,
                host_name=self.host_name,
                service_description=self.service_description,
                destination=self.destination,
                # Performance graph dashlets already use graph_id, but for example in reports, we still
                # use graph_index. We should switch to graph_id everywhere (CMK-7308). Once this is
                # done, we can remove the line below.
                graph_index=index,
                graph_id=graph_template_tuned.id,
            ),
        )


# Performance graph dashlets already use graph_id, but for example in reports, we still use
# graph_index. Therefore, this function needs to support both. We should switch to graph_id
# everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot easily
# build a corresponding transform, so even after switching to graph_id everywhere, we will need to
# keep this functionality here for some time to support already created dashlets, reports etc.
def matching_graph_templates(
    *,
    graph_id: str | None,
    graph_index: int | None,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterable[tuple[int, GraphTemplate]]:
    # Single metrics
    if (
        isinstance(graph_id, str)
        and graph_id.startswith("METRIC_")
        and graph_id[7:] in translated_metrics
    ):
        yield (0, GraphTemplate.from_name(graph_id))
        return

    yield from (
        (index, graph_template)
        for index, graph_template in enumerate(get_graph_templates(translated_metrics))
        if (graph_index is None or index == graph_index)
        and (graph_id is None or graph_template.id == graph_id)
    )


def _replace_expressions(text: str, translated_metrics: Mapping[str, TranslatedMetric]) -> str:
    """Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"""

    def eval_to_string(match: Match[str]) -> str:
        try:
            result = parse_expression(match.group()[2:-1], translated_metrics).evaluate(
                translated_metrics
            )
        except ValueError:
            return _("n/a")
        return result.unit_info["render"](result.value)

    return regex.regex(r"%\([^)]*\)").sub(eval_to_string, text)


def _horizontal_rules_from_thresholds(
    thresholds: Iterable[ScalarDefinition],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> list[HorizontalRule]:
    horizontal_rules = []
    for entry in thresholds:
        try:
            if (result := entry.expression.evaluate(translated_metrics)).value:
                horizontal_rules.append(
                    (
                        result.value,
                        result.unit_info["render"](result.value),
                        result.color,
                        entry.title,
                    )
                )
        # Scalar value like min and max are always optional. This makes configuration
        # of graphs easier.
        except Exception:
            pass

    return horizontal_rules


def create_graph_recipe_from_template(
    graph_template: GraphTemplate, translated_metrics: Mapping[str, TranslatedMetric], row: Row
) -> GraphRecipeBase:
    def _graph_metric(metric_definition: MetricDefinition) -> GraphMetric:
        unit_color = metric_unit_color(metric_definition.expression, translated_metrics)
        return GraphMetric(
            title=metric_line_title(
                metric_definition,
                metric_definition.expression,
                translated_metrics,
            ),
            line_type=metric_definition.line_type,
            operation=metric_expression_to_graph_recipe_expression(
                metric_definition.expression,
                translated_metrics,
                row,
                graph_template.consolidation_function or "max",
            ),
            unit=unit_color["unit"] if unit_color else "",
            color=unit_color["color"] if unit_color else "#000000",
            visible=True,
        )

    metrics = list(map(_graph_metric, graph_template.metrics))
    units = {m.unit for m in metrics}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of different units '%s'") % ", ".join(units)
        )

    title = _replace_expressions(graph_template.title or "", translated_metrics)
    if not title:
        title = next((m.title for m in metrics), "")

    painter_options = PainterOptions.get_instance()
    if painter_options.get("show_internal_graph_and_metric_ids"):
        title = title + f" (Graph ID: {graph_template.id})"

    return GraphRecipeBase(
        title=title,
        metrics=metrics,
        unit=units.pop(),
        explicit_vertical_range=get_graph_range(graph_template, translated_metrics),
        horizontal_rules=_horizontal_rules_from_thresholds(
            graph_template.scalars, translated_metrics
        ),  # e.g. lines for WARN and CRIT
        omit_zero_metrics=graph_template.omit_zero_metrics,
        consolidation_function=graph_template.consolidation_function or "max",
    )


def _to_metric_operation(
    declaration: MetricDeclaration,
    translated_metrics: Mapping[str, TranslatedMetric],
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    if isinstance(declaration, Constant):
        return MetricOpConstant(value=float(declaration.value))
    if isinstance(declaration, Metric):
        sources = [
            MetricOpRRDSource(
                site_id=lq_row["site"],
                host_name=lq_row["host_name"],
                service_name=lq_row.get("service_description", "_HOST_"),
                metric_name=pnp_cleanup(orig_name),
                consolidation_func_name=(
                    declaration.consolidation_func_name or enforced_consolidation_function
                ),
                scale=scale,
            )
            for orig_name, scale in zip(
                translated_metrics[declaration.name]["orig_name"],
                translated_metrics[declaration.name]["scale"],
            )
        ]
        if len(sources) > 1:
            return MetricOpOperator(
                operator_name="MERGE",
                operands=sources,
            )
        return sources[0]
    if isinstance(declaration, Sum):
        return MetricOpOperator(
            operator_name="+",
            operands=[
                _to_metric_operation(
                    s,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for s in declaration.summands
            ],
        )
    if isinstance(declaration, Product):
        return MetricOpOperator(
            operator_name="*",
            operands=[
                _to_metric_operation(
                    f,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for f in declaration.factors
            ],
        )
    if isinstance(declaration, Difference):
        return MetricOpOperator(
            operator_name="-",
            operands=[
                _to_metric_operation(
                    declaration.minuend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
                _to_metric_operation(
                    declaration.subtrahend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
            ],
        )
    if isinstance(declaration, Fraction):
        return MetricOpOperator(
            operator_name="/",
            operands=[
                _to_metric_operation(
                    declaration.dividend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
                _to_metric_operation(
                    declaration.divisor,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
            ],
        )
    if isinstance(declaration, Maximum):
        return MetricOpOperator(
            operator_name="MAX",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    if isinstance(declaration, Minimum):
        return MetricOpOperator(
            operator_name="MIN",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    if isinstance(declaration, Average):
        return MetricOpOperator(
            operator_name="AVERAGE",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    if isinstance(declaration, Merge):
        return MetricOpOperator(
            operator_name="MERGE",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    raise TypeError(declaration)


def metric_expression_to_graph_recipe_expression(
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    return _to_metric_operation(
        metric_expression.declaration,
        translated_metrics,
        lq_row,
        enforced_consolidation_function,
    )


def metric_line_title(
    metric_definition: MetricDefinition,
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> str:
    if metric_definition.title:
        return metric_definition.title
    return translated_metrics[next(metric_expression.metrics()).name]["title"]


def metric_unit_color(
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    optional_metrics: Sequence[str] | None = None,
) -> MetricUnitColor | None:
    try:
        result = metric_expression.evaluate(translated_metrics)
    except KeyError as err:  # because metric_name is not in translated_metrics
        metric_name = err.args[0]
        if optional_metrics and metric_name in optional_metrics:
            return None
        raise MKGeneralException(
            _("Graph recipe '%s' uses undefined metric '%s', available are: %s")
            % (
                metric_expression,
                metric_name,
                ", ".join(sorted(translated_metrics.keys())) or "None",
            )
        )
    return MetricUnitColor(unit=result.unit_info["id"], color=result.color)
