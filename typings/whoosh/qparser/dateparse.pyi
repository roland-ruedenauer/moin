from _typeshed import Incomplete
from whoosh.qparser.syntax import SyntaxNode
from whoosh.qparser.taggers import Tagger
from whoosh.qparser.plugins import Plugin

class DateParseError(Exception): ...

def print_debug(level, msg, *args) -> None: ...

class Props:
    __dict__: Incomplete
    def __init__(self, **args) -> None: ...
    def get(self, key, default=None): ...

class ParserBase:
    def to_parser(self, e): ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999) -> None: ...
    def date_from(self, text, dt=None, pos: int = 0, debug: int = -9999): ...

class MultiBase(ParserBase):
    elements: Incomplete
    name: Incomplete
    def __init__(self, elements, name=None) -> None: ...

class Sequence(MultiBase):
    sep_pattern: Incomplete
    sep_expr: Incomplete
    progressive: Incomplete
    def __init__(self, elements, sep: str = "(\\s+|\\s*,\\s*)", name=None, progressive: bool = False) -> None: ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...

class Combo(Sequence):
    fn: Incomplete
    min: Incomplete
    max: Incomplete
    def __init__(
        self, elements, fn=None, sep: str = "(\\s+|\\s*,\\s*)", min: int = 2, max: int = 2, name=None
    ) -> None: ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...
    def dates_to_timespan(self, dates): ...

class Choice(MultiBase):
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...

class Bag(MultiBase):
    sep_expr: Incomplete
    onceper: Incomplete
    requireall: Incomplete
    allof: Incomplete
    anyof: Incomplete
    def __init__(
        self,
        elements,
        sep: str = "(\\s+|\\s*,\\s*)",
        onceper: bool = True,
        requireall: bool = False,
        allof=None,
        anyof=None,
        name=None,
    ) -> None: ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...

class Optional(ParserBase):
    element: Incomplete
    def __init__(self, element) -> None: ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...

class ToEnd(ParserBase):
    element: Incomplete
    def __init__(self, element) -> None: ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...

class Regex(ParserBase):
    fn: Incomplete
    modify: Incomplete
    pattern: Incomplete
    expr: Incomplete
    def __init__(self, pattern, fn=None, modify=None) -> None: ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...
    def extract(self, match): ...
    def modify_props(self, props) -> None: ...
    def props_to_date(self, props, dt): ...

class Month(Regex):
    patterns: Incomplete
    exprs: Incomplete
    pattern: Incomplete
    expr: Incomplete
    def __init__(self, *patterns) -> None: ...
    def modify_props(self, p) -> None: ...

class PlusMinus(Regex):
    pattern: Incomplete
    expr: Incomplete
    def __init__(self, years, months, weeks, days, hours, minutes, seconds) -> None: ...
    def props_to_date(self, p, dt): ...

class Daynames(Regex):
    next_pattern: Incomplete
    last_pattern: Incomplete
    pattern: Incomplete
    expr: Incomplete
    def __init__(self, next, last, daynames) -> None: ...
    def props_to_date(self, p, dt): ...

class Time12(Regex):
    pattern: str
    expr: Incomplete
    def __init__(self) -> None: ...
    def props_to_date(self, p, dt): ...

class DateParser:
    day: Incomplete
    year: Incomplete
    time24: Incomplete
    time12: Incomplete
    simple: Incomplete
    def __init__(self) -> None: ...
    def setup(self) -> None: ...
    def get_parser(self): ...
    def parse(self, text, dt, pos: int = 0, debug: int = -9999): ...
    def date_from(self, text, basedate=None, pos: int = 0, debug: int = -9999, toend: bool = True): ...

class English(DateParser):
    day: Incomplete
    plusdate: Incomplete
    dayname: Incomplete
    time: Incomplete
    month: Incomplete
    dmy: Incomplete
    datetime: Incomplete
    bundle: Incomplete
    torange: Incomplete
    all: Incomplete
    def setup(self): ...

class DateParserPlugin(Plugin):
    basedate: Incomplete
    dateparser: Incomplete
    callback: Incomplete
    free: Incomplete
    freeexpr: Incomplete
    def __init__(
        self,
        basedate=None,
        dateparser=None,
        callback=None,
        free: bool = False,
        free_expr: str = "([A-Za-z][A-Za-z_0-9]*):([^^]+)",
    ) -> None: ...
    def taggers(self, parser): ...
    def filters(self, parser): ...
    def errorize(self, message, node): ...
    def text_to_dt(self, node): ...
    def range_to_dt(self, node): ...
    def do_dates(self, parser, group): ...

class DateTimeNode(SyntaxNode):
    has_fieldname: bool
    has_boost: bool
    fieldname: Incomplete
    dt: Incomplete
    boost: float
    def __init__(self, fieldname, dt, boost: float = 1.0) -> None: ...
    def r(self): ...
    def query(self, parser): ...

class DateRangeNode(SyntaxNode):
    has_fieldname: bool
    has_boost: bool
    fieldname: Incomplete
    start: Incomplete
    end: Incomplete
    boost: float
    def __init__(self, fieldname, start, end, boost: float = 1.0) -> None: ...
    def r(self): ...
    def query(self, parser): ...

class DateTagger(Tagger):
    plugin: Incomplete
    expr: Incomplete
    def __init__(self, plugin, expr) -> None: ...
    def match(self, parser, text, pos): ...
