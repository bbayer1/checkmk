// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicRRDColumn_h
#define DynamicRRDColumn_h

#include <memory>
#include <stdexcept>
#include <string>

#include "livestatus/DynamicColumn.h"
#include "livestatus/RRDColumn.h"
#include "livestatus/opids.h"
class Column;
class ColumnOffsets;
class Filter;
class ICore;

template <class T>
class DynamicRRDColumn : public DynamicColumn {
public:
    DynamicRRDColumn(const std::string &name, const std::string &description,
                     ICore *mc, const ColumnOffsets &offsets)
        : DynamicColumn(name, description, offsets), _mc(mc) {}

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        RelationalOperator /*unused*/, const std::string & /*unused*/) const {
        throw std::runtime_error("filtering on dynamic RRD column '" + name() +
                                 "' not supported");
    }

    std::unique_ptr<Column> createColumn(
        const std::string &name, const std::string &arguments) override {
        return std::make_unique<T>(
            name, "dynamic column", _offsets, std::make_unique<RRDRenderer>(),
            RRDDataMaker{_mc, RRDColumnArgs{arguments, _name}});
    }

private:
    ICore *_mc;
};

#endif  // DynamicRRDColumn_h
