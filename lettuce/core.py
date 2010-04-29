# -*- coding: utf-8 -*-
# <Lettuce - Behaviour Driven Development for python>
# Copyright (C) <2010>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import os

from lettuce import strings
from lettuce.registry import STEP_REGISTRY
from lettuce.registry import CALLBACK_REGISTRY
from lettuce.exceptions import ReasonToFail
from lettuce.exceptions import NoDefinitionFound

def parse_data_list(lines):
    keys = []
    data_list = []
    if lines:
        first_line = lines.pop(0)
        keys = strings.split_wisely(first_line, "|", True)

        for line in lines:
            values = strings.split_wisely(line, "|", True)
            data_list.append(dict(zip(keys, values)))

    return keys, data_list

class StepDefinition(object):
    """A step definition is a wrapper for user-defined callbacks. It
    gets a few metadata from file, such as filename and line number"""
    def __init__(self, step, function):
        self.function = function
        self.file = os.path.relpath(function.func_code.co_filename)
        self.line = function.func_code.co_firstlineno + 1
        self.step = step

    def __call__(self, *args, **kw):
        """Method that actually wrapps the call to step definition
        callback. Sends step object as first argument
        """
        try:
            ret = self.function(self.step, *args, **kw)
            self.step.passed = True
        except Exception, e:
            self.step.failed = True
            self.step.why = ReasonToFail(e)
            raise e

        return ret

class StepDescription(object):
    """A simple object that holds filename and line number of a step
    description (step within feature file)"""
    def __init__(self, line, filename):
        self.file = filename
        if self.file:
            self.file = os.path.relpath(self.file)

        self.line = line

class ScenarioDescription(object):
    """A simple object that holds filename and line number of a scenario
    description (scenario within feature file)"""

    def __init__(self, scenario, filename, string):
        self.file = os.path.relpath(filename)
        self.line = None

        for pline, part in enumerate(string.splitlines()):
            part = part.strip()
            if re.match("Scenario( Outline)?[:] " + re.escape(scenario.name), part):
                self.line = pline + 1
                break

class FeatureDescription(object):
    """A simple object that holds filename and line number of a feature
    description"""

    def __init__(self, feature, filename, string):
        lines = [l.strip() for l in string.splitlines()]
        self.file = os.path.relpath(filename)
        self.line = None
        described_at = []
        description_lines = strings.get_stripped_lines(feature.description)
        for pline, part in enumerate(lines):
            part = part.strip()
            line = pline + 1
            if part.startswith("Feature:"):
                self.line = line
            else:
                for description in description_lines:
                    if part == description:
                        described_at.append(line)

        self.description_at = tuple(described_at)

class Step(object):
    """ Object that represents each step on feature files."""
    has_definition = False
    indentation = 4
    table_indentation = indentation + 2
    defined_at = None
    ran = False
    passed = None
    failed = None

    def __init__(self, sentence, remaining_lines, line=None, filename=None):
        self.sentence = sentence
        self._remaining_lines = remaining_lines
        keys, data_list = self._parse_remaining_lines(remaining_lines)

        self.keys = tuple(keys)
        self.data_list = list(data_list)
        self.described_at = StepDescription(line, filename)

    def _calc_list_length(self, lst):
        length = self.table_indentation + 2
        for item in lst:
            length += len(item) + 2

        if len(lst) > 1:
            length += 1

        return length

    def _calc_key_length(self, data):
        return self._calc_list_length(data.keys())

    def _calc_value_length(self, data):
        return self._calc_list_length(data.values())

    @property
    def max_length(self):
        max_length = len(self.sentence) + self.indentation
        for data in self.data_list:
            key_size = self._calc_key_length(data)
            if key_size > max_length:
                max_length = key_size

            value_size = self._calc_value_length(data)
            if value_size > max_length:
                max_length = value_size

        return max_length

    def represent_string(self, string):
        head = ' ' * self.indentation + string
        where = self.described_at
        if self.defined_at:
            where = self.defined_at
        return strings.rfill(head, self.scenario.feature.max_length + 1, append='# %s:%d\n' % (where.file, where.line))

    def represent_data_list(self):
        lines = strings.dicts_to_string(self.data_list, self.keys).splitlines()
        return "\n".join([(" " * self.table_indentation) + line for line in lines]) + "\n"

    def __repr__(self):
        return u'<Step: "%s">' % self.sentence

    def _parse_remaining_lines(self, lines):
        return parse_data_list(lines)

    def _get_match(self, ignore_case):
        matched, func = None, lambda: None

        for regex, func in STEP_REGISTRY.items():
            matched = re.search(regex, self.sentence, ignore_case and re.I or 0)
            if matched:
                break

        return matched, StepDefinition(self, func)

    def pre_run(self, ignore_case):
        matched, step_definition = self._get_match(ignore_case)
        if not self.defined_at:
            if not matched:
                raise NoDefinitionFound(self)

            self.has_definition = True
            self.defined_at = step_definition

        return matched, step_definition

    def run(self, ignore_case):
        """Runs a step, trying to resolve it on available step
        definitions"""
        matched, step_definition = self.pre_run(ignore_case)
        self.ran = True
        kw = matched.groupdict()

        if kw:
            step_definition(**kw)
        else:
            groups = matched.groups()
            step_definition(*groups)

        self.passed = True
        return True

    @classmethod
    def from_string(cls, string, with_file=None, original_string=None):
        """Creates a new step from string"""
        lines = strings.get_stripped_lines(string)
        sentence = lines.pop(0)

        line = None
        if with_file and original_string:
            for pline, line in enumerate(original_string.splitlines()):
                if sentence in line:
                    line = pline + 1
                    break

        return cls(sentence, remaining_lines=lines, line=line, filename=with_file)

class Scenario(object):
    """ Object that represents each scenario on feature files."""
    described_at = None
    indentation = 2
    table_indentation = indentation + 2
    def __init__(self, name, remaining_lines, keys, outlines, with_file=None,
                 original_string=None):

        self.name = name
        self.steps = self._parse_remaining_lines(remaining_lines,
                                                 with_file,
                                                 original_string)
        self.keys = keys
        self.outlines = outlines
        if with_file and original_string:
            scenario_definition = ScenarioDescription(self, with_file,
                                                      original_string)
            self._set_definition(scenario_definition)

        self.solved_steps = list(self._resolve_steps(self.steps, self.outlines,
                                                     with_file, original_string))
        self._add_myself_to_steps()

    @property
    def max_length(self):
        if self.outlines:
            prefix = "Scenario Outline:"
        else:
            prefix = "Scenario:"

        max_length = len("%s %s" % (prefix, self.name)) + self.indentation

        for step in self.steps:
            if step.max_length > max_length:
                max_length = step.max_length

        for outline in self.outlines:
            key_size = self._calc_key_length(outline)
            if key_size > max_length:
                max_length = key_size

            value_size = self._calc_value_length(outline)
            if value_size > max_length:
                max_length = value_size

        return max_length

    def _calc_list_length(self, lst):
        length = self.table_indentation + 2
        for item in lst:
            length += len(item) + 2

        if len(lst) > 1:
            length += 2

        return length

    def _calc_key_length(self, data):
        return self._calc_list_length(data.keys())

    def _calc_value_length(self, data):
        return self._calc_list_length(data.values())

    def __repr__(self):
        return u'<Scenario: "%s">' % self.name

    def run(self, ignore_case):
        """Runs a scenario, running each of its steps. Also call
        before_each and after_each callbacks for steps and scenario"""

        steps_passed = []
        steps_failed = []
        steps_undefined = []

        for callback in CALLBACK_REGISTRY['scenario']['before_each']:
            callback(self)

        for step in self.steps:
            try:
                step.pre_run(ignore_case)
                for callback in CALLBACK_REGISTRY['step']['before_each']:
                    callback(step)

                if not steps_failed and not steps_undefined:
                    step.run(ignore_case)
                    steps_passed.append(step)

            except AssertionError:
                steps_failed.append(step)

            except NoDefinitionFound, e:
                steps_undefined.append(e.step)

            finally:
                for callback in CALLBACK_REGISTRY['step']['after_each']:
                    callback(step)

        for callback in CALLBACK_REGISTRY['scenario']['after_each']:
            callback(self)


        skip = lambda x: x not in steps_passed and x not in steps_undefined and x not in steps_failed

        steps_skipped = filter(skip, self.steps)

        return ScenarioResult(
            self,
            steps_passed,
            steps_failed,
            steps_skipped,
            steps_undefined
        )

    def _add_myself_to_steps(self):
        for step in self.steps:
            step.scenario = self

        for step in self.solved_steps:
            step.scenario = self

    def _resolve_steps(self, steps, outlines, with_file, original_string):
        for outline in outlines:
            for step in steps:
                sentence = step.sentence
                for k, v in outline.items():
                    sentence = sentence.replace(u'<%s>' % k, v)

                yield Step(sentence, step._remaining_lines)

    def _parse_remaining_lines(self, lines, with_file, original_string):
        step_strings = []
        for line in lines:
            if strings.wise_startswith(line, "|"):
                step_strings[-1] += "\n%s" % line
            else:
                step_strings.append(line)

        mkargs = lambda s: [s, with_file, original_string]
        return [Step.from_string(*mkargs(s)) for s in step_strings]

    def _set_definition(self, definition):
        self.described_at = definition

    def represented(self):
        comp = self.outlines and ' Outline' or ''
        head = '%sScenario%s: %s' % (' ' * self.indentation, comp, self.name)
        return strings.rfill(head, self.feature.max_length + 1, append='# %s:%d\n' % (self.described_at.file, self.described_at.line))

    def represent_examples(self):
        lines = strings.dicts_to_string(self.outlines, self.keys).splitlines()
        return "\n".join([(" " * self.table_indentation) + line for line in lines]) + '\n'

    @classmethod
    def from_string(new_scenario, string, with_file=None, original_string=None):
        """ Creates a new scenario from string"""

        splitted = strings.split_wisely(string, "Example[s]?[:]", True)
        string = splitted[0]
        keys = []
        outlines = []
        if len(splitted) is 2:
            part = splitted[1]
            keys, outlines = parse_data_list(strings.get_stripped_lines(part))

        lines = strings.get_stripped_lines(string)
        scenario_line = lines.pop(0)
        line = strings.remove_it(scenario_line, "Scenario( Outline)?[:] ")

        scenario =  new_scenario(name=line,
                                 remaining_lines=lines,
                                 keys=keys,
                                 outlines=outlines,
                                 with_file=with_file,
                                 original_string=original_string)

        return scenario

class Feature(object):
    """ Object that represents a feature."""
    described_at = None
    def __init__(self, name, remaining_lines, with_file, original_string):
        self.name = name
        self.scenarios, self.description = self._parse_remaining_lines(
            remaining_lines,
            original_string,
            with_file
        )

        self.original_string = original_string

        if with_file:
            feature_definition = FeatureDescription(self,
                                                    with_file,
                                                    original_string)
            self._set_definition(feature_definition)

        self._add_myself_to_scenarios()

    @property
    def max_length(self):
        max_length = len("Feature: %s" % self.name)
        for line in self.description.splitlines():
            length = len(line.strip()) + Scenario.indentation
            if length > max_length:
                max_length = length

        for scenario in self.scenarios:
            if scenario.max_length > max_length:
                max_length = scenario.max_length

        return max_length

    def _add_myself_to_scenarios(self):
        for scenario in self.scenarios:
            scenario.feature = self

    def __repr__(self):
        return u'<Feature: "%s">' % self.name

    def get_head(self):
        return "Feature: %s" % self.name

    def represented(self):
        length = self.max_length + 1

        filename = self.described_at.file
        line = self.described_at.line
        head = strings.rfill(self.get_head(), length, append="# %s:%d\n" % (filename, line))
        for description, line in zip(self.description.splitlines(), self.described_at.description_at):
            head += strings.rfill("  %s" % description, length, append="# %s:%d\n" % (filename, line))

        return head

    @classmethod
    def from_string(new_feature, string, with_file=None):
        """Creates a new feature from string"""
        lines = strings.get_stripped_lines(string)
        while lines:
            matched = re.search(r'Feature:(.*)', lines[0], re.I)
            if matched:
                name = matched.groups()[0].strip()
                break

            lines.pop(0)

        feature = new_feature(name=name,
                              remaining_lines=lines,
                              with_file=with_file,
                              original_string=string)
        return feature

    @classmethod
    def from_file(new_feature, filename):
        """Creates a new feature from filename"""
        f = open(filename)
        string = f.read()
        f.close()
        feature = new_feature.from_string(string, with_file=filename)
        return feature

    def _set_definition(self, definition):
        self.described_at = definition

    def _parse_remaining_lines(self, lines, original_string, with_file=None):
        joined = "\n".join(lines[1:])
        regex = re.compile("Scenario( Outline)?[:]\s", re.I)
        joined = regex.sub('Scenario: ', joined)
        parts = strings.split_wisely(joined, "Scenario[:] ")

        description = ""

        if not re.search("^Scenario[:] ", joined):
            description = parts[0]
            parts.pop(0)

        scenario_strings = ["Scenario: %s" % s for s in parts if s.strip()]
        kw = dict(original_string=original_string, with_file=with_file)

        scenarios = [Scenario.from_string(s, **kw) for s in scenario_strings]

        return scenarios, description

    def run(self, ignore_case=True):
        for callback in CALLBACK_REGISTRY['feature']['before_each']:
            callback(self)

        scenarios_ran = [scenario.run(ignore_case) for scenario in self.scenarios]

        for callback in CALLBACK_REGISTRY['feature']['after_each']:
            callback(self)

        return FeatureResult(self, *scenarios_ran)

class FeatureResult(object):
    """Object that holds results of each scenario ran from within a feature"""
    def __init__(self, feature, *scenario_results):
        self.feature = feature
        self.scenario_results = scenario_results

    @property
    def passed(self):
        return all([result.passed for result in self.scenario_results])

class ScenarioResult(object):
    """Object that holds results of each step ran from within a scenario"""
    def __init__(self, scenario, steps_passed, steps_failed, steps_skipped,
                 steps_undefined):

        self.scenario = scenario

        self.steps_passed = steps_passed
        self.steps_failed = steps_failed
        self.steps_skipped = steps_skipped
        self.steps_undefined = steps_undefined

        all_lists = [steps_passed + steps_skipped + steps_undefined + steps_failed]
        self.total_steps = sum(map(len, all_lists))

    @property
    def passed(self):
        return self.total_steps is len(self.steps_passed)

class TotalResult(object):
    def __init__(self, feature_results):
        self.feature_results = feature_results
        self.scenario_results = []
        self.steps_passed = 0
        self.steps_failed = 0
        self.steps_skipped = 0
        self.steps_undefined= 0
        self.proposed_definitions = []
        self.steps = 0
        for feature_result in self.feature_results:
            for scenario_result in feature_result.scenario_results:
                self.scenario_results.append(scenario_result)
                self.steps_passed += len(scenario_result.steps_passed)
                self.steps_failed += len(scenario_result.steps_failed)
                self.steps_skipped += len(scenario_result.steps_skipped)
                self.steps_undefined += len(scenario_result.steps_undefined)
                self.steps += scenario_result.total_steps
                self.proposed_definitions.extend(scenario_result.steps_undefined)

    @property
    def features_ran(self):
        return len(self.feature_results)

    @property
    def features_passed(self):
        return len([result for result in self.feature_results if result.passed])

    @property
    def scenarios_ran(self):
        return len(self.scenario_results)

    @property
    def scenarios_passed(self):
        return len([result for result in self.scenario_results if result.passed])
