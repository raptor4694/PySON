import pyson, json, pprint
import re
from pyson.tokenize import *
from tokenprinter import *
from builtins import open
from collections import OrderedDict

filename = R'C:\Users\lrezac\Documents\vscode-javapp\vscode-javapp\syntaxes\javapp.tmLanguage.pyson'
INDENT_REGEX = re.compile(r"^(\s*).*$")
NAME_REGEX = re.compile(r"name:.*$")

with open(filename, 'r') as file:
    lines: list = file.readlines()

def get_indent(line: str):
    match = INDENT_REGEX.match(line)
    # print(f'get_indent({line!r}): match = {match}')
    return match[1]

index = 0
def search(curindent: str):
    global lines, index
    if index >= len(lines):
        return
    line: str = lines[index]
    if line.startswith(curindent):
        if len(line) > len(curindent) and line[len(curindent)].isspace():
            indent = get_indent(line)
            search(indent)
            return
    else:
        indent = get_indent(line)
        if len(indent) > len(curindent):
            search(indent)
        return
    start_index = index
    name_index = None
    while index < len(lines):
        line: str = lines[index]
        if line.startswith(curindent):
            if line.startswith("name:", len(curindent)):
                name_index = index
            elif len(line) > len(curindent) and line[len(curindent)].isspace():
                indent = get_indent(line)
                search(indent)
                continue
            index += 1
        else:
            indent = get_indent(line)
            if len(indent) > len(curindent):
                search(indent)
            else:
                break

    if name_index is not None and name_index != start_index:
        name_line: str = lines[name_index]
        print('Moving line', name_index, 'above line', start_index)
        print('   the line:', name_line.lstrip())
        del lines[name_index]
        lines.insert(start_index, name_line)

search("")

with open(filename, 'w') as file:
    file.writelines(lines)

# def visit(elem):
#     if isinstance(elem, dict):
#         if len(elem) > 1 and 'name' in elem:
#             newelem = OrderedDict()
#             newelem['name'] = elem['name']
#             for key, value in elem.items():
#                 if key != 'name':
#                     newelem[key] = visit(value)
#             elem = newelem
#     elif isinstance(elem, list):
#         for i in range(len(elem)):
#             elem[i] = visit(elem[i])
#     elif isinstance(elem, tuple):
#         elem = tuple(visit(subelem) for subelem in elem)
#     return elem

# data = visit(data)

# with open(filename, 'w') as file:
#     pyson.dump(data, file, indent=4)

# obj = {
#     'key1': 'value1',
#     'key2': 'value2',
#     'list1': [1,2,3,4],
#     'list2': [
#         {
#             'key1': 'value1',
#             'key2': 'value2'
#         },
#         {
#             'key1': 'value2',
#             'key2': 'value1'
#         }
#     ],
#     'object1': {
#         'key1': 'value 1',
#         'key2': 'value 2'
#     },
#     'Infinity': float("inf"),
#     'inf': float("inf"),
#     "0.2": "0.2",
#     b"bytes": True
# }

# print(pyson.dumps(obj, indent=None))

# with open('data.json') as f:
    # print(f.read())

# with open('data.cson', 'rb') as f:
#     print_tokens(tokenize(f.readline))

# with open('data.pyson', 'rb') as f:
    # data = pyson.load(f)
# data = pyson.loads("""
# list1: [
#     id: bcaa9bbe-ff57-44c0-b9ec-9276f208455c
#     value: 82932652004413992431
#     id: bc83a66c-c2ab-41d1-aa55-d8fb2a38ce81
#     value: 98472786162101876596
#     id: ab82fa1d-7642-4de4-8279-09867a3d034d
#     value: 92503826752001134910
#     False
# ]
# flag1: @list1.3
# object1:
#     key: elem_attrs
#     value:
#         id: @key
#         value: False
# object2: { key: "value 2", value: { id: @key, value: True } }
# object3: @object1
#     key2: "value 2"
# object4: @object2 { key2: "value 3" }
# object5:
#     name: object5
#     id: object5
# object6: @object5 name: object6
# object7:
#     key1: value1
# object8: @object7
#     key2: value2
# object9:
#     **object8
#     key3: value3
# object10: dict(
#     key1: value1,
#     key2: value2
# )
# object11:
#     key2: value2
# list2:
#     - 1
#     - 2
#     - False
#     - key1: value1
#       **object11
#       key3: value3
#     - key1: value2
#       key2: value4
#     -
#         key1: value1
#         key2: value2
#     - **object10
#       key3: value4
#     - -- element1
#       -- element2
#     - @object1.value.id
#     - -inf
# """)

# print(pyson.util.model(data))
# print(pprint.pformat(data, indent=4))

# print(json.dumps(data, ensure_ascii=False, indent=4))