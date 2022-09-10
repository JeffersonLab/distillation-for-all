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

# Log levels, for now, 0 (no logging) and 1 (some logging)
LOG_LEVEL = 0

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


def check_list_or_dict(value, path):
    """
    Check that the input is a dictionary or a list.
    """

    show_error(isinstance(value, (list, dict)),
               "unexpected type, expected either an object (dictionary) or a list", path)


def check_flat_list(value, path):
    """
    Check that the input is a list of strings.
    """

    check_list(value, path)
    for i, v in enumerate(value):
        check_string(v, f"{path}/[{i}]")


def check_dict_with_keywords(value, path, keywords):
    """
    Check that input is a dictionary with keys in `keywords` and values passing the check function
    associated as the `keywords` dictionary values.
    """

    check_dict(value, path)
    all_keywords = ", ".join(keywords.keys())
    for k, v in value.items():
        show_error(k in keywords,
                   f"unexpected key, it should be one of {all_keywords}.", f"{path}/{k}")
        keywords[k](v, f"{path}/{k}")


def is_property_value(value):
    """
    Check that the input is a JSON string or [ "broken-line", "string"... ] or
    [ "multiple-lines", "string"... ].
    """

    return (isinstance(value, str) or
            isinstance(value, list) and
            len(value) > 0 and value[0] in ('broken-line', 'multiple-lines') and
            all([isinstance(v, str) for v in value[1:]]))


def check_property_value(value, path):
    """
    Check "JSON string" or [ "broken-line", "JSON string"... ] or
    [ "multiple-lines", "JSON string"... ].
    """

    show_error(
        isinstance(value, str) or
        isinstance(value, list) and len(value) > 0 and value[0] in (
            'broken-line', 'multiple-lines'),
        'expected a string or a list headed with "broken-line" or "multiple-lines" '
        'and the remaining elements being strings', path)
    if isinstance(value, list):
        for i, v in enumerate(value[1:]):
            check_string(v, f"{path}/[{i+1}]")


def check_property_constrain_in(value, path):
    """
    Check [ _property_value_ ] or null
    """

    show_error(value is None or isinstance(value, list),
               "expected `null` or a list of strings", path)
    if isinstance(value, list):
        for i, v in enumerate(value):
            check_property_value(v, f"{path}/[i]")


def check_string_or_null(value, path):
    """
    Check that the input is either a string or null
    """

    show_error(value is None or isinstance(value, str), "expected either a string or `null`", path)


def check_property_constrains(value, path):
    """
    Check _property_constrain_ = {
        /*optional*/ "interpolate": _property_value_,
        /*optional*/ "in": [ _property_value_ ] or null
        /*optional*/ "copy-to": _property_name_,
        /*optional*/ "move-to": _property_name_ or null,
        /*optional*/ "matching-re": _property_value_ }
    """

    check_dict(value, path)
    keywords = {
        'interpolate': check_property_value,
        'in': check_property_constrain_in,
        'copy-to': check_string,
        'move-to': check_string_or_null,
        'matching-re': check_property_value
    }
    for k, v in value.items():
        if not(is_property_value(v) or
                isinstance(v, list) and all([is_property_value(vi) for vi in v])):
            check_dict_with_keywords(v, f"{path}/{k}", keywords)


def check_select(value, path):
    """
    Check that the input is either an entry constrain or a list of empty constrains headed by the
    string "and" or "joint".
    """

    check_list_or_dict(value, path)
    if isinstance(value, dict):
        check_property_constrains(value, path)
    elif isinstance(value, list):
        show_error(len(value) > 1,
                   "expected either a dictionary or a list with at least two elements", path)
        show_error(value[0] in ("and", "joint"), 'expected either "and" or "joint"', f"{path}/[0]")
        for i, entry_constrains in enumerate(value[1:]):
            check_property_constrains(entry_constrains, f"{path}/[{i+1}]")


def check_modify(value, path):
    """
    Check that the input is a dictionary with values a list of  _property_value_ or a list of those.
    """

    check_list_or_dict(value, path)
    if isinstance(value, list):
        for i, v in enumerate(value):
            check_modify(v, f"{path}/[{i}]")
    else:
        for k, v in value.items():
            check_string(k, path)
            if not is_property_value(v):
                check_list(v, f"{path}/{k}")
                for i, list_value in enumerate(v):
                    check_property_value(list_value, f"{path}/{k}/[i]")


def check_execute(value, path):
    """
    Check that the input is a dictionary with {
        "command": _property_value_,
        "return-properties": [ _property_name_ ] }
    """

    check_list_or_dict(value, path)
    if isinstance(value, list):
        for i, v in enumerate(value):
            check_execute(v, f"{path}/[{i}]")
    else:
        keywords = {
            'command': check_property_value,
            'return-properties': check_flat_list
        }
        check_dict_with_keywords(value, path, keywords)


def check_show_after(value, path):
    """
    Check that the input is a list of any of the following strings:
    "select" or "modify" or "execute" or "finalize" or "updated-entries"
    """

    check_list(value, path)
    for i, v in enumerate(value):
        show_error(v in ("select", "modify", "execute", "finalize", "updated-entries"),
                   'expected either "select" or "modify" or "execute" or "finalize" or "updated-entries"',
                   f"{path}/[i]")


def check_schema(value):
    """
    Check that the input is a list of dictionaries satisfying the scheme.
    """

    check_list(value, "/")
    keywords = {
        'name': check_string,
        'description': lambda _, __: None,
        'select': check_select,
        'modify': check_modify,
        'execute': check_execute,
        'finalize': check_modify,
        'show-after': check_show_after,
        'id': check_string
    }
    for i, v in enumerate(value):
        action_name = f"[name='{v['name']}']" if isinstance(v, dict) and 'name' in v else f"[{i}]"
        check_dict_with_keywords(v, action_name, keywords)


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

def print_entries_for_debugging(entries, action, step):
    """
    Print entries in JSON format for helping user debug the schema.
    """

    if "show-after" not in action or step not in action['show-after']:
        return

    header = f"Entries after applying `{step}`" if step != "updated-entries" else "Updated entries"
    sys.stderr.write(f"> {header}\n")
    json.dump(entries, sys.stderr, indent=4, sort_keys=True)
    sys.stderr.write("\n")


def make_a_list(value):
    """
    Return [value] if value isn't a list. Otherwise return value.
    """

    return value if isinstance(value, list) else [value]


def get_property_value(value):
    """
    Return a string or a list of strings."
    """

    if is_property_value(value):
        if isinstance(value, str):
            return value
        return ("" if value[0] == 'broken-line' else "\n").join(value[1:])
    return [get_property_value(v) for v in value]


def execute_schema(schema, constrained_view, env):
    """
    Execute each of the actions in the schema in the same order as given.
    """

    entries = {}
    for i, action in enumerate(schema):
        action_name = action.get('name', f"[{i}]")
        if LOG_LEVEL > 0:
            sys.stderr.write(f"Running action `{action_name}`\n")

        if 'select' in action:
            active_entries = select_entries(entries.values(), action['select'], env)
        else:
            active_entries = [{}]
        print_entries_for_debugging(active_entries, action, 'select')

        active_entries = [
            new_entry for modify_item in make_a_list(action.get('modify', [{}]))
            for entry in active_entries for new_entry in modify_entry(entry, modify_item)]
        print_entries_for_debugging(active_entries, action, 'modify')

        for j, execute_item in enumerate(make_a_list(action.get('execute', []))):
            try:
                active_entries = execute_entries(active_entries, execute_item, env)
            except Exception as e:
                raise Exception(f"Error in {action_name}/execute/[j].") from e
        print_entries_for_debugging(active_entries, action, 'execute')

        active_entries = [
            new_entry for modify_item in make_a_list(action.get('finalize', [{}]))
            for entry in active_entries for new_entry in modify_entry(entry, modify_item)]
        print_entries_for_debugging(active_entries, action, 'finalize')

        updated_entries = set()
        for entry in active_entries if 'id' in action else []:
            try:
                id = action['id'].format(
                    **dict_with_defaults(apply_at_defaults_on_entry(entry), env))
            except KeyError as e:
                raise Exception(
                    f"Error interpolating the id in action with name `{action_name}` for entry {entry}.") from e
            entries[id] = apply_at_defaults_on_entry(
                dict_with_defaults(entry, entries[id]) if id in entries else entry)
            updated_entries.add(id)
        if 'updated-entries' in action.get('show-after', []):
            print_entries_for_debugging(
                [entry for id, entry in entries.items() if id in updated_entries], action,
                'updated-entries')

    # Apply the constrains
    entries = [entry for entry in entries.values()
               if is_entry_in_constrained_view(entry, constrained_view)]
    return entries


def apply_defaults(artifacts, defaults):
    """
    Set missing attributes.
    """

    for artifact in artifacts:
        for k, v in defaults.items():
            artifact.setdefault(k, v)


def is_entry_in_view(entry, view):
    """
    Return whether the entry satisfies the constrains in the view.
    """

    for k, v in view.items():
        if k in entry and entry[k] not in v:
            return False
    return True


def is_entry_in_constrained_view(entry, constrained_view):
    """
    Return whether the entry satisfies any of the views.
    """

    for view in constrained_view:
        if is_entry_in_view(entry, view):
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


def apply_at_defaults_on_entry(entry):
    """
    If there's a property name ended in "@default" renamed as the property without "@default" if
    there is not a property with that name.
    """

    new_entry = {}
    suffix = "@default"
    for k, v in entry.items():
        if k.endswith(suffix):
            prop_without_suffix = k[0:-len(suffix)]
            if prop_without_suffix not in entry:
                new_entry[prop_without_suffix] = v
        else:
            new_entry[k] = v
    return new_entry


def select_entries(entries, select_item, env):
    """
    Return entries that passes the select specification.
    """

    if isinstance(select_item, dict):
        return get_entries_with_property_constrain(entries, select_item, env)

    entries_list = [select_entries(entries, item, env) for item in select_item[1:]]
    return joint_entries_list(entries_list) if select_item[0] == "joint" else add_entries_list(entries_list)


def get_entry_after_property_constrains(entry, entry_constrains, env):
    """
    Return a list of entries after applying the constrains.
    """

    return_entry = dict(**entry)
    for prop, prop_constrains in entry_constrains.items():
        if is_property_value(prop_constrains):
            if prop not in entry or get_property_value(prop_constrains) != entry[prop]:
                return None
            continue
        if isinstance(prop_constrains, list) and all([is_property_value(v) for v in prop_constrains]):
            if prop not in entry or entry[prop] not in [get_property_value(v) for v in prop_constrains]:
                return None
            continue

        assert isinstance(prop_constrains, dict)
        if not prop_constrains:
            prop_constrains = {'in': None}
        if "interpolate" in prop_constrains:
            try:
                value = get_property_value(prop_constrains["interpolate"]).format(
                    **apply_at_defaults_on_entry(dict_with_defaults(entry, env)))
            except KeyError as e:
                return None
            if prop in entry and entry[prop] != value:
                return None
            return_entry[prop] = value
        if 'in' in prop_constrains:
            if prop_constrains['in'] is None and prop not in entry:
                return None
            if prop_constrains['in'] is not None and len(prop_constrains['in']) == 0 and prop in entry:
                return None
            if prop_constrains['in'] is not None and (len(prop_constrains['in']) > 0 and
                                                      (prop not in entry or entry[prop] not in prop_constrains['in'])):
                return None
        if 'copy-to' in prop_constrains:
            if prop not in entry:
                return None
            return_entry[prop_constrains['copy-to']] = entry[prop]
        if 'move-to' in prop_constrains:
            if prop not in entry:
                return None
            if prop_constrains['move-to'] is not None:
                return_entry[prop_constrains['move-to']] = entry[prop]
            del return_entry[prop]
        if "matching-re" in prop_constrains:
            if "interpolate" in prop_constrains:
                value = return_entry[prop]
            elif prop in entry:
                value = entry[prop]
            else:
                return None
            try:
                m = re.fullmatch(get_property_value(prop_constrains['matching-re'])
                                 .format(**apply_at_defaults_on_entry(dict_with_defaults(entry,
                                                                                         env))),
                                 value)
            except KeyError:
                return None
            if not m:
                return None
            return_entry.update(m.groupdict())
    return return_entry


def add_entries_list(entries_list):
    """
    Add all entries into a single list.
    """

    return [entry for entries in entries_list for entry in entries]


def joint_entries_list(entries_list):
    """
    Joint entries from all lists without conflicting values for the shared properties.
    """

    # Find the common attributes to all entries
    if sum([len(entries) for entries in entries_list]) > 0:
        common_properties = list(set.intersection(
            *[set(entry.keys()) for entries in entries_list for entry in entries]))
    else:
        common_properties = []

    # Trivial case: if there's no common property just do the Cartesian product of the lists
    if len(common_properties) == 0:
        return [{k: v for ti in t for k, v in ti} for t in itertools.product(*entries_list)]

    # Classify the entries of all lists that have the same values for the common properties
    joint = {}  # tuple(property_value) -> tuple(entries)
    for i, entries in enumerate(entries_list):
        for entry in entries:
            joint_key = tuple([entry[k] for k in common_properties])
            if joint_key not in joint:
                joint[joint_key] = tuple([[] for _ in range(len(entries_list))])
            joint[joint_key][i].append(entry)

    # Return the Cartesian product of all entries with the same shared properties
    return_entries = []
    for joint_value in joint.values():
        for t in itertools.product(*joint_value):
            new_entry = {}
            for entry in t:
                new_entry.update(entry)
            return_entries.append(new_entry)
    return return_entries


def get_entries_with_property_constrain(entries, entry_constrains, env):
    """
    Return a list of entries after applying the constrains.
    """

    return_entries = []
    for entry in entries:
        new_entry = get_entry_after_property_constrains(entry, entry_constrains, env)
        if new_entry is not None:
            return_entries.append(new_entry)
    return return_entries


def modify_entry(entry, modify_item):
    """
    Apply the properties in modify_item to the entry.
    """

    entries = [entry]
    for prop, values in modify_item.items():
        entries = [dict_with_defaults({prop: value}, entry)
                   for value in make_a_list(get_property_value(values)) for entry in entries]
    return entries


def execute_entries(entries, execute_item, env):
    """
    Execute some command and return entries from the output.
    """

    new_entries = []
    expected_num_fields = len(execute_item['return-properties'])
    for entry in entries:
        try:
            cmd = get_property_value(execute_item['command']).format(
                **dict_with_defaults(apply_at_defaults_on_entry(entry), env))
        except KeyError:
            continue
        if LOG_LEVEL > 0:
            sys.stderr.write(f"Executing commandline: {cmd}\n")
        r = subprocess.run(cmd, stdout=subprocess.PIPE,
                           universal_newlines=True, shell=True, check=True)
        for line in r.stdout.splitlines():
            line_elems = line.split(sep=execute_item.get('split', None))
            if len(line_elems) != expected_num_fields:
                raise Exception(
                    f'Expected an output with {expected_num_fields} field(s) from output `{line}`')
            new_entries.append(dict_with_defaults(entry, dict(zip(execute_item['return-properties'],
                                                                  line_elems))))
    return new_entries

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
    schema = [{'modify': artifacts}]
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
        if 'select' in action or 'execute' in action:
            continue
        for entry in execute_schema([action], [{}], {}):
            if "option-name" in entry and "option-doc" in entry:
                r[entry['option-name']] = (entry['option-name'], entry['option-doc'],
                                           entry.get('option-group', ''))
    return r.values()


def get_variables_from_schema(schema):
    """
    Get entries with attributes `variable-name` and `variable-doc`.
    """

    r = {}
    for action in schema:
        if 'select' in action or 'execute' in action:
            continue
        for entry in execute_schema([action], [{}], {}):
            if "variable-name" in entry and "variable-doc" in entry:
                r[entry['variable-name']] = (entry['variable-name'],
                                             entry.get('variable-default', None),
                                             entry['variable-doc'])
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
    parser.add_argument('--log', action='store_true', default=False, required=False)
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

    # Set log level
    LOG_LEVEL = 1 if args.log else 0

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
        "modify": [
            {"name": ["broken-line", "ensemble1"]},
            {"name": "ensemble2", "kind": ["multiple-lines", "file"]}
        ],
        "finalize": {"kind": "ensemble"},
        "id": "ensemble-{name}"
    }, {
        "select": {"name": {"matching-re": r"ensemble(?P<num>\d+)", "copy-to": "alias"}},
        "id": "ensemble-{name}"
    }]
    check_schema(schema)
    true_artifacts = [{"kind": "ensemble", "name": "ensemble1", "alias": "ensemble1", "num": "1"},
                      {"kind": "ensemble", "name": "ensemble2", "alias": "ensemble2", "num": "2"}]
    assert execute_schema(schema, [{}], {}) == true_artifacts
    assert execute_schema(schema, [{'name': ['ensemble2']}], {}) == true_artifacts[1:]

    schema = [{
        "modify": [{"option-name": "prefix", "option-doc": "prefix doc"}],
        "id": "option-{option-name}"
    }, {
        "modify": [
            {"prefix@default": "pre0"},
            {"prefix": "pre1"}
        ],
        "id": "{prefix}"
    }, {
        "select": {},
        "modify": {"o2@default": "v2"},
        "execute": {
            "command": "for i in `seq 2` ; do echo {prefix} $i; done",
            "return-properties": ["o0", "o1"]
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
