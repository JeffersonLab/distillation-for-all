# KaoN Schema

KaoN is a simple data manipulation language. The internal structure is a collection of key-value
dictionaries, referred as `entries`. The keys and values of an entry referred as attributes and
values are also strings. The language allows to query, manipulate, and insert new entries. Also, it
allows to execute shell commands based on entries and retrieve the output and incorporate it as
entries.

The KaoN language is currently defined only on JSON.
The KaoN interpreter expects a list of objects where each object describes an `action` on the database
entries. Each `action` is processed in the same order as appearing in the JSON document.

The KaoS database is just a dictionary from _id_, which is a string, into an _entry_, which is a
dictionary of _properties_, string key-value pairs. The process of an action results in a list of
entries that will be added to the database. The action has a formula for computing the id
associated to each entry, specified in the key `"id"`. If there's an entry in the database already
with the same `id`, the properties of the database entry are updated with the new entry properties.

Each action is broken into the following steps:

* `select`: select entries in the database that matches the constrains under the action key 
  `depends`. If not given, it returns an entry without properties.

* `defaults`: set attributes with the given values if the entries doesn't have them.

* `values`: spawn new entries setting different properties.

* `exector`: execute a shell command for each entry returned after `values`.

* `update`: 

## General specification

JSON specification of a KaoN schema:

```javascript
kaon_schema = [ _action_ ]

_action_ = {
    /*optional*/ "name": "JSON string",
    /*optional*/ "description": _anything_,
    /*optional*/ "select": _select_item_,
    /*optional*/ "modify": [ _modify_item_ ] or _modify_item_,
    /*optional*/ "execute": [ _execute_item ] or _execute_item_,
    /*optional*/ "finalize": [ _modify_item_ ] or _modify_item_,
    /*optional*/ "show-after": [ _show_after_flag_ ],
    /*optional*/ "id": "JSON string"
}

_select_item = [ "and" _select_item_... ] or
               [ "joint" select_item_... ] or
               _entry_constrains_

_entry_constrains_ = { _property_name_: _property_value or
                                        [_property_value_ ] or
                                        _property_constrain_ }

_property_constrain_ = {
    /*optional*/ "interpolate": _property_value_,
    /*optional*/ "in": [ _property_value_ ] or null
    /*optional*/ "copy-to": _property_name_,
    /*optional*/ "move-to": _property_name_ or null,
    /*optional*/ "matching-re": _property_value_
}

_modify_item = { _property_name_: [ _property_value_ ] or _property_value_ } 

_execute_item = {
    "command": _property_value_,
    "return-properties": [ _property_name_ ]
}

_show_after_flag_ = "select" or "modify" or "execute" or "finalize" or "updated-entries"

_property_value_ = "JSON string" or
                   [ "broken-line", "JSON string"... ] or
                   [ "multiple-lines", "JSON string"... ]

_property_name_ = "JSON string"
```
Pseudocode of the KaoN interpreter:

```python
def execute_kaon_schema(schema):
    entries = {}
    for action in schema:
        if 'select' in action:
            active_entries = select_entries(entries.values(), schema['select'])
        else:
            active_entries = [{}]
        if 'select' in action.get('debug', []): print_entries(active_entries)

        for modify_item in action['modify'] if 'modify' in action else []:
            active_entries = modify_entries(active_entries, modify)
        if 'modify' in action.get('debug', []): print_entries(active_entries)

        for execute_item in action['execute'] if 'execute' in action else []:
            active_entries = execute_entries(active_entries, execute_item)
        if 'execute' in action.get('debug', []): print_entries(active_entries)

        for modify_item in action['finalize'] if 'finalize' in action else []:
            active_entries = modify_entries(active_entries, modify_item)
        if 'finalize' in action.get('debug', []): print_entries(active_entries)

        updated_entries = set()
        for entry in active_entries if 'id' in action else []:
            id = action['id'].format(**entry)
            entries[id] = update_entry(entries[id], entry) if id in entries else entry
            updated_entries.add(id)
        if 'updated-entries' in action.get('debug', []):
            print_entries([entry for id, entry in entries.items() if id in updated_entries])

```
There is two kinds of actions allowed. Ones that insert new entries (specified in the
key `"values"`) and others that update or create new entries based on the database entries. The latter
may filter and transform entries (specified in the key `"depends"`) and execute shell commands
(specified in the key `"executor"`).

The remaining of the document details the possible keys in each action:

## `"name"` and `"description"`

Associate a name and a description to an action. Some error messages and debugging messages may
refer to action's name. They don't have any effect on the result.

Example: 
```json
[{
    "name": "add ensembles",
    "description": "add a couple of ensembles for testing",
    "modify": [
        {"ens-name": "ensemble1" },
        {"ens-name": "ensemble2" }
    ],
    "id": "ensemble-{ens-name}"
}]
```
## `"select"`

If the key `"select"` is present, the action will take as input all database entries that match
the constrains. Otherwise, the action's input will be an empty entry. The possible constrains are:

- a list indicates the values that the entries should have on that property. An empty list
  indicates to filter out entries with some value on that property. Example:

```bash
cat << EOF > schema.json
[{
    "values": [
        {"kind": "ensemble", "name": "ensemble1" },
        {"kind": "ensemble", "name": "ensemble2" }
    ],
    "id": "ensemble-{name}"
},{
    "depends": {
        "name": [ "ensemble1" ]
    },
    "executor": { "command": "echo Hi {name}!" }
}]
EOF
kaon.py schema.json
Hi ensemble1!
```

- a dictionary with a key `copy-as` and a string value indicates that the entries should have some value
  on that property, and copy the value into a new property with the `copy-as` string value associated.
  Example:

```bash
[{
    "values": [
        {"kind": "ensemble", "name": "ensemble1" },
        {"kind": "ensemble", "name": "ensemble2" }
    ],
    "id": "ensemble-{name}"
}, {
    "depends": {
        "name": {"copy-as": "alias"}
    },
    "id": "ensemble-{name}"
}]
EOF
kaon.py schema.json --show kind name alias
ensemble ensemble1 ensemble1
ensemble ensemble2 ensemble2
```

- a dictionary with a key `interpolate` and a string value indicates that the entries
  being referred in the string value (property names enclosed in curly brackets, eg. `{name}`) should have some value, and a new property
  is created with the name indicated in the parent key and the value the result of the string
  interpolation.  Example:

```bash
[{
    "values": [
        {"kind": "ensemble", "name": "ensemble1" },
        {"kind": "ensemble", "name": "ensemble2" }
    ],
    "id": "ensemble-{name}"
}, {
    "depends": {
        "alias": {"interpolate": "the-{name}"}
    },
    "id": "ensemble-{name}"
}]
EOF
kaon.py schema.json --show kind name alias
ensemble ensemble1 the-ensemble1
ensemble ensemble2 the-ensemble2
```

- a dictionary with a key `matching-re` and a string value indicates that the entries
  being referred in the string value (property names enclosed in curly brackets, eg. `{name}`) together
  with parent key should have some value; besides, the parent key should match the regular expression
  define in the string value. The regular expression follows the
  [python `re` module specification](https://docs.python.org/3/library/re.html?highlight=re#regular-expression-syntax);
  also, new properties are inserted with the capture values. Example:

```bash
[{
    "values": [
        {"kind": "ensemble", "name": "ensemble1" },
        {"kind": "ensemble", "name": "ensemble2" }
    ],
    "id": "ensemble-{name}"
}, {
    "depends": {
        "name": {"matching-re": "{kind}(?P<num>\d+)"}
    },
    "id": "{kind}-{name}"
}]
EOF
kaon.py schema.json --show kind name num
ensemble ensemble1 1
ensemble ensemble2 2
```


## `"values"`

List of `entries` to introduce in the database. It cannot be used together with `"executor"`.

Examples:
- Introduce two entries in the database

```bash
cat << EOF > schema.json
[{
    "values": [
        {"kind": "ensemble", "name": "ensemble1" },
        {"kind": "ensemble", "name": "ensemble2" }
    ],
    "id": "ensemble-{name}"
}]
EOF
kaon.py schema.json --show kind name
ensemble ensemble1
ensemble ensemble2
```

Equivalent action: 
```json
[{
    "values": [
        {"name": "ensemble1" },
        {"name": "ensemble2" }
    ],
    "update": {"kind": "ensemble"},
    "id": "ensemble-{name}"
}]
```
## `"defaults"`

...

## `"update"`

...

## `"executor"`

...

## `"id"`

The id of each entry is computed with the interpolated
expression in `"id"` key. The properties will be updated if an entry with that id exists already.
Otherwise, a new entry will be added.

...
