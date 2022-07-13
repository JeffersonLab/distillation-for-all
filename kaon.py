#!/usr/bin/env python
"""
KAON: KhAOs Nemesis

Simple support tool for using the filesystem as a database. You shouldn't do that, but do it right
if you have to do it.

Kaon keeps a dictionary of artifacts. The user provides the `schema` that describe ways to
introduce, modify, remove dictionary entries.
"""

import json
import sys
import os.path
import re
import itertools
import argparse
import subprocess

#
# Check schema types
#


def show_error(check_value, msg, path):
    """
    If `check_value` is False, then the message error `msg` is raised up.
    """

    if not check_value:
        raise ValueError("Error in path `{}`: {}".format(path, msg))


def check_string(x, path):
    """
    Check that the input is a string.
    """

    show_error(isinstance(x, str),
               "unexpected type, it should be a string", path)


def check_list(x, path):
    """
    Check that the input is a list.
    """

    show_error(isinstance(x, list),
               "unexpected type, it should be a list", path)


def check_dict(x, path):
    """
    Check that the input is a dictionary.
    """

    show_error(isinstance(x, dict),
               "unexpected type, it should be an object (dictionary)", path)


def check_flat_dict(x, path):
    """
    Check that the input is a dictionary with keys and values as strings.
    """

    check_dict(x, path)
    for k, v in x.items():
        show_error(isinstance(k, str) and isinstance(v, str),
                   "unexpected type, the key and the value should be strings", path + "/" + k)


def check_list_flat_dicts(x, path):
    """
    Check that the input a list of flat dictionaries
    """

    check_list(x, path)
    for i, v in enumerate(x):
        check_flat_dict(v, "{}/[{}]".format(path, i))


def check_flat_list(x, path):
    """
    Check that the input is a list of strings.
    """

    check_list(x, path)
    for i, v in enumerate(x):
        check_string(v, "{}/[{}]".format(path, i))


def check_depends_value_dict(x, path):
    """
    Check that the input is a dictionary with possible entries `matching-re`, `interpolate`,
    and `copy-as`.
    """

    check_dict(x, path)
    for k, v in x.items():
        show_error(k in ("matching-re", "copy-as", "interpolate"),
                   "unexpected key, it can be `matching-re`, `interpolate`, or `copy-as`", path + "/" + k)
        check_string(v, path + "/" + k)
    show_error('interpolate' not in x or 'copy-as' not in x,
               "unexpected key, `interpolate` and `copy-as` cannot be together", x)


def check_depends(x, path):
    """
    Check that the input is a dictionary where the keys are strings and the values can be a list
    of strings or a dictionary satisfying depends value dictionary restriction.
    """

    check_dict(x, path)
    for k, v in x.items():
        check_string(k, path)
        if isinstance(v, list):
            check_flat_list(v, path + "/" + k)
        elif isinstance(v, dict):
            check_depends_value_dict(v, path + "/" + k)
        else:
            show_error(False, "unexpected value, it should be a list of an object", path + "/" + k)


def check_executor(x, path):
    """
    Check that the input is a dictionary where the keys are `command`, with a string value and
    `return-attributes` with a plain list.
    """

    check_dict(x, path)
    for k, v in x.items():
        show_error(k in ("command", "return-attributes"),
                   "unexpected key, it can be `command` or `return-attributes`", path + "/" + k)
        check_string(k, path)
        if k == "command":
            check_string(v, path + "/" + k)
        elif k == "return-attributes":
            check_flat_list(v, path + "/" + k)
    show_error("command" in x and "return-attributes" in x,
               "missing keys, expected `command` and `return-attribute` as keys", path)


def check_scheme_item(x, path):
    """
    Check that the input is a dictionary with keys `id`, `depends`, `executor` (optional), `values`
    (optional), `defaults` (optional), and `update` (optional).
    """

    check_dict(x, path)
    for k, v in x.items():
        if k == "name":
            check_string(v, path + "/name")
        elif k == "description":
            check_string(v, path + "/description")
        elif k == "id":
            check_string(v, path + "/id")
        elif k == "depends":
            check_depends(v, path + "/depends")
        elif k == "executor":
            check_executor(v, path + "/executor")
        elif k == "values":
            check_list_flat_dicts(v, path + "/values")
        elif k == "defaults":
            check_flat_dict(v, path + "/defaults")
        elif k == "update":
            check_flat_dict(v, path + "/update")
        else:
            show_error(False, "unexpected key", path + "/" + k)
    show_error("values" not in x or ("depends" not in x and "executor" not in x),
               "unexpected keys, if `values` is present, `depends` or `executor` isn't allowed", path)


def check_schema(x):
    """
    Check that the input is a list of dictionaries satisfying the scheme.
    """

    check_list(x, "/")
    for i, v in enumerate(x):
        check_scheme_item(v, "[{}]".format(i))

#
# Execute schemas
#


def execute_schema(schema, view):
    """
    Execute each of the actions in the schema in the same order as given.
    """

    artifacts = {}
    for i, action in enumerate(schema):
        action_name = action.get('name', "[{}]".format(i))
        # Process action
        if "values" in action:
            new_artifacts = [dict(**d) for d in action['values']]
            # Set default values for missing attributes
            apply_defaults(new_artifacts, action.get('defaults', {}))
            new_artifacts = [
                artifact for artifact in new_artifacts if is_artifact_in_view(artifact, view)]
        else:
            filtered_artifacts = apply_depends_to_artifacts(
                artifacts.values(), view, action.get('depends', {}))
            # Set default values for missing attributes
            apply_defaults(filtered_artifacts, action.get('defaults', {}))
            try:
                new_artifacts = apply_executor_to_artifacts(
                    filtered_artifacts, action['executor']) if 'executor' in action else filtered_artifacts
            except Exception as e:
                raise Exception(
                    "Error in executing executor in action with name `{}`.".format(action_name)) from e
        for artifact in new_artifacts:
            # Enforce some values
            artifact.update(action.get('update', {}))
            # Compute the identification
            try:
                the_id = action['id'].format(**artifact)
            except KeyError as e:
                raise Exception(
                    "Error interpolating the id in action with name `{}` for entry {}.".format(action_name, artifact)) from e
            if the_id in artifacts:
                artifacts[the_id].update(artifact)
            else:
                artifacts[the_id] = artifact

    return list(artifacts.values())


def apply_defaults(artifacts, defaults):
    """
    Set missing attributes.
    """

    for artifact in artifacts:
        for k, v in defaults.items():
            artifact.setdefault(k, v)


def is_artifact_in_view(artifact, view):
    """
    Return whether the artifact satisfies the constrains in the view.
    """

    for k, v in view.items():
        if k in artifact and artifact[k] not in v:
            return False
    return True


def apply_depends(artifact, depends):
    """
    Return an artifact after applying the constrain and actions in depends or None if the artifact
    does not satisfies the constrains.
    """

    new_artifact = dict(**artifact)
    for k, v in depends.items():
        if k not in artifact and (isinstance(v, list) or 'interpolate' not in v):
            return None
        if isinstance(v, list) and artifact[k] not in v:
            return None
        else:
            if "matching-re" in v:
                try:
                    m = re.fullmatch(v['matching-re'].format(**artifact), artifact[k])
                except KeyError:
                    return None
                if not m:
                    return None
                new_artifact.update(m.groupdict())
            if "copy-as" in v:
                new_artifact[v['copy-as']] = artifact[k]
    return new_artifact


def apply_depends_to_artifacts(artifacts, view, depends):
    """
    Filter artifacts that pass the constrains in the view and depends.
    """

    filtered_artifacts = []
    for artifact in artifacts:
        # Ignore artifacts that don't pass the view
        if not is_artifact_in_view(artifact, view):
            continue
        # Apply depends
        new_artifact = apply_depends(artifact, depends)
        # Append new artifact to the list
        if new_artifact is not None:
            filtered_artifacts.append(new_artifact)
    return filtered_artifacts


def apply_executor_to_artifacts(artifacts, executor):
    """
    Execute some command and return artifacts from the output.
    """

    new_artifacts = []
    expected_num_fields = len(executor['return-attributes'])
    for artifact in artifacts:
        try:
            cmd = executor['command'].format(**artifact)
        except KeyError:
            continue
        r = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True)
        for line in r.stdout.splitlines():
            line_elems = line.split()
            if len(line_elems) != expected_num_fields:
                raise Exception(
                    'Expected an output with {} field(s) from output `{}`'.format(
                        expected_num_fields, line))
            new_artifact = dict(**artifact)
            new_artifact.update(zip(executor['return-attributes'], line_elems))
            new_artifacts.append(new_artifact)
    return new_artifacts

#
# Read/write schemas and artifacts
#


def get_schema_from_json(json_files):
    """
    Return a schema concatenating the schemas from all files in the same order as given.
    """

    schema = []
    for filename in json_files:
        f = sys.stdin if filename == '-' else open(filename, 'rt')
        schema_item = json.load(f)
        try:
            check_schema(schema_item)
        except Exception as e:
            raise ValueError("KaoN schema error in file {}:" + str(e))
        f.close()
        schema.extend(schema_item)
    return schema


# Internal attributes that are not interesting in outputs
ignore_attributes = ["option-name", "option-doc"]


def restrict_output_attributes(artifacts, output_attributes, ignore_doc_attributes=True):
    """
    Return a list of nonempty entries to print.
    """

    if output_attributes is not None:
        output_artifacts = []
        for artifact in artifacts:
            output_artifact = dict([(k, v) for k, v in artifact.items() if k in output_attributes])
            if output_artifact:
                output_artifacts.append(output_artifact)
    elif ignore_doc_attributes:
        output_artifacts = []
        for artifact in artifacts:
            output_artifact = dict([(k, v)
                                    for k, v in artifact.items() if k not in ignore_attributes])
            if output_artifact:
                output_artifacts.append(output_artifact)
    else:
        output_artifacts = artifacts
    return output_artifacts


def print_artifacts_as_table(artifacts, output_attributes, print_headers, column_separator):
    """
    Print a list of dictionaries each of them in a single line. Filter the properties to show in
    each artifact.
    """

    artifacts = restrict_output_attributes(artifacts, output_attributes)
    if output_attributes is None:
        output_attributes = list(
            set([k for artifact in artifacts for k in artifact.keys() if k not in ignore_attributes]))

    table = [
        [artifact[k] if k in artifact else "_null_" for k in output_attributes]
        for artifact in artifacts]
    if print_headers:
        table.insert(0, output_attributes)

    column_lengths = [0 for _ in range(len(output_attributes))]
    for row in table:
        column_lengths = [max(len(attr), max_col_len)
                          for attr, max_col_len in zip(row, column_lengths)]

    print("\n".join([column_separator.join([v.ljust(col_len)
                                            for v, col_len in zip(row, column_lengths)]) for row in table]))


def print_artifacts_as_json(artifacts, output_attributes):
    """
    Print a list of dictionaries each of them being an artifact. Filter the properties to show in
    each artifact.
    """

    artifacts = restrict_output_attributes(artifacts, output_attributes)
    json.dump(artifacts, sys.stdout, indent=4, sort_keys=True)


def print_artifacts_as_schema(artifacts, output_attributes):
    """
    Print the artifacts as values in a single action schema. Filter the properties to show in
    each artifact.
    """

    artifacts = restrict_output_attributes(
        artifacts, output_attributes, ignore_doc_attributes=False)
    schema = [{'values': artifacts}]
    json.dump(schema, sys.stdout, indent=4, sort_keys=True)

#
# Commandline
#


def get_options_from_schema(schema):
    """
    Get entries with attributes `option_name` and `option_doc`.
    """

    return dict(
        [(entry['option-name'],
          entry['option-doc']) for action in schema
         if 'values' in action for entry in action['values']
         if "option-name" in entry and "option-doc" in entry])


def normalize_value_constrain(values):
    """
    Return a set of possible options allowed for each attribute.
    """

    s = set()
    for value in values:
        if re.fullmatch(r"\d+:\d+", value):
            v = value.split(":")
            s.update([str(i) for i in range(int(v[0]), int(v[1]))])
        elif re.fullmatch(r"\d+:\d+:\d+", value):
            v = value.split(":")
            s.update([str(i) for i in range(int(v[0]), int(v[2]), int(v[1]))])
        else:
            s.add(value)
    return s


def process_args():
    """
    Process the commandline arguments
    """

    prog_description = """
KaoN (KhAOs Nemesis) aggregates information and queries on an information system that emerges
from a fileysystem.
"""

    value_constraints_and_examples = """
Possible constrain expressions <constrain> for an attribute <attr>:
- <value> [<value> ...]: the attribute has any of the given values.
- <num>:<num>: the attibute has integer value between the first number and the second number - 1
- <num>:<num>:<num>: the attribute has an integer value between the first number and the third
  number - 1 in steps of the second number;

Examples:
- Show all configuration files with trajectory between 1000 and 1099
$ kaon.py --kind configuration --cfg_dir cl21_48_96_b6p3_m0p2416_m0p2050 --cfg_num 1000:1100 --show cfg_file

- Show all eigenvectors files with trajectory between 1000 and 1099
$ kaon.py --kind eigenvector --cfg_dir cl21_48_96_b6p3_m0p2416_m0p2050 --cfg_num 1000:1100 --show eig_file

- Show all eigenvectors files whose consiguration exists with trajectory between 1000 and 1099
$ kaon.py --kind configuration eigenvector --cfg_dir cl21_48_96_b6p3_m0p2416_m0p2050 --cfg_num 1000:1100 --show eig_file

- Show all configuration files whose eigenvector does not exist with trajectory between 1000 and 1099
$ kaon.py --kind configuration eigenvector --cfg_dir cl21_48_96_b6p3_m0p2416_m0p2050 --cfg_num 1000:1100 --show cfg_file --eig_file_status missing
"""

    # Do a first commandline parsing to capture the values in the databases
    # that describe arguments
    parser = argparse.ArgumentParser(
        description=prog_description,
        epilog=value_constraints_and_examples, formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)
    parser.add_argument('inputs', metavar='file', nargs='*',
                        help="KaoN schema file, use - to read it from the standard input")
    parser.add_argument('--help', '-h', help='Show help', action='store_true',
                        default=False, required=False)
    try:
        args = parser.parse_known_args()
    except Exception as e:
        print(str(e))
        parser.print_help()
        sys.exit(1)

    if "inputs" not in args[0] or not args[0].inputs:
        help = args[0].help if "help" in args[0] else False
        if not help:
            print("Invalid arguments")
        parser.print_help()
        sys.exit(0 if help else 1)

    # Read schemas
    schema = get_schema_from_json(args[0].inputs)

    # Get options and documentation from the values of the schema
    attribute_options = get_options_from_schema(schema)

    # Do the full commandline parsing
    attributes_str = ", ".join(attribute_options.keys())
    parser.add_argument(
        '--show', metavar='<attr>', nargs='+', required=False,
        help='output only the values of the indicated attributes; if --option-format is `table`, '
        'the printed attributes follows the same order as indicated here. Possible values: ' +
        attributes_str)
    parser.add_argument(
        '--output-format', dest='output_format', nargs=1, required=False,
        choices=['headless-table', 'table', 'json', 'schema'],
        default='headless-table',
        help='how to print the artifacts, in table form with headers (table) '
        'or without headers (headless-table), in a list of dictionaries (json), '
        'or as KaoN schema (schema)')
    parser.add_argument(
        '--column-sep', metavar='<sep>', nargs=1, required=False,
        help='column separation when printing a table', default=[' '])
    group_attributes = parser.add_argument_group('Options for attributes')
    for k, v in attribute_options.items():
        group_attributes.add_argument(
            '--' + k, nargs='+', required=False, help=v, metavar='value')

    args = parser.parse_args()
    # Show help
    if args.help:
        parser.print_help()
        sys.exit(0)

    # Create a view with all the constrains
    view = {}
    for k, v in vars(args).items():
        if v is None or k not in attribute_options:
            continue
        view[k] = normalize_value_constrain(v)

    # Execute the scheme
    artifacts = execute_schema(schema, view)

    # Print the results
    output_attributes = args.show
    output_format = args.output_format[0]
    column_separator = args.column_sep[0]
    if output_format in ['table', 'headless-table']:
        print_artifacts_as_table(artifacts, output_attributes,
                                 output_format == 'table', column_separator)
    elif output_format == 'json':
        print_artifacts_as_json(artifacts, output_attributes)
    else:
        print_artifacts_as_schema(artifacts, output_attributes)


def do_test():
    """
    Minimal tests.
    """

    # Check simple schema with values
    schema = [{
        "values": [
            {"name": "ensemble1"},
            {"name": "ensemble2", "kind": "file"}
        ],
        "update": {"kind": "ensemble"},
        "id": "ensemble-{name}"
    }, {
        "depends": {"name": {"matching-re": "ensemble(?P<num>\d+)", "copy-as": "alias"}},
        "id": "ensemble-{name}"
    }]
    check_schema(schema)
    true_artifacts = [{"kind": "ensemble", "name": "ensemble1", "alias": "ensemble1", "num": "1"},
                      {"kind": "ensemble", "name": "ensemble2", "alias": "ensemble2", "num": "2"}]
    assert(list(execute_schema(schema, {})) == true_artifacts)
    assert(list(execute_schema(schema, {'name': ['ensemble2']})) == true_artifacts[1:])

    schema = [{
        "values": [{"option-name": "prefix", "option-doc": "prefix doc"}],
        "id": "option-{option-name}"
    }, {
        "defaults": {"prefix": "pre0"},
        "values": [
            {},
            {"prefix": "pre1"}
        ],
        "id": "{prefix}"
    }, {
        "defaults": {"o2": "v2"},
        "executor": {"command": "for i in `seq 2` ; do echo {prefix} $i; done", "return-attributes": ["o0", "o1"]},
        "id": "ex-{o0}-{o1}"
    }]
    check_schema(schema)
    true_artifacts = [{"option-name": "prefix", "option-doc": "prefix doc"},
                      {"prefix": "pre0"}, {"prefix": "pre1"},
                      {"prefix": "pre0", "o0": "pre0", "o1": "1", "o2": "v2"},
                      {"prefix": "pre0", "o0": "pre0", "o1": "2", "o2": "v2"},
                      {"prefix": "pre1", "o0": "pre1", "o1": "1", "o2": "v2"},
                      {"prefix": "pre1", "o0": "pre1", "o1": "2", "o2": "v2"}]
    assert(list(execute_schema(schema, {})) == true_artifacts)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == '--test':
        do_test()
    else:
        process_args()
