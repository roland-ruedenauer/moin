from _typeshed import Incomplete
from whoosh.query.qcore import Query
from whoosh.query.terms import MultiTerm

class RangeMixin:
    def __unicode__(self): ...
    def __eq__(self, other): ...
    def __hash__(self): ...
    def is_range(self): ...
    def overlaps(self, other): ...
    def merge(self, other, intersect: bool = True): ...

class TermRange(RangeMixin, MultiTerm):
    fieldname: Incomplete
    start: Incomplete
    end: Incomplete
    startexcl: Incomplete
    endexcl: Incomplete
    boost: Incomplete
    constantscore: Incomplete
    def __init__(
        self,
        fieldname,
        start,
        end,
        startexcl: bool = False,
        endexcl: bool = False,
        boost: float = 1.0,
        constantscore: bool = True,
    ) -> None: ...
    def normalize(self): ...

class NumericRange(RangeMixin, Query):
    fieldname: Incomplete
    start: Incomplete
    end: Incomplete
    startexcl: Incomplete
    endexcl: Incomplete
    boost: Incomplete
    constantscore: Incomplete
    def __init__(
        self,
        fieldname,
        start,
        end,
        startexcl: bool = False,
        endexcl: bool = False,
        boost: float = 1.0,
        constantscore: bool = True,
    ) -> None: ...
    def simplify(self, ixreader): ...
    def estimate_size(self, ixreader): ...
    def estimate_min_size(self, ixreader): ...
    def docs(self, searcher): ...
    def matcher(self, searcher, context=None): ...

class DateRange(NumericRange):
    startdate: Incomplete
    enddate: Incomplete
    def __init__(
        self,
        fieldname,
        start,
        end,
        startexcl: bool = False,
        endexcl: bool = False,
        boost: float = 1.0,
        constantscore: bool = True,
    ) -> None: ...
