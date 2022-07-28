# KaoN Schema

KaoN is a simple data manipulation language. The internal structure is a collection of key-value
dictionaries, referred as `entries`. The keys of an entry, referred as properties, have a string
value associated. The language allows to insert new entries, query, and manipulate them. Also, it
allows to execute shell commands based on entries and process the output to generate new entries.

The KaoN language is currently defined only on JSON.
The KaoN interpreter expects a list of objects where each object describes an `action` on the database
entries. Each `action` is processed in the same order as appearing in the JSON document.

The KaoS database is just a dictionary from _id_, which is a string, into an _entry_, which is a
dictionary of _properties_, string key-value pairs. The process of an action results in a list of
entries that will be added to the database. The action has a formula for computing the id
associated to each entry, specified in the key `"id"`. If there's an entry in the database already
with the same `id`, the properties of the database entry are updated with the new entry properties.

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
* Content of `kaon.json`:
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

* Output of `./kaon.py kaon.json --output-format json`:
  ```json
  [
      {"ens-name": "ensemble1" },
      {"ens-name": "ensemble2" }
  ]
  ```

## `"select"`

If the key `"select"` is present, the action will take as input all database entries that match
the constrains. Otherwise, the action's input will be an empty entry. The possible constrains are:

* an object with property constrains (`_entry_constrains_`).

  The possible constrains are:

  * "interpolate": sets a new property on entries that have all the requested properties, indicated
    between curly brakets, `{property}`.

    Example: 
    * Content of `kaon.json`:
      ```json
      [{
          "name": "add ensembles",
          "modify": [
              {"ens-name": "ensemble1" },
              {"ens-name": "ensemble2" }
          ],
          "id": "ensemble-{ens-name}"
      },{
          "name": "add streams",
          "modify": [
              {"ens-name": "ensemble1", "stream": "stream1" },
              {"ens-name": "ensemble1", "stream": "stream2" },
              {"ens-name": "ensemble2", "stream": "stream1" },
              {"ens-name": "ensemble2", "stream": "stream2" }
          ],
          "id": "stream-{ens-name}-{stream}"
      },{
          "name": "add description",
          "select": { "descrip": { "interpolate": "This is the stream {stream} in ensemble {ens-name}"} },
          "id": "stream-{ens-name}-{stream}"
      }]
      ```
    
    * Output of `./kaon.py kaon.json --output-format json`:
      ```json
      [
          {
              "ens-name": "ensemble1"
          },
          {
              "ens-name": "ensemble2"
          },
          {
              "descrip": "This is the stream stream1 in ensemble ensemble1",
              "ens-name": "ensemble1",
              "stream": "stream1"
          },
          {
              "descrip": "This is the stream stream2 in ensemble ensemble1",
              "ens-name": "ensemble1",
              "stream": "stream2"
          },
          {
              "descrip": "This is the stream stream1 in ensemble ensemble2",
              "ens-name": "ensemble2",
              "stream": "stream1"
          },
          {
              "descrip": "This is the stream stream2 in ensemble ensemble2",
              "ens-name": "ensemble2",
              "stream": "stream2"
          }
      ]
      ```
    Notice that only the entries with properties `ens-name` and `stream` are modified.

  * "in": select entries for which the property has been set and the value is in the list is given.

    Example: 
    * Content of `kaon.json`:
      ```json
      [{
          "name": "add streams",
          "modify": [
              {"ens-name": "ensemble1", "stream": "stream1" },
              {"ens-name": "ensemble1", "stream": "stream2" },
              {"ens-name": "ensemble2", "stream": "stream1" },
              {"ens-name": "ensemble2", "stream": "stream2" }
          ],
          "id": "stream-{ens-name}-{stream}"
      },{
          "name": "add description to ensemble1's streams",
          "select": {
              "descrip": { "interpolate": "This is a ensemble1 stream" },
              "ens-name": { "in": ["ensemble1"] }
          },
          "id": "stream-{ens-name}-{stream}"
      }]
      ```
    
    * Output of `./kaon.py kaon.json --output-format json`:
      ```json
      [
          {
              "descrip": "This is a ensemble1 stream",
              "ens-name": "ensemble1",
              "stream": "stream1"
          },
          {
              "descrip": "This is a ensemble1 stream",
              "ens-name": "ensemble1",
              "stream": "stream2"
          },
          {
              "ens-name": "ensemble2",
              "stream": "stream1"
          },
          {
              "ens-name": "ensemble2",
              "stream": "stream2"
          }
      ]
      ```
    Notice that only the entries with `ens-name` property being `ensemble1` are modified.

    The `"in"` key has a shortcut. The following exemple is equivalent to the above:
    ```json
    [{
        "name": "add streams",
        "modify": [
            {"ens-name": "ensemble1", "stream": "stream1" },
            {"ens-name": "ensemble1", "stream": "stream2" },
            {"ens-name": "ensemble2", "stream": "stream1" },
            {"ens-name": "ensemble2", "stream": "stream2" }
        ],
        "id": "stream-{ens-name}-{stream}"
    },{
        "name": "add description to ensemble1's streams",
        "select": {
            "descrip": { "interpolate": "This is a ensemble1 stream" },
            "ens-name": ["ensemble1"]
        },
        "id": "stream-{ens-name}-{stream}"
    }]
    ```
 
  * "copy-to": select entries for which the property has been set and it copies the value into another property.

    Example: 

    * Content of `kaon.json`:
      ```json
      [{
          "name": "add streams",
          "modify": [
              {"ens-name": "ensemble1", "stream": "stream1" },
              {"ens-name": "ensemble1", "stream": "stream2" },
              {"ens-name": "ensemble2", "stream": "stream1" },
              {"ens-name": "ensemble2", "stream": "stream2" }
          ],
          "id": "stream-{ens-name}-{stream}"
      },{
          "name": "add alias to the ensemble name",
          "select": {
              "ens-name": { "copy-to": "alias" }
          },
          "id": "stream-{ens-name}-{stream}"
      }]
      ```
    
    * Output of `./kaon.py kaon.json --output-format json`:
      ```json
      [
          {
              "alias": "ensemble1",
              "ens-name": "ensemble1",
              "stream": "stream1"
          },
          {
              "alias": "ensemble1",
              "ens-name": "ensemble1",
              "stream": "stream2"
          },
          {
              "alias": "ensemble2",
              "ens-name": "ensemble2",
              "stream": "stream1"
          },
          {
              "alias": "ensemble2",
              "ens-name": "ensemble2",
              "stream": "stream2"
          }
      ]
      ```
    Notice that entries with `ens-name` have a new property `alias`.

  * "move-to": select entries for which the property has been set and it renames the property, or
    deletes it when `null` is given.

    Example: 
    * Content of `kaon.json`:
```json
[{
    "name": "add streams",
    "modify": [
        {"ens-name": "ensemble1", "stream": "stream1" },
        {"ens-name": "ensemble1", "stream": "stream2" },
        {"ens-name": "ensemble2", "stream": "stream1" },
        {"ens-name": "ensemble2", "stream": "stream2" }
    ],
    "id": "stream-{ens-name}-{stream}"
},{
    "name": "rename ens-name to name",
    "select": {
        "ens-name": { "move-to": "name" }
    },
    "id": "stream-{name}-{stream}"
}]
```
    
    * Output of `./kaon.py kaon.json --output-format json`:
      ```json
      [
          {
              "name": "ensemble1",
              "stream": "stream1"
          },
          {
              "name": "ensemble1",
              "stream": "stream2"
          },
          {
              "name": "ensemble2",
              "stream": "stream1"
          },
          {
              "name": "ensemble2",
              "stream": "stream2"
          }
      ]
      ```
    Notice that entries with `ens-name` have a renamed the property to `name`.

  * "matching-re": select entries for which the property has been set and all the properties
    enclosed in curly brackets exits and the value matches the regular expression.
    The regular expression follows the [python `re` module specification](https://docs.python.org/3/library/re.html?highlight=re#regular-expression-syntax).
    Also, new properties are inserted with the captured values.

    Example: 
    * Content of `kaon.json`:
    ```json
[{
    "name": "add streams",
    "modify": [
        {"ens-name": "ensemble1" },
        {"ens-name": "ensemble2" }
    ],
    "id": "ensemble-{ens-name}"
},{
    "name": "extract number from ensemble name",
    "select": {
        "ens-name": { "matching-re": "ensemble(?P<num>\\d+)" }
    },
    "id": "ensemble-{ens-name}"
}]
    ```
    
    * Output of `./kaon.py kaon.json --output-format json`:
    ```json
[
    {
        "ens-name": "ensemble1",
        "num": "1"
    },
    {
        "ens-name": "ensemble2",
        "num": "2"
    }
]
    ```
    Notice that entries with `ens-name` have a new property `num`.

* a list of property constrains headed by `"and"`.

  Select entries that satisfy *any* of the constrains.

  Example: 
  * Content of `kaon.json`:
    ```json
    [{
        "name": "add ensembles",
        "modify": [
            {"ens-name": "ensemble1" },
            {"ens-name": "ensemble2" },
            {"ens-name": "ensemble3" },
            {"ens-name": "ensemble4" }
        ],
        "id": "ensemble-{ens-name}"
    },{
        "name": "add description to ensemble1 and ensemble2",
        "select": [
            "and",
            { "ens-name": ["ensemble1"] },
            { "ens-name": ["ensemble2"] }
        ],
        "modify": {"MeV": "100"},
        "id": "ensemble-{ens-name}"
    }]
    ```
    
  * Output of `./kaon.py kaon.json --output-format json`:
    ```json
    [
        {
            "MeV": "100",
            "ens-name": "ensemble1"
        },
        {
            "MeV": "100",
            "ens-name": "ensemble2"
        },
        {
            "ens-name": "ensemble3"
        },
        {
            "ens-name": "ensemble4"
        }
    ]
    ```
  Notice that entries with `ens-name` either `ensemble1` or `ensemble2` have a new property `MeV`.

* a list of property constrains headed by `"joint"`.

  Select entries that satisfy *all* of the constrains and return objects combining all posible
  entries in each constrain:

  Example: 
  * Content of `kaon.json`:
    ```json
    [{
        "name": "add ensembles",
        "modify": [
            {"ens-name": "ensemble1", "MeV": "150" },
            {"ens-name": "ensemble2", "MeV": "200" }
        ],
        "id": "ensemble-{ens-name}"
    },{
        "name": "add streams",
        "modify": [
            {"ens-name": "ensemble1", "stream": "stream1" },
            {"ens-name": "ensemble1", "stream": "stream2" },
            {"ens-name": "ensemble2", "stream": "stream1" }
        ],
        "id": "stream-{ens-name}-{stream}"
    },{
        "name": "update the streams with the ensemble's MeV",
        "select": [
            "joint",
            { "MeV": {} },
            { "stream": {} }
        ],
        "id": "stream-{ens-name}-{stream}"
    }]
    ```
    
  * Output of `./kaon.py kaon.json --output-format json`:
    ```json
    [
        {
            "MeV": "150",
            "ens-name": "ensemble1"
        },
        {
            "MeV": "200",
            "ens-name": "ensemble2"
        },
        {
            "MeV": "150",
            "ens-name": "ensemble1",
            "stream": "stream1"
        },
        {
            "MeV": "150",
            "ens-name": "ensemble1",
            "stream": "stream2"
        },
        {
            "MeV": "200",
            "ens-name": "ensemble2",
            "stream": "stream1"
        }
    ]
    ```
    Notice that entries with property `MeV` are combined with entries with property `stream` such
    that they have the same value for the common properties, in this case, `ens-name`.


## `"modify"` and `"finalize"`

For each active entree, spawn new entries with the given properties. If a property has a list of
values, it creates one entry for each value. `"modify"` applies to the active entries after `"select"`
and `"finalize"` applies after `"execute"`.

* Content of `kaon.json`:
  ```json
  [{
      "name": "add ensembles",
      "modify": [
          {"ens-name": "ensemble1" },
          {"ens-name": "ensemble2" }
      ],
      "id": "ensemble-{ens-name}"
  }]
  ```
    
* Output of `./kaon.py kaon.json --output-format json`:
  ```json
  [
      {
          "ens-name": "ensemble1"
      },
      {
          "ens-name": "ensemble2"
      }
  ]
  ```

The above example is equivalent to:

```json
[{
    "name": "add ensembles",
    "modify": [
        {"ens-name": ["ensemble1", "ensemble2"]}
    ],
    "id": "ensemble-{ens-name}"
}]
```
 
## `"execute"`

Execute a commandline for each active entree.

* Content of `kaon.json`:
  ```json
  [{
      "name": "add ensembles",
      "modify": [
          {"ens-name": "ensemble1", "dir": "/cache/ensemble1" },
          {"ens-name": "ensemble2", "dir": "/cache/ensemble2" }
      ],
      "id": "ensemble-{ens-name}"
  },{
      "name": "find files",
      "select": {},
      "execute": {
          "command": "find {dir}",
          "return-properties": ["file"]
      }
      "id": "file-{ens-name}-{file}"
  }]
  ```
    
* Possible output of `./kaon.py kaon.json --output-format json`:
  ```json
  [
      {
          "ens-name": "ensemble1",
          "dir": "/cache/ensemble1"
      },
      {
          "ens-name": "ensemble2",
          "dir": "/cache/ensemble2"
      },
      {
          "ens-name": "ensemble1",
          "dir": "/cache/ensemble1",
          "file": "/cache/ensemble1/conf-1.sdb"
      },
      {
          "ens-name": "ensemble1",
          "dir": "/cache/ensemble1",
          "file": "/cache/ensemble1/conf-2.sdb"
      },
      {
          "ens-name": "ensemble2",
          "dir": "/cache/ensemble2",
          "file": "/cache/ensemble2/conf-1.sdb"
      },
  ]
  ```

## `"id"`

The id of each entry is computed with the interpolated
expression in `"id"` key. The properties will be updated if an entry with that id exists already.
Otherwise, a new entry will be added.

...

## `"show-after"` (debugging)

...
