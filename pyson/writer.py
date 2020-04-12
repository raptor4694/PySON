import io, re
import math
from collections.abc import MutableSet

class IdentitySet(MutableSet):
    key = id  # should return a hashable object

    def __init__(self, iterable=()):
        self.map = {} # id -> object
        self |= iterable  # add elements from iterable to the set (union)

    def __len__(self):  # Sized
        return len(self.map)

    def __iter__(self):  # Iterable
        return iter(self.map.values())

    def __contains__(self, x):  # Container
        return self.key(x) in self.map

    def add(self, value):  # MutableSet
        """Add an element."""
        self.map[self.key(value)] = value

    def discard(self, value):  # MutableSet
        """Remove an element.  Do not raise an exception if absent."""
        self.map.pop(self.key(value), None)

    def __repr__(self):
        if self:
            return '{0}([{1}])'.format(self.__class__.__name__, ', '.join(repr(item) for item in self))
        else:
            return self.__class__.__name__ + '()'

class EmptySet(MutableSet):
    def __init__(self, iterable=()):
        pass

    def __len__(self):
        return 0

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration

    def __contains__(self, value):
        return False

    def add(self, value):
        pass

    def discard(self, value):
        pass

    def __repr__(self):
        return self.__class__.__name__ + '()'

class PySONEncoder:
    ALLOWED_TYPES = (dict, list, set, str, int, float, complex, bytes, bytearray, bool, type(None))
    KEY_REGEX = re.compile(r"^[-.\w]+$")

    def __init__(self, fp, skipkeys=False, check_circular=True, 
                 indent=None, default=None, sort_keys=False, 
                 python_constants=False):
        self.fp = fp
        self.write = fp.write
        self.skipkeys = skipkeys
        self.check_circular = check_circular
        self._indent = indent
        self.default = default
        self.sort_keys = sort_keys
        self.already_printed = IdentitySet() if check_circular else EmptySet()
        self.python_constants = python_constants
        if python_constants:
            self.TRUE = 'True'
            self.FALSE = 'False'
            self.INFINITY = 'inf'
            self.NAN = 'nan'
            self.NONE = 'None'
        else:
            self.TRUE = 'true'
            self.FALSE = 'false'
            self.INFINITY = 'Infinity'
            self.NAN = 'NaN'
            self.NONE = 'null'
        self.curr_indent = 0
        if indent is None:
            self.separator = ','
            self.keyseparator = ':'
            self.space = ''
        else:
            self.separator = ', '
            self.keyseparator = ': '
            self.space = ' '

    def indent(self):
        if self._indent is not None:
            self.curr_indent += 1
            if self._indent == 0:
                self.write(' ')
            else:
                self.write('\n')
                self.write(' '*self._indent*self.curr_indent)

    def newline(self):
        if self._indent is not None:
            if self._indent == 0:
                self.write(' ')
            else:
                self.write('\n')
                self.write(' '*self._indent*self.curr_indent)

    def dedent(self):
        if self._indent is not None:
            self.curr_indent -= 1
            if self._indent == 0:
                self.write(' ')
            else:
                self.write('\n')
                self.write(' '*self._indent*self.curr_indent)

    def encode(self, obj):
        try:
            self._encode(obj)
        except TypeError:
            if self.default is None:
                raise 
            self._encode(self.default(obj))

    def _encode(self, obj):
        if obj is None:
            self.encode_None()
        elif isinstance(obj, dict):
            self.encode_dict(obj)
        elif isinstance(obj, (bytes, bytearray)):
            self.encode_bytes(obj)
        elif isinstance(obj, (list, set, tuple)):
            self.encode_list(obj)
        elif isinstance(obj, str):
            self.encode_str(obj)
        elif isinstance(obj, int):
            self.encode_int(obj)
        elif isinstance(obj, float):
            self.encode_float(obj)
        elif isinstance(obj, complex):
            self.encode_complex(obj)
        elif isinstance(obj, bool):
            self.encode_bool(obj)
        else:
            raise TypeError(f"{type(obj).__name__!r} object is not PySON-serializable")

    def encode_None(self):
        self.write(self.NONE)

    def encode_key(self, key):
        if isinstance(key, bytearray):
            self.write(repr(bytes(key)))
        elif isinstance(key, bytes):
            self.write(repr(key))
        elif PySONEncoder.KEY_REGEX.match(key) and key not in (self.TRUE, self.FALSE, self.NONE, self.INFINITY, self.NAN, '-'+self.INFINITY, '+'+self.INFINITY, '-'+self.NAN, '+'+self.NAN):
            self.write(key)
        else:
            self.write(repr(key))

    def encode_dict(self, obj: dict, check_circular=True):
        if check_circular and obj in self.already_printed:
            self.write("{}" if len(obj) == 0 else "...")
            return
        if self._indent is None or self._indent == 0:
            self.encode_dict_braces(obj, check_circular=False)
            return
        self.already_printed.add(obj)
        keys = obj.keys()
        if self.sort_keys:
            keys = sorted(keys)
        else:
            keys = list(keys)

        for i, key in enumerate(keys):
            
            elem = obj[key]
            if not isinstance(key, (str, bytes, bytearray)):
                if isinstance(key, (int, float)):
                    key = repr(key)
                elif isinstance(key, complex):
                    key = repr(key)
                    if key[0] == '(':
                        key = key[1:-1]
                else:
                    raise TypeError(f'Invalid key type: {type(key).__name__!r}')
            if not isinstance(elem, PySONEncoder.ALLOWED_TYPES):
                if self.default is None:
                    raise TypeError(f"{type(elem).__name__!r} object is not PySON-serializable")
                elem = self.default(elem)
            if not isinstance(elem, (dict, set, list, tuple)) or elem not in self.already_printed:
                if i != 0:
                    self.newline()
                self.encode_key(key)
                self.write(self.keyseparator)
                if isinstance(elem, dict):
                    if len(elem) == 0:
                        self.write('{}')
                    else:
                        self.indent()
                        self.encode_dict(elem)
                        self.curr_indent -= 1
                else:
                    self._encode(elem)

    def encode_dict_braces(self, obj: dict, check_circular=True):
        if check_circular and obj in self.already_printed:
            self.write("{}" if len(obj) == 0 else "...")
            return
        self.already_printed.add(obj)
        keys = obj.keys()
        if self.sort_keys:
            keys = sorted(keys)
        else:
            keys = list(keys)

        if len(keys) == 0:
            self.write('{}')
        else:
            self.write('{')
            self.indent()
            if self._indent is None or self._indent == 0:
                separator = ','
            else:
                separator = ''
            
            for i, key in enumerate(keys):
                elem = obj[key]
                if not isinstance(key, (str, bytes, bytearray)):
                    if isinstance(key, (int, float)):
                        key = repr(key)
                    elif isinstance(key, complex):
                        key = repr(key)
                        if key[0] == '(':
                            key = key[1:-1]
                    else:
                        raise TypeError(f'Invalid key type: {type(key).__name__!r}')
                if not isinstance(elem, PySONEncoder.ALLOWED_TYPES):
                    if self.default is None:
                        raise TypeError(f"{type(elem).__name__!r} object is not PySON-serializable")
                    elem = self.default(elem)
                if not isinstance(elem, (dict, set, list, tuple)) or elem not in self.already_printed:
                    if i != 0:
                        if separator:
                            self.write(separator)
                        self.newline()
                    self.encode_key(key)
                    self.write(self.keyseparator)
                    if isinstance(elem, dict):
                        self.encode_dict_braces(elem, check_circular=False)
                    else:
                        self._encode(elem)
                
            self.dedent()
            self.write('}')

    def encode_list(self, lst: list):
        if lst in self.already_printed:
            self.write("[]" if len(lst) == 0 else "...")
            return
        self.already_printed.add(lst)
        elems = [None]*len(lst)
        for i, elem in enumerate(lst):
            if not isinstance(elem, PySONEncoder.ALLOWED_TYPES):
                if self.default is None:
                    raise TypeError(f"{type(elem).__name__!r} object is not PySON-serializable")
                elem = self.default(elem)
            elems[i] = elem
        
        if self._indent is None or self._indent == 0:
            needs_newlines = False
        else:
            for elem in elems:
                if isinstance(elem, (str, bytes, bytearray)) and len(elem) > 4 \
                        or not isinstance(elem, (int, complex, float)) or len(repr(elem)) > 4:
                    needs_newlines = True
                    break
            else:
                needs_newlines = False

        self.write('[')
        if needs_newlines:
            for i, elem in enumerate(elems):
                if i == 0:
                    self.indent()
                else:
                    self.newline()
                if isinstance(elem, dict):
                    self.encode_dict_braces(elem)
                else:
                    self._encode(elem)
            self.dedent()
        else:
            if len(elems) != 0:
                self.write(self.space)
                for i, elem in enumerate(elems):
                    if i != 0:
                        self.write(self.separator)
                    self._encode(elem)
                self.write(self.space)
        self.write(']')

    def encode_str(self, string: str):
        if PySONEncoder.KEY_REGEX.match(string):
            try:
                complex(string)
                self.write(repr(string))
            except ValueError:
                self.encode_key(string)
        elif string.count('\n') > 2:
            if "'" in string and not '"' in string:
                quotes = '"'
            else:
                quotes = "'"
            quotes *= 3

            self.write(quotes + '\n'.join(repr(line)[1:-1] for line in string.splitlines()) + quotes)

        else:
            self.write(repr(string))

    def encode_bytes(self, bts: bytes):
        if bts.count(b'\n') > 2:
            if b"'" in bts and not b'"' in bts:
                quotes = '"'
            else:
                quotes = "'"
            quotes *= 3

            self.write('b' + quotes + '\n'.join(repr(line)[2:-1] for line in bts.splitlines()) + quotes)

        else:
            self.write(repr(bts))

    def encode_int(self, num: int):
        self.write(repr(num))

    def encode_float(self, num: float):
        if num == -math.inf:
            self.write('-')
            self.write(self.INFINITY)
        elif num == math.inf:
            self.write(self.INFINITY)
        elif math.isnan(num):
            self.write(self.NAN)
        else:
            self.write(repr(num))

    def encode_complex(self, num: complex):
        res: str = repr(num)
        if res[0] == '(':
            res: str = res[1:-1]
        if not self.python_constants:
            res = res.replace('inf', self.INFINITY).replace('nan', self.NAN)
        self.write(res)

    def encode_bool(self, b: bool):
        self.write(self.TRUE if b else self.FALSE)

def dumps(obj, skipkeys=False, check_circular=True, 
          indent=None, default=None, sort_keys=False,
          python_constants=False):
    """Serialize ``obj`` as a PySON formatted stream to a string.

    If ``skipkeys`` is true then ``dict`` keys that are not basic types
    (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped
    instead of raising a ``TypeError``.

    If ``check_circular`` is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If ``indent`` is a non-negative integer, then JSON array elements and
    object members will be pretty-printed with that indent level. An indent
    level of 0 will only insert newlines. ``None`` is the most compact
    representation.

    ``default(obj)`` is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    If *sort_keys* is true (default: ``False``), then the output of
    dictionaries will be sorted by key.

    If ``python_constants`` is true, then the following literals will be used:
        LITERAL     | Python Value
        ------------+-------------
        True        | True
        False       | False
        inf         | math.inf
        nan         | math.nan

    Otherwise, the following literals will be used:
        LITERAL     | Python Value
        ------------+-------------
        true        | True
        false       | False
        Infinity    | math.inf
        NaN         | math.nan

    """
    fp = io.StringIO()
    dump(obj, fp, skipkeys, check_circular, indent, default, sort_keys, python_constants)
    return fp.getvalue()

def dump(obj, fp, skipkeys=False, check_circular=True, 
         indent=None, default=None, sort_keys=False,
         python_constants=False):
    """Serialize ``obj`` as a PySON formatted stream to ``fp`` (a
    ``.write()``-supporting file-like object).

    If ``skipkeys`` is true then ``dict`` keys that are not basic types
    (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped
    instead of raising a ``TypeError``.

    If ``check_circular`` is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If ``indent`` is a non-negative integer, then JSON array elements and
    object members will be pretty-printed with that indent level. An indent
    level of 0 will only insert newlines. ``None`` is the most compact
    representation.

    ``default(obj)`` is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    If *sort_keys* is true (default: ``False``), then the output of
    dictionaries will be sorted by key.

    If ``python_constants`` is true, then the following literals will be used:
        LITERAL     | Python Value
        ------------+-------------
        True        | True
        False       | False
        inf         | math.inf
        nan         | math.nan

    Otherwise, the following literals will be used:
        LITERAL     | Python Value
        ------------+-------------
        true        | True
        false       | False
        Infinity    | math.inf
        NaN         | math.nan

    """
    PySONEncoder(fp, skipkeys, check_circular, indent, default, sort_keys, python_constants).encode(obj)
    
