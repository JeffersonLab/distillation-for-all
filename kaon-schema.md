# KaoN Schema

The specification of the information system passed to KaoN is currently supported only on JSON.
The JSON document should be a list of objects where each object describes an `action` on the database
entries. Each `action` is processed in the same order as appearing in the JSON document.

The KaoS database is just a dictionary from _id_, which is a string, into an _entry_, which is a
dictionary of _properties_, string key-value pairs. The process of an action results in a list of
entries that will be added to the database. The action has a formula for computing the id
associated to each entry, specified in the key `"id"`. If there's an entry in database with the same
`id`, the properties of the database entry are updated with the entries.

There is two kinds of actions allowed. Ones that insert new entries (specified in the
key `"values"`) and others that update or create new entries based on the database entries. The latter
may filter and transform entries (specified in the key `"depends"`) and execute shell commands
(specified in the key `"executor"`).

The remaining of the document details the possible keys in each action:

## `"name"` and `"description"`

Associate a name and a description to an action. They don't have any effect on the result.

Example: 
```json
[{
    "name": "add ensembles",
    "description": "add a couple of ensembles for testing",
    "values": [
        {"name": "ensemble1" },
        {"name": "ensemble2" }
    ],
    "id": "ensemble-{name}"
}]
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
## `"depends"`

If the key `"depends"` is present, the action will take as input all database entries that match
the constrain on each key. The possible constrains are:

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
