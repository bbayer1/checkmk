#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import contextlib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Callable, Final, Literal

from cmk.utils.metrics import MetricName

from cmk.gui.graphing._type_defs import TranslatedMetric, UnitInfo

from ._color import mix_colors, parse_color, render_color, scalar_colors
from ._type_defs import GraphConsoldiationFunction
from ._unit_info import unit_info


# TODO: real unit computation!
def _unit_mult(u1: UnitInfo, u2: UnitInfo) -> UnitInfo:
    return u2 if u1 in (unit_info[""], unit_info["count"]) else u1


_unit_div: Callable[[UnitInfo, UnitInfo], UnitInfo] = _unit_mult
_unit_add: Callable[[UnitInfo, UnitInfo], UnitInfo] = _unit_mult
_unit_sub: Callable[[UnitInfo, UnitInfo], UnitInfo] = _unit_mult


def _choose_operator_color(a: str, b: str) -> str:
    if a == "#000000":
        return b
    if b == "#000000":
        return a
    return render_color(mix_colors(parse_color(a), parse_color(b)))


@dataclass(frozen=True)
class MetricExpressionResult:
    value: int | float
    unit_info: UnitInfo
    color: str


class MetricDeclaration(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        raise NotImplementedError()

    @abc.abstractmethod
    def metrics(self) -> Iterator[Metric]:
        raise NotImplementedError()

    @abc.abstractmethod
    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        raise NotImplementedError()


@dataclass(frozen=True)
class Constant(MetricDeclaration):
    value: int | float

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            self.value,
            unit_info["count"] if isinstance(self.value, int) else unit_info[""],
            "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from ()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from ()


@dataclass(frozen=True)
class Metric(MetricDeclaration):
    name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None = None

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.name]["value"],
            translated_metrics[self.name]["unit"],
            translated_metrics[self.name]["color"],
        )

    def metrics(self) -> Iterator[Metric]:
        yield self

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from ()


@dataclass(frozen=True)
class WarningOf(MetricDeclaration):
    metric: Metric
    name: Final = "warn"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["warn"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("warn", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class CriticalOf(MetricDeclaration):
    metric: Metric
    name: Final = "crit"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["crit"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("crit", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class MinimumOf(MetricDeclaration):
    metric: Metric
    name: Final = "min"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["min"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("min", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class MaximumOf(MetricDeclaration):
    metric: Metric
    name: Final = "max"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["max"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("max", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class Sum(MetricDeclaration):
    summands: Sequence[MetricDeclaration]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.summands) == 0:
            return MetricExpressionResult(0.0, unit_info[""], "#000000")

        first_result = self.summands[0].evaluate(translated_metrics)
        values = [first_result.value]
        unit_info_ = first_result.unit_info
        color = first_result.color
        for successor in self.summands[1:]:
            successor_result = successor.evaluate(translated_metrics)
            values.append(successor_result.value)
            unit_info_ = _unit_add(unit_info_, successor_result.unit_info)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(sum(values), unit_info_, color)

    def metrics(self) -> Iterator[Metric]:
        yield from (m for s in self.summands for m in s.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (sc for s in self.summands for sc in s.scalars())


@dataclass(frozen=True)
class Product(MetricDeclaration):
    factors: Sequence[MetricDeclaration]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.factors) == 0:
            return MetricExpressionResult(1.0, unit_info[""], "#000000")

        first_result = self.factors[0].evaluate(translated_metrics)
        product = first_result.value
        unit_info_ = first_result.unit_info
        color = first_result.color
        for successor in self.factors[1:]:
            successor_result = successor.evaluate(translated_metrics)
            product *= successor_result.value
            unit_info_ = _unit_mult(unit_info_, successor_result.unit_info)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(product, unit_info_, color)

    def metrics(self) -> Iterator[Metric]:
        yield from (m for f in self.factors for m in f.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for f in self.factors for s in f.scalars())


@dataclass(frozen=True, kw_only=True)
class Difference(MetricDeclaration):
    minuend: MetricDeclaration
    subtrahend: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        minuend_result = self.minuend.evaluate(translated_metrics)
        subtrahend_result = self.subtrahend.evaluate(translated_metrics)

        if (subtrahend_result.value) == 0.0:
            value = 0.0
        else:
            value = minuend_result.value - subtrahend_result.value

        return MetricExpressionResult(
            value,
            _unit_sub(minuend_result.unit_info, subtrahend_result.unit_info),
            _choose_operator_color(minuend_result.color, subtrahend_result.color),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.minuend.metrics()
        yield from self.subtrahend.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.minuend.scalars()
        yield from self.subtrahend.scalars()


@dataclass(frozen=True, kw_only=True)
class Fraction(MetricDeclaration):
    dividend: MetricDeclaration
    divisor: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        dividend_result = self.dividend.evaluate(translated_metrics)
        divisor_result = self.divisor.evaluate(translated_metrics)

        if (divisor_result.value) == 0.0:
            value = 0.0
        else:
            value = dividend_result.value / divisor_result.value

        return MetricExpressionResult(
            value,
            _unit_div(dividend_result.unit_info, divisor_result.unit_info),
            _choose_operator_color(dividend_result.color, divisor_result.color),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.dividend.metrics()
        yield from self.divisor.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.dividend.scalars()
        yield from self.divisor.scalars()


@dataclass(frozen=True)
class Minimum(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        minimum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value < minimum.value:
                minimum = operand_result

        return minimum

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


@dataclass(frozen=True)
class Maximum(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        maximum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value > maximum.value:
                maximum = operand_result

        return maximum

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


# Composed metric declarations:


@dataclass(frozen=True, kw_only=True)
class Percent(MetricDeclaration):
    """percentage = 100 * percent_value / base_value"""

    percent_value: MetricDeclaration
    base_value: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                Fraction(
                    dividend=Product([Constant(100.0), self.percent_value]),
                    divisor=self.base_value,
                )
                .evaluate(translated_metrics)
                .value
            ),
            unit_info["%"],
            self.percent_value.evaluate(translated_metrics).color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.percent_value.metrics()
        yield from self.base_value.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.percent_value.scalars()
        yield from self.base_value.scalars()


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class Average(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        result = Sum(self.operands).evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value / len(self.operands),
            result.unit_info,
            result.color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


@dataclass(frozen=True)
class Merge(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        # TODO None?
        for operand in self.operands:
            if (result := operand.evaluate(translated_metrics)).value is not None:
                return result
        return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


class ConditionalMetricDeclaration(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        raise NotImplementedError()


@dataclass(frozen=True, kw_only=True)
class GreaterThan(ConditionalMetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            > self.right.evaluate(translated_metrics).value
        )


@dataclass(frozen=True, kw_only=True)
class GreaterEqualThan(ConditionalMetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            >= self.right.evaluate(translated_metrics).value
        )


@dataclass(frozen=True, kw_only=True)
class LessThan(ConditionalMetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            < self.right.evaluate(translated_metrics).value
        )


@dataclass(frozen=True, kw_only=True)
class LessEqualThan(ConditionalMetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            <= self.right.evaluate(translated_metrics).value
        )


def _extract_consolidation_func_name(
    expression: str,
) -> tuple[str, GraphConsoldiationFunction | None]:
    if expression.endswith(".max"):
        return expression[:-4], "max"
    if expression.endswith(".min"):
        return expression[:-4], "min"
    if expression.endswith(".average"):
        return expression[:-8], "average"
    return expression, None


def _from_scalar(
    scalar_name: str, metric: Metric
) -> WarningOf | CriticalOf | MinimumOf | MaximumOf:
    match scalar_name:
        case "warn":
            return WarningOf(metric)
        case "crit":
            return CriticalOf(metric)
        case "min":
            return MinimumOf(metric)
        case "max":
            return MaximumOf(metric)
    raise ValueError(scalar_name)


def _parse_single_expression(
    expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
    enforced_consolidation_func_name: GraphConsoldiationFunction | None,
) -> MetricDeclaration:
    if expression not in translated_metrics:
        with contextlib.suppress(ValueError):
            return Constant(int(expression))
        with contextlib.suppress(ValueError):
            return Constant(float(expression))

    var_name, consolidation_func_name = _extract_consolidation_func_name(expression)
    if percent := var_name.endswith("(%)"):
        var_name = var_name[:-3]

    if ":" in var_name:
        var_name, scalar_name = var_name.split(":")
        metric = Metric(var_name, consolidation_func_name or enforced_consolidation_func_name)
        scalar = _from_scalar(scalar_name, metric)
        return Percent(percent_value=scalar, base_value=MaximumOf(metric)) if percent else scalar

    metric = Metric(var_name, consolidation_func_name or enforced_consolidation_func_name)
    return Percent(percent_value=metric, base_value=MaximumOf(metric)) if percent else metric


RPNOperators = Literal["+", "*", "-", "/", "MIN", "MAX", "AVERAGE", "MERGE", ">", ">=", "<", "<="]


def _parse_expression(
    expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
    enforced_consolidation_func_name: GraphConsoldiationFunction | None,
) -> tuple[Sequence[MetricDeclaration | RPNOperators], str, str]:
    # Evaluates an expression, returns a triple of value, unit and color.
    # e.g. "fs_used:max"    -> 12.455, "b", "#00ffc6",
    # e.g. "fs_used(%)"     -> 17.5,   "%", "#00ffc6",
    # e.g. "fs_used:max(%)" -> 100.0,  "%", "#00ffc6",
    # e.g. 123.4            -> 123.4,  "",  "#000000"
    # e.g. "123.4#ff0000"   -> 123.4,  "",  "#ff0000",
    # Note:
    # "fs_growth.max" is the same as fs_growth. The .max is just
    # relevant when fetching RRD data and is used for selecting
    # the consolidation function MAX.

    explicit_color = ""
    if "#" in expression:
        expression, explicit_color = expression.rsplit("#", 1)  # drop appended color information

    explicit_unit_name = ""
    if "@" in expression:
        expression, explicit_unit_name = expression.rsplit("@", 1)  # appended unit name

    stack: list[MetricDeclaration | RPNOperators] = []
    for p in expression.split(","):
        match p:
            case "+":
                stack.append("+")
            case "-":
                stack.append("-")
            case "*":
                stack.append("*")
            case "/":
                stack.append("/")
            case "MIN":
                stack.append("MIN")
            case "MAX":
                stack.append("MAX")
            case "AVERAGE":
                stack.append("AVERAGE")
            case "MERGE":
                stack.append("MERGE")
            case ">":
                stack.append(">")
            case ">=":
                stack.append(">=")
            case "<":
                stack.append("<")
            case "<=":
                stack.append("<=")
            case _:
                stack.append(
                    _parse_single_expression(
                        p,
                        translated_metrics,
                        enforced_consolidation_func_name,
                    )
                )

    return stack, explicit_unit_name, explicit_color


def _resolve_stack(
    stack: Sequence[MetricDeclaration | RPNOperators],
) -> MetricDeclaration | ConditionalMetricDeclaration:
    resolved: list[MetricDeclaration | ConditionalMetricDeclaration] = []
    for element in stack:
        if isinstance(element, MetricDeclaration):
            resolved.append(element)
            continue

        if not isinstance(right := resolved.pop(), MetricDeclaration):
            raise TypeError(right)

        if not isinstance(left := resolved.pop(), MetricDeclaration):
            raise TypeError(left)

        match element:
            case "+":
                resolved.append(Sum([left, right]))
            case "-":
                resolved.append(Difference(minuend=left, subtrahend=right))
            case "*":
                resolved.append(Product([left, right]))
            case "/":
                # Handle zero division by always adding a tiny bit to the divisor
                resolved.append(Fraction(dividend=left, divisor=Sum([right, Constant(1e-16)])))
            case "MIN":
                resolved.append(Minimum([left, right]))
            case "MAX":
                resolved.append(Maximum([left, right]))
            case "AVERAGE":
                resolved.append(Average([left, right]))
            case "MERGE":
                resolved.append(Merge([left, right]))
            case ">=":
                resolved.append(GreaterEqualThan(left=left, right=right))
            case ">":
                resolved.append(GreaterThan(left=left, right=right))
            case "<=":
                resolved.append(LessEqualThan(left=left, right=right))
            case "<":
                resolved.append(LessThan(left=left, right=right))

    return resolved[0]


@dataclass(frozen=True)
class MetricExpression:
    declaration: MetricDeclaration
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        result = self.declaration.evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value,
            unit_info[self.explicit_unit_name] if self.explicit_unit_name else result.unit_info,
            "#" + self.explicit_color if self.explicit_color else result.color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.declaration.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.declaration.scalars()


def parse_expression(
    expression: str | int | float,
    translated_metrics: Mapping[str, TranslatedMetric],
    enforced_consolidation_func_name: GraphConsoldiationFunction | None = None,
) -> MetricExpression:
    if isinstance(expression, (int, float)):
        return MetricExpression(Constant(expression))

    (
        stack,
        explicit_unit_name,
        explicit_color,
    ) = _parse_expression(
        expression,
        translated_metrics,
        enforced_consolidation_func_name,
    )
    if isinstance(resolved := _resolve_stack(stack), MetricDeclaration):
        return MetricExpression(resolved, explicit_unit_name, explicit_color)
    raise TypeError(resolved)


def parse_conditional_expression(
    expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
    enforced_consolidation_func_name: GraphConsoldiationFunction | None = None,
) -> ConditionalMetricDeclaration:
    (
        stack,
        _explicit_unit_name,
        _explicit_color,
    ) = _parse_expression(
        expression,
        translated_metrics,
        enforced_consolidation_func_name,
    )
    if isinstance(resolved := _resolve_stack(stack), ConditionalMetricDeclaration):
        return resolved
    raise TypeError(resolved)


def has_required_metrics_or_scalars(
    expressions: Sequence[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> bool:
    for expression in expressions:
        for metric in expression.metrics():
            if metric.name not in translated_metrics:
                return False
        for scalar in expression.scalars():
            if scalar.metric.name not in translated_metrics:
                return False
            # TODO: scalar has type "WarningOf | CriticalOf | MinimumOf | MaximumOf" and these types
            # meet at MetricDeclaration. But MetricDeclaration has no "name" attribute. This should
            # be done differently either by introduing another class (the common superclass of those
            # types) or by a protocol.
            if scalar.name not in translated_metrics[scalar.metric.name]["scalar"]:  # type: ignore[operator]
                return False
    return True
