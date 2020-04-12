import textwrap
import math
import re
from enum import IntEnum
from numbers import Number
from collections.abc import Sequence, MutableSet, Iterator
from typing import Union, Dict

def join_natural(iterable, separator=', ', word='and', oxford_comma=True, add_spaces=True):
    if add_spaces:
        if len(word) != 0 and not word[-1].isspace():
            word += ' '
        if len(separator) != 0 and len(word) != 0 and not separator[-1].isspace() and not word[0].isspace():
            word = ' ' + word

    last2 = None
    set_last2 = False
    last1 = None
    set_last1 = False

    result = ""
    for i, item in enumerate(iterable):
        if set_last2:
            if i == 2:
                result += str(last2)
            else:
                result += separator + str(last2)
        last2 = last1
        set_last2 = set_last1
        last1 = item
        set_last1 = True

    if set_last2:
        if result:
            if oxford_comma:
                result += separator + str(last2) + separator + word + str(last1)
            else:
                if add_spaces and not word[0].isspace():
                    word = ' ' + word

                result += separator + str(last2) + word + str(last1)
                
        else:
            if add_spaces and not word[0].isspace():
                word = ' ' + word

            result = str(last2) + word + str(last1)

    elif set_last1:
        result = str(last1)

    return result

class IdentitySet(MutableSet):
    def __init__(self, items=[]):
        self.__values = {}
        self |= items

    def __contains__(self, item):
        return id(item) in self.__values

    def __iter__(self):
        return iter(self.__values.values())

    def __len__(self):
        return len(self.__values)

    def add(self, item):
        self.__values[id(item)] = item

    def discard(self, item):
        self.__values.pop(id(item), None)

class EmptyIterator(Iterator):
    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration

class GhostSet(MutableSet):
    """ A "mutable" set which can never contain any elements. """

    def __init__(self, items=[]):
        pass

    def __contains__(self, item):
        return False

    def __iter__(self):
        return EmptyIterator()

    def __len__(self):
        return 0

    def add(self, item):
        pass

    def discard(self, item):
        pass

class NewlineOption(IntEnum):
    NONE = 0b00
    ALL = 0b11
    DICT_ONLY = 0b10
    LIST_ONLY = 0b01

def model(obj, newlines=True, find_recursion=True, concise_short_lists=True):
    """ Create a pretty-printed string representation of ``obj``.
    This differs from pprint in a few ways:
    1. The keys aren't sorted alphabetically
    2. Subclasses of dict are represented by a dict-literal wrapped in the
       constructor instead of a list of 2-tuples.
    3. The ``newlines`` option
    4. recursion testing can be turned off/on by the ``find_recursion`` parameter.
    You can override the result of model() by providing a __model__() instance method in a custom class.
    If the object does not inherit from either dict, set, list, tuple, str, bytes, bytearray, type, or Number,
    then the following special form is used:
    
    `<type name of the object> [[ <elements of the object (if it is iterable)> ]] [{ <attributes of the object> }]`
    
    Args:
        obj: The object to pretty-print
        newlines (Union[bool, NewlineOption], optional): When a bool, whether to use newlines in objects and lists and tuples and sets. Defaults to True.
            This could also be a NewlineOption enum member.
        find_recursion (bool, optional): Whether to check for recursion. Defaults to True. 
            If False, StackOverflowError may be raised for collections containing themselves.
        concise_short_lists (bool, optional): Whether to *not* separate list elements by newlines if the list is considered short, 
            even if newlines is set to True, NewlineOption.ALL, or NewlineOption.LIST_ONLY. Defaults to True.
    """
    if isinstance(newlines, NewlineOption):
        newlines_model = bool(newlines & 0b10)
        newlines_list = bool(newlines & 0b01)
    else:
        newlines_list = newlines_model = bool(newlines)
    return _model(obj, newlines_list, newlines_model, concise_short_lists, IdentitySet() if find_recursion else GhostSet())

MAX_SHORT_LIST_LEN = 10
"""int: The maximum length a collection may be
to be considered 'short' by the model() function
and not be separated by newlines.
"""

MAX_SHORT_STR_LEN = 5
"""int: The maximum length the string representation of an 
element of a collection may be for the collection
to be considered 'short' by the model() function
and not be separated by newlines.
"""

MAX_LONG_ELEM_PERCENTAGE = 30
"""int (0-100): The maximum percentage allowed
of 'long' elements in a collection before it
is considered 'long' by the model() function
and separated by newlines.
If it is 0, then the collection will
be considered 'long' if any of its elements
are considered 'long'.
"""

def is_long_elem(elem):
    if isinstance(elem, str):
        return len(elem) > MAX_SHORT_STR_LEN
    elif isinstance(elem, (int, float)):
        return len(str(elem)) > MAX_SHORT_STR_LEN
    else:
        return True

def is_long_list(lst: list):
    if len(lst) > MAX_SHORT_LIST_LEN:
        return True
    if MAX_LONG_ELEM_PERCENTAGE == 0:
        for elem in lst:
            if is_long_elem(elem):
                return True
        return False
    else:
        long_count = 0
        for elem in lst:
            if is_long_elem(elem):
                long_count += 1
        return long_count/len(lst) * 100 > MAX_LONG_ELEM_PERCENTAGE

CUSTOM_NUMBER_FORMS: Dict[Number, str] = {}

def _add_number(num, name):
    num = abs(num)
    CUSTOM_NUMBER_FORMS[num] = name
    CUSTOM_NUMBER_FORMS[-num] = '-' + name

_add_number(math.e, 'e')
_add_number(math.pi, 'pi')
for scalar, name in [(1/4, 'pi/4'), (1/3, 'pi/3'), (1/2, 'pi/2'), (2/3, '2*pi/3'), (3/4, '3*pi/4'), (5/4, '5*pi/4'), (4/3, '4*pi/3'), (3/2, '3*pi/2'), (7/3, '7*pi/3'), (7/4, '7*pi/4'), (2, '2*pi')]:
    _add_number(scalar*math.pi, name)

del _add_number

def _model(obj, newlines_list: bool, newlines_model: bool, concise_short_lists: bool, recursion: set):
    if obj is None:
        result = 'None'
    elif hasattr(obj, '__model__'):
        if obj in recursion:
            result = object.__repr__(obj)
        else:
            recursion.add(obj)
            result = obj.__model__(newlines_list, newlines_model)
            if not isinstance(result, str):
                raise TypeError(f'__model__ returned non-string (type {type(result).__name__}')
    elif isinstance(obj, complex):
        real = obj.real
        imag = obj.imag
        if real == 0 and imag == 0:
            result = "0j"
        elif real == 0:
            result = CUSTOM_NUMBER_FORMS.get(imag, repr(imag)) + 'j'
        elif imag < 0:
            result = CUSTOM_NUMBER_FORMS.get(real, repr(real)) + CUSTOM_NUMBER_FORMS.get(imag, repr(imag)) + 'j'
        else:
            result = CUSTOM_NUMBER_FORMS.get(real, repr(real)) + '+' + CUSTOM_NUMBER_FORMS.get(imag, repr(imag)) + 'j'
    elif isinstance(obj, Number):
        result = CUSTOM_NUMBER_FORMS.get(obj, repr(obj))
    elif isinstance(obj, str):
        obj: str
        if len(obj) > 1:
            # attempt to see if it's a regex:
            result = None
            try:
                re.compile(obj)
            except:
                newline_count = 0
                dquote_count = 0
                squote_count = 0
                for c in obj:
                    if c == '\n':
                        newline_count += 1
                    elif c == '"':
                        dquote_count += 1
                    elif c == "'":
                        squote_count += 1
            else:
                punct_count = 0
                newline_count = 0
                dquote_count = 0
                squote_count = 0
                for c in obj:
                    if c == '\n':
                        newline_count += 1
                    elif c == '"':
                        dquote_count += 1
                    elif c == "'":
                        squote_count += 1
                    elif c in "()[]{,}!?@#^|*+-:<=>$":
                        punct_count += 1
                if punct_count >= 3 or len(re.findall(r"(?x) \\ (?:[AbBdDsSwWZ] | (?:(?![0-7][1-7]{2}) | (?=[1-7][0-7]{2}\d)) [1-9] )", obj)) + punct_count >= 3:
                    if newline_count:
                        if squote_count and not dquote_count:
                            quote = '"""'
                        else:
                            quote = "'''"
                        result = "r" + quote + ''.join(line.replace(quote, '\\' + quote) for line in obj.splitlines(keepends=True)) + quote
                    else:
                        if squote_count and not dquote_count:
                            result = 'r"' + obj + '"'
                        else:
                            result = "r'"
                            escape = False
                            for c in obj:
                                if escape:
                                    escape = False
                                elif c == '\\':
                                    escape = True
                                elif c == "'":
                                    result += '\\'
                                result += c
                            result += "'"
                else:
                    result = None

            if result is None:
                if newline_count > 3:
                    if squote_count and not dquote_count:
                        result = '"""' + ''.join(repr(line)[1:-1].replace(r"\"\"\"", R'\"""').replace(r"\'\'\'", "'''") for line in obj.splitlines(keepends=True)) + '"""'
                    else:
                        result = "'''" + ''.join(repr(line)[1:-1].replace(r"\'\'\'", R"\'''").replace(r"\"\"\"", '"""') for line in obj.splitlines(keepends=True)) + "'''"
                else:
                    result = repr(obj)
        else:
            result = repr(obj)
        assert result is not None
    elif isinstance(obj, (type, bytes, bytearray)):
        result = repr(obj)
    elif isinstance(obj, tuple):
        if obj in recursion:
            result = object.__repr__(obj)
        else:
            recursion.add(obj)
            if newlines_list and (not concise_short_lists or is_long_list(obj)):
                result = ',\n'.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
                if result:
                    result = '\n' + textwrap.indent(result, '    ') + '\n'
            else:
                result = ', '.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
            result = '(' + result + ')'
            if type(obj) is not tuple:
                result = f"{type(obj).__name__}({result})"
    elif isinstance(obj, set):
        if obj in recursion:
            result = object.__repr__(obj)
        else:
            recursion.add(obj)
            if newlines_list and (not concise_short_lists or is_long_list(obj)):
                result = ',\n'.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
                if result:
                    result = '\n' + textwrap.indent(result, '    ') + '\n'
            else:
                result = ', '.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
            result = '{' + result + '}'
            if type(obj) is not set:
                result = f"{type(obj).__name__}({result})"
    elif isinstance(obj, list):
        if obj in recursion:
            result = object.__repr__(obj)
        else:
            recursion.add(obj)
            if newlines_list and (not concise_short_lists or is_long_list(obj)):
                result = ',\n'.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
                if result:
                    result = '\n' + textwrap.indent(result, '    ') + '\n'
            else:
                result = ', '.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
            result = '[' + result + ']'
            if type(obj) is not list:
                result = f"{type(obj).__name__}({result})"
    elif isinstance(obj, dict):
        if obj in recursion:
            result = object.__repr__(obj)
        else:
            recursion.add(obj)
            if newlines_model:
                result = ',\n'.join(_model(k, newlines_list, newlines_model, concise_short_lists, recursion) + ': ' + _model(v, newlines_list, newlines_model, concise_short_lists, recursion) for k, v in obj.items())
                if result:
                    result = '\n' + textwrap.indent(result, '    ') + '\n'
            else:
                result = ', '.join(_model(k, newlines_list, newlines_model, concise_short_lists, recursion) + ': ' + _model(v, newlines_list, newlines_model, concise_short_lists, recursion) for k, v in obj.items())
            result = '{' + result + '}'
            if type(obj) is not dict:
                result = f"{type(obj).__name__}({result})"
    else:
        if obj in recursion:
            result = object.__repr__(obj)
        else:
            recursion.add(obj)
            try:
                iter(obj)
            except TypeError:
                result = type(obj).__name__
            else:
                result = f"{type(obj).__name__} ["
                if newlines_list:
                    joined = ',\n'.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
                    if joined:
                        result += '\n' + textwrap.indent(joined, '    ') + '\n'
                else:
                    result += ', '.join(_model(e, newlines_list, newlines_model, concise_short_lists, recursion) for e in obj)
                result += ']'
            

            if newlines_model:
                first = True
                for key, value in vars(obj).items():
                    if first:
                        first = False
                        result += " {\n    "
                    else:
                        result += "\n    "
                    
                    if not re.match(r'[a-zA-Z_][a-zA-Z_0-9]*', key):
                        key = repr(key)
                    
                    result += key + ' = ' + textwrap.indent(_model(value, newlines_list, newlines_model, concise_short_lists, recursion), '    ').lstrip()

                if not first: # has at least 1 entry in obj.__dict__
                    result += "\n}"
            else:
                first = True
                for key, value in obj.__dict__.items():
                    if first:
                        first = False
                        result += ' { '
                    else:
                        result += ', '
                    
                    if not re.match(r'[a-zA-Z_][a-zA-Z_0-9]*', key):
                        key = repr(key)
                    
                    result += key + ' = ' + _model(value, newlines_list, newlines_model, concise_short_lists, recursion)

                if not first: # has at least 1 entry in obj.__dict__
                    result += ' }'

    return result

class LookAheadListIterator(Sequence):
    __slots__ = ('list', 'marker', 'saved_markers', 'default')

    def __init__(self, iterable):
        self.list = list(iterable)

        self.marker = 0
        self.saved_markers = []

        self.default = None

    def __getitem__(self, index):
        return self.list[index]

    def __len__(self):
        return len(self.list)

    def __repr__(self):
        return repr(self.list)

    def __eq__(self, other):
        if isinstance(other, LookAheadListIterator):
            return self.list == other.list
        else:
            return self.list == other

    def __iter__(self):
        return self

    def previous(self):
        try:
            value = self.list[self.marker-1]
            self.marker -= 1
            return value
        except IndexError:
            return None

    def __next__(self):
        try:
            value = self.list[self.marker]
            self.marker += 1
            return value
        except IndexError:
            raise StopIteration

    next = __next__

    def look(self, i=0):
        """ Look ahead of the iterable by some number of values with advancing
        past them.

        If the requested look ahead is past the end of the iterable then None is
        returned.

        """

        try:
            return self.list[self.marker + i]
        except IndexError:
            return self.default

    @property
    def current(self):
        try:
            return self.list[self.marker]
        except IndexError:
            return self.default

    @property
    def last(self):
        try:
            return self.list[self.marker - 1]
        except IndexError:
            return None

    def __enter__(self):
        self.push_marker()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Reset the iterator if there was an error
        if exc_type or exc_val or exc_tb:
            self.pop_marker(True)
        else:
            self.pop_marker(False)

    def push_marker(self):
        """ Push a marker on to the marker stack """
        # print('push marker, stack =', self.saved_markers)
        self.saved_markers.append(self.marker)

    def pop_marker(self, reset):
        """ Pop a marker off of the marker stack. If reset is True then the
        iterator will be returned to the state it was in before the
        corresponding call to push_marker().

        """

        saved = self.saved_markers.pop()
        if reset:
            self.marker = saved