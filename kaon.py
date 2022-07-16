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
import re
import itertools
import argparse
import subprocess

LOG_LEVEL = 1

#
# Check schema types
#


def show_error(check_value, msg, path):
    """
    If `check_value` is False, then the message error `msg` is raised up.
    """

    if not check_value:
        raise ValueError(f"Error in path `{path}`: {msg}")


def check_string(value, path):
    """
    Check that the input is a string.
    """

    show_error(isinstance(value, str),
               "unexpected type, it should be a string", path)


def check_list(value, path):
    """
    Check that the input is a list.
    """

    show_error(isinstance(value, list),
               "unexpected type, it should be a list", path)


def check_dict(value, path):
    """
    Check that the input is a dictionary.
    """

    show_error(isinstance(value, dict),
               "unexpected type, it should be an object (dictionary)", path)


def check_flat_dict(value, path):
    """
    Check that the input is a dictionary with keys and values as strings.
    """

    check_dict(value, path)
    for k, v in value.items():
        show_error(isinstance(k, str) and isinstance(v, str),
                   "unexpected type, the key and the value should be strings", f"{path}/{k}")


def check_list_flat_dicts(value, path):
    """
    Check that the input a list of flat dictionaries
    """

    check_list(value, path)
    for i, v in enumerate(value):
        check_flat_dict(v, f"{path}/[{i}]")


def check_flat_list(value, path):
    """
    Check that the input is a list of strings.
    """

    check_list(value, path)
    for i, v in enumerate(value):
        check_string(v, f"{path}/[{i}]")


def check_depends_value_dict(value, path):
    """
    Check that the input is a dictionary with possible entries `matching-re`, `interpolate`,
    and `copy-as`.
    """

    check_dict(value, path)
    for k, v in value.items():
        show_error(k in ("matching-re", "copy-as", "interpolate"),
                   "unexpected key, it can be `matching-re`, `interpolate`, or `copy-as`",
                   f"{path}/{k}")
        check_string(v, f"{path}/{k}")
    show_error('interpolate' not in value or 'copy-as' not in value,
               "unexpected key, `interpolate` and `copy-as` cannot be together", value)


def check_depends(value, path):
    """
    Check that the input is a dictionary where the keys are strings and the values can be a list
    of strings or a dictionary satisfying depends value dictionary restriction.
    """

    check_dict(value, path)
    for k, v in value.items():
        check_string(k, path)
        if isinstance(v, list):
            check_flat_list(v, f"{path}/{k}")
        elif isinstance(v, dict):
            check_depends_value_dict(v, f"{path}/{k}")
        else:
            show_error(False, "unexpected value, it should be a list or an object", f"{path}/{k}")


def check_executor(value, path):
    """
    Check that the input is a dictionary where the keys are `command`, with a string value,
    `return-attributes` with a plain list, and optionally `split` with a string.
    """

    check_dict(value, path)
    for k, v in value.items():
        show_error(k in ("command", "return-attributes", "split"),
                   "unexpected key, it can be `command` or `return-attributes`", f"{path}/{k}")
        check_string(k, path)
        if k == "command":
            check_string(v, f"{path}/{k}")
        elif k == "return-attributes":
            check_flat_list(v, f"{path}/{k}")
        elif k == 'split':
            check_string(v, f"{path}/{k}")
    show_error("command" in value and "return-attributes" in value,
               "missing keys, expected `command` and `return-attributes` as keys", path)


def check_action(value, path):
    """
    Check that the input is a dictionary with keys `id`, `depends`, `executor` (optional), `values`
    (optional), `defaults` (optional), and `update` (optional).
    """

    check_dict(value, path)
    for k, v in value.items():
        if k == "name":
            check_string(v, f"{path}/{k}")
        elif k == "description":
            check_string(v, f"{path}/description")
        elif k == "id":
            check_string(v, f"{path}/id")
        elif k == "depends":
            check_depends(v, f"{path}/depends")
        elif k == "executor":
            check_executor(v, f"{path}/executor")
        elif k == "values":
            check_list_flat_dicts(v, f"{path}/values")
        elif k == "defaults":
            check_flat_dict(v, f"{path}/defaults")
        elif k == "update":
            check_flat_dict(v, f"{path}/update")
        elif k == "debug":
            check_flat_list(v, f"{path}/debug")
        else:
            show_error(False, "unexpected key", f"{path}/{k}")
    show_error("id" in value, "expected key `id` is missing", path)


def check_schema(value):
    """
    Check that the input is a list of dictionaries satisfying the scheme.
    """

    check_list(value, "/")
    for i, v in enumerate(value):
        action_name = f"[name='{v['name']}']" if isinstance(v, dict) and 'name' in v else f"[{i}]"
        check_action(v, action_name)


def check_constrain_item(value, path):
    """
    Check that the input is a dictionary with possible values a list of strings or a string.
    """

    check_dict(value, path)
    for k, v in value.items():
        check_string(k, value)
        if not isinstance(v, str):
            check_flat_list(v, f"{path}/{k}")


def check_constrains(value):
    """
    Check that the input is a list of dictionaries satisfying a constrain schema.
    """

    check_list(value, "/")
    for i, v in enumerate(value):
        check_constrain_item(v, f"[{i}]")


#
# Execute schemas
#

def print_artifacts_for_debugging(artifacts, action, step):
    """
    Print artifacts in JSON format for helping user debug the schema.
    """

    if "debug" not in action or step not in action['debug']:
        return

    headers = {
        "depends": "Entries after applying `depends`",
        "values": "Entries after applying `values`",
        "executor": "Entries after applying `executor`",
        "update": "Entries after applying `update`",
        "final": " Modified entries by the action",
    }
    sys.stderr.write(f"> {headers[step]}\n")
    json.dump(artifacts, sys.stderr, indent=4, sort_keys=True)
    sys.stderr.write("\n")


def execute_schema(schema, constrained_view, env):
    """
    Execute each of the actions in the schema in the same order as given.
    """

    artifacts = {}
    for i, action in enumerate(schema):
        action_name = action.get('name', f"[{i}]")
        if "debug" in action:
            sys.stderr.write(f"Running action `{action_name}`\n")

        # a) Apply depends
        filtered_artifacts = apply_depends_to_artifacts(
            artifacts.values(), [{}], env, action['depends']) if 'depends' in action else [{}]
        print_artifacts_for_debugging(filtered_artifacts, action, "depends")

        # b) Apply defaults
        apply_defaults(filtered_artifacts, action.get('defaults', {}))
        print_artifacts_for_debugging(filtered_artifacts, action, "defaults")

        # c) Apply values
        if "values" in action:
            new_artifacts = [dict_with_defaults(d, artifact)
                             for d in action['values'] for artifact in filtered_artifacts]
        else:
            new_artifacts = filtered_artifacts
        print_artifacts_for_debugging(new_artifacts, action, "values")

        # e) Apply executor
        if 'executor' in action:
            try:
                new_artifacts = apply_executor_to_artifacts(new_artifacts, env, action['executor'])
            except Exception as e:
                raise Exception(
                    f"Error in executing executor in action with name `{action_name}`.") from e
        print_artifacts_for_debugging(new_artifacts, action, "executor")

        # f) Apply update
        if "update" in action:
            for artifact in new_artifacts:
                artifact.update(action["update"])
        print_artifacts_for_debugging(new_artifacts, action, "update")

        # g) Merge the new entries into artifacts
        the_ids = set()
        track_updated_entries = ("debug" in action and "final" in action['debug'])
        for artifact in new_artifacts:
            # Compute the identification
            try:
                the_id = action['id'].format(**dict_with_defaults(artifact, env))
            except KeyError as e:
                raise Exception(
                    f"Error interpolating the id in action with name `{action_name}` for entry {artifact}.") from e
            if the_id in artifacts:
                artifacts[the_id].update(artifact)
            else:
                artifacts[the_id] = artifact
            if track_updated_entries:
                the_ids.add(the_id)
        if track_updated_entries:
            updated_entries = [v for k, v in artifacts.items() if k in the_ids]
            print_artifacts_for_debugging(updated_entries, action, "final")

    # Apply the constrains
    artifacts = [artifact for artifact in artifacts.values()
                 if is_artifact_in_constrained_view(artifact, constrained_view)]
    return artifacts


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


def is_artifact_in_constrained_view(artifact, constrained_view):
    """
    Return whether the artifact satisfies any of the views.
    """

    for view in constrained_view:
        if is_artifact_in_view(artifact, view):
            return True
    return False


def dict_with_defaults(a, defaults):
    """
    Return the first dictionary with key-values from the second dictionary if missing in the first one.
    """

    r = dict(**a)
    for k, v in defaults.items():
        r.setdefault(k, v)
    return r


def apply_depends(artifact, env, depends):
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
        if "matching-re" in v:
            try:
                m = re.fullmatch(
                    v['matching-re'].format(**dict_with_defaults(artifact, env)), artifact[k])
            except KeyError:
                return None
            if not m:
                return None
            new_artifact.update(m.groupdict())
        if "copy-as" in v:
            new_artifact[v['copy-as']] = artifact[k]
        elif "interpolate" in v:
            try:
                new_artifact[k] = v["interpolate"].format(**dict_with_defaults(artifact, env))
            except KeyError as e:
                return None
    return new_artifact


def apply_depends_to_artifacts(artifacts, constrained_view, env, depends):
    """
    Filter artifacts that pass the constrains in the view and depends.
    """

    filtered_artifacts = []
    for artifact in artifacts:
        # Ignore artifacts that don't pass the view
        if not is_artifact_in_constrained_view(artifact, constrained_view):
            continue
        # Apply depends
        new_artifact = apply_depends(artifact, env, depends)
        # Append new artifact to the list
        if new_artifact is not None:
            filtered_artifacts.append(new_artifact)
    return filtered_artifacts


def apply_executor_to_artifacts(artifacts, env, executor):
    """
    Execute some command and return artifacts from the output.
    """

    new_artifacts = []
    expected_num_fields = len(executor['return-attributes'])
    for artifact in artifacts:
        try:
            cmd = executor['command'].format(**dict_with_defaults(artifact, env))
        except KeyError:
            continue
        if LOG_LEVEL > 0:
            sys.stderr.write(f"Executing commandline: {cmd}\n")
        r = subprocess.run(cmd, stdout=subprocess.PIPE,
                           universal_newlines=True, shell=True, check=True)
        for line in r.stdout.splitlines():
            line_elems = line.split(sep=executor.get('split', None))
            if len(line_elems) != expected_num_fields:
                raise Exception(
                    f'Expected an output with {expected_num_fields} field(s) from output `{line}`')
            new_artifact = dict(**artifact)
            new_artifact.update(zip(executor['return-attributes'], line_elems))
            new_artifacts.append(new_artifact)
    return new_artifacts

#
# Read/write schemas, constrains, and artifacts
#


def get_schema_from_json(json_files):
    """
    Return a schema concatenating the schemas from all files in the same order as given.
    """

    schema = []
    for filename in json_files:
        try:
            f = sys.stdin if filename == '-' else open(filename, 'rt')
            schema_item = json.load(f)
            check_schema(schema_item)
            if filename != '-':
                f.close()
        except Exception as e:
            raise ValueError(f"KaoN schema error in file {filename}") from e
        schema.extend(schema_item)
    return schema


def normalize_value_constrain(values):
    """
    Return a set of possible options allowed for each attribute.
    """

    if not isinstance(values, list):
        values = [values]
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


def get_constrains_from_json(json_files):
    """
    Return a list of constrains concatenating the constrains from all given files.
    """

    constrains = []
    for filename in json_files:
        try:
            f = sys.stdin if filename == '-' else open(filename, 'rt')
            constrains_item = json.load(f)
            f.close()
            check_constrains(constrains_item)
        except Exception as e:
            raise ValueError("KaoN constrains error in file {}:") from e
        # Normalize the constrains
        normalize_constrains_item = [{k: normalize_value_constrain(v) for k, v in constrain.items()}
                                     for constrain in constrains_item]
        constrains.extend(normalize_constrains_item)
    return constrains


# Internal attributes that are not interesting in outputs
ignore_attributes = ["option-name", "option-doc", "option-group",
                     "variable-name", "variable-doc", "variable-default"]


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
            set([k for artifact in artifacts for k in artifact.keys()
                 if k not in ignore_attributes]))

    table = [
        [artifact[k] if k in artifact else "_null_" for k in output_attributes]
        for artifact in artifacts]
    if print_headers:
        table.insert(0, output_attributes)

    column_lengths = [0 for _ in range(len(output_attributes))]
    for row in table:
        column_lengths = [max(len(attr), max_col_len)
                          for attr, max_col_len in zip(row, column_lengths)]
    if table:
        print("\n".join([
            column_separator.join([v.ljust(col_len)
                                   for v, col_len in zip(row, column_lengths)]) for row in table]))


def print_artifacts_as_json(artifacts, output_attributes):
    """
    Print a list of dictionaries each of them being an artifact. Filter the properties to show in
    each artifact.
    """

    artifacts = restrict_output_attributes(artifacts, output_attributes)
    json.dump(artifacts, sys.stdout, indent=4, sort_keys=True)
    sys.stdout.write('\n')


def print_artifacts_as_schema(artifacts, output_attributes):
    """
    Print the artifacts as values in a single action schema. Filter the properties to show in
    each artifact.
    """

    artifacts = restrict_output_attributes(
        artifacts, output_attributes, ignore_doc_attributes=False)
    schema = [{'values': artifacts}]
    json.dump(schema, sys.stdout, indent=4, sort_keys=True)
    sys.stdout.write('\n')

#
# Commandline
#


def get_options_from_schema(schema):
    """
    Get entries with attributes `option-name` and `option-doc`.
    """

    r = {}
    for action in schema:
        for entry in action.get('values', []):
            extended_entry = dict(**entry)
            apply_defaults(extended_entry, action.get('defaults', {}))
            extended_entry.update(action.get('update', {}))
            if "option-name" in extended_entry and "option-doc" in extended_entry:
                r[extended_entry['option-name']] = (extended_entry['option-name'],
                                                    extended_entry['option-doc'],
                                                    extended_entry.get('option-group', ''))
    return r.values()


def get_variables_from_schema(schema):
    """
    Get entries with attributes `variable-name` and `variable-doc`.
    """

    r = {}
    for action in schema:
        for entry in action.get('values', []):
            extended_entry = dict(**entry)
            apply_defaults(extended_entry, action.get('defaults', {}))
            extended_entry.update(action.get('update', {}))
            if "variable-name" in extended_entry and "variable-doc" in extended_entry:
                r[extended_entry['variable-name']] = (extended_entry['variable-name'],
                                                      extended_entry.get('variable-default', None),
                                                      extended_entry['variable-doc'])
    return r.values()


def get_constrained_view(constrains, view):
    """
    Apply the view to all given constrains.
    """

    # If no constrain, just return the view
    if not constrains:
        return [view]

    output_constrains = []
    for constrain in constrains:
        new_constrain = dict(**constrain)
        for k, v in view.items():
            new_constrain[k] = new_constrain[k].intersect(v) if k in new_constrain else v
        output_constrains.append(new_constrain)
    return output_constrains


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
    parser.add_argument('--constrains', help='JSON file with a list of constrains', nargs='+',
                        required=False, default=[])
    try:
        args = parser.parse_known_args()
    except Exception as e:
        print(str(e))
        parser.print_help()
        sys.exit(1)

    if "inputs" not in args[0] or not args[0].inputs:
        show_help = args[0].help if "help" in args[0] else False
        if not show_help:
            print("Invalid arguments")
        parser.print_help()
        sys.exit(0 if show_help else 1)

    # Read schemas
    schema = get_schema_from_json(args[0].inputs)

    # Get options, variables, and documentation from the values of the schema
    attribute_options = get_options_from_schema(schema)
    attribute_variables = get_variables_from_schema(schema)

    # Do the full commandline parsing
    attributes_str = ", ".join([k for k, _, _ in attribute_options])
    parser.add_argument(
        '--show', metavar='<attr>', nargs='+', required=False,
        help='output only the values of the indicated attributes; if --option-format is `table`, '
        'the printed attributes follows the same order as indicated here. Possible values: ' +
        attributes_str)
    parser.add_argument(
        '--output-format', dest='output_format', nargs=1, required=False,
        choices=['headless-table', 'table', 'json', 'schema'],
        default=['headless-table'],
        help='how to print the artifacts, in table form with headers (table) '
        'or without headers (headless-table), in a list of dictionaries (json), '
        'or as KaoN schema (schema)')
    parser.add_argument(
        '--column-sep', metavar='<sep>', nargs=1, required=False,
        help='column separation when printing a table', default=[' '])
    group_attributes = {}
    for k, v, g in attribute_options:
        if g not in group_attributes:
            group_attributes[g] = parser.add_argument_group(
                'Options for {}'.format(g if g else 'attributes'))
        group_attributes[g].add_argument(
            f'--{k}', nargs='+', required=False, help=v, metavar='value')
    group_attributes = parser.add_argument_group('Variables')
    for k, default, doc in attribute_variables:
        group_attributes.add_argument(
            f'--{k}', nargs=1, required=default is None, help=doc, metavar='value',
            default=[default])
    args = parser.parse_args()

    # Show help
    if args.help:
        parser.print_help()
        sys.exit(0)

    # Create a view with all the constrains
    vars_args = vars(args)
    view = {}
    for k, _, _ in attribute_options:
        if k in vars_args and vars_args[k] is not None:
            view[k] = normalize_value_constrain(vars_args[k])

    # Load extra constrains
    constrains = get_constrains_from_json(args.constrains)
    constrained_view = get_constrained_view(constrains, view)

    # Get environment for interpolation
    env = {}
    for k, _, _ in attribute_variables:
        env[k] = vars_args[k][0]

    # Execute the scheme
    artifacts = execute_schema(schema, constrained_view, env)

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
        "depends": {"name": {"matching-re": r"ensemble(?P<num>\d+)", "copy-as": "alias"}},
        "id": "ensemble-{name}"
    }]
    check_schema(schema)
    true_artifacts = [{"kind": "ensemble", "name": "ensemble1", "alias": "ensemble1", "num": "1"},
                      {"kind": "ensemble", "name": "ensemble2", "alias": "ensemble2", "num": "2"}]
    assert execute_schema(schema, [{}], {}) == true_artifacts
    assert execute_schema(schema, [{'name': ['ensemble2']}], {}) == true_artifacts[1:]

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
        "depends": {},
        "defaults": {"o2": "v2"},
        "executor": {
            "command": "for i in `seq 2` ; do echo {prefix} $i; done",
            "return-attributes": ["o0", "o1"]
        },
        "id": "ex-{o0}-{o1}"
    }]
    check_schema(schema)
    true_artifacts = [{"option-name": "prefix", "option-doc": "prefix doc"},
                      {"prefix": "pre0"}, {"prefix": "pre1"},
                      {"prefix": "pre0", "o0": "pre0", "o1": "1", "o2": "v2"},
                      {"prefix": "pre0", "o0": "pre0", "o1": "2", "o2": "v2"},
                      {"prefix": "pre1", "o0": "pre1", "o1": "1", "o2": "v2"},
                      {"prefix": "pre1", "o0": "pre1", "o1": "2", "o2": "v2"}]
    assert execute_schema(schema, [{}], {}) == true_artifacts


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == '--test':
        do_test()
    else:
        process_args()
