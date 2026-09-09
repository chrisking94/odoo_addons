# @Description  : Python-like chained select expression, e.g. `tag_ids[0].name`,
#   `partner.mapped('name')`. Each step runs against the previous step's value
#   with real Python semantics; the base value is each row's own record.
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from odoo import models

from .base import IRecsReader, AclUnit, UnitKind
from .field import FieldAccess
from .func import FuncCall
from .util import tn
from odoo.tools.translate import _


def _chain_attr(value: Any, name: str, expr: str):
    """Read an attribute (field / bound method / python attribute) from a value."""
    if isinstance(value, models.Model):
        # Let Odoo resolve attrs; an empty set still exposes bound methods.
        try:
            attr = getattr(value, name)
            if callable(attr):
                # Since it's impossible to collect static ACL units from an arbitrary
                # model method, we need to downgrade records to use odoo's built-in ACL.
                attr = getattr(value.sudo(False), name)
            return attr
        except Exception as e:
            raise Exception(_("OQL chain `%s`: failed reading `%s` on `%s`: %s")
                            % (expr, name, tn(value), e)) from e
    if isinstance(value, dict):
        if name in value:
            return value[name]
        raise Exception(_("OQL chain `%s`: key `%s` not found in dict `%s`.")
                        % (expr, name, value))
    try:
        return getattr(value, name)
    except AttributeError as e:
        raise Exception(_("OQL chain `%s`: `%s` has no attribute `%s`.")
                        % (expr, tn(value), name)) from e


def _chain_index(value: Any, index: int, expr: str):
    """Apply `__getitem__`: subscript a recordset / list / tuple / sequence."""
    if isinstance(value, (models.Model, list, tuple, str, bytes, dict)):
        try:
            return value[index]
        except Exception as e:
            raise Exception(_("OQL chain `%s`: can't index `%s` with `%s`: %s")
                            % (expr, tn(value), index, e)) from e
    if value is None or value is False:
        raise Exception(_("OQL chain `%s`: can't index empty value `%s` with `%s`.")
                        % (expr, value, index))
    raise Exception(_("OQL chain `%s`: `%s` is not subscriptable with `%s`.")
                    % (expr, tn(value), index))


def _chain_call(value: Any, argv: List[Any], expr: str):
    """Call the current value (a bound method / callable)."""
    if not callable(value):
        raise Exception(_("OQL chain `%s`: `%s` is not callable.")
                        % (expr, tn(value)))
    return value(*argv)


class Step(ABC):

    __slots__ = ()

    @abstractmethod
    def chip(self) -> str:
        """Source fragment of this step, e.g. `.name`, `[0]`, `(...)`."""
        raise NotImplementedError

    def __repr__(self):
        keys = getattr(type(self), "__slots__", ())
        args = ", ".join("%s=%r" % (k, getattr(self, k)) for k in keys)
        return "%s(%s)" % (type(self).__name__, args)


class StepAttr(Step):
    """`.name` attribute navigation; payload: attribute/field name (`str`)."""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def chip(self) -> str:
        return "." + self.name


class StepIndex(Step):
    """`[n]` subscript (`__getitem__`); payload: index (`int`)."""

    __slots__ = ("index",)

    def __init__(self, index: int):
        self.index = index

    def chip(self) -> str:
        return "[%s]" % self.index


class StepCall(Step):
    """`(...)` call on the current value; payload: positional argv (`list`)."""

    __slots__ = ("args",)

    def __init__(self, args: List[Any]):
        self.args = args

    def chip(self) -> str:
        return "(...)"


class StepHead(Step):
    """Receiver-less head call carried as a per-row column.

    Payload is a `FuncCall`; only used when further steps follow the head
    (a bare head call with no further steps stays a `FuncCall`).
    """

    __slots__ = ("func",)

    def __init__(self, func: FuncCall):
        self.func = func

    def chip(self) -> str:
        return self.func.name + "(...)"


class Chain(IRecsReader):
    """A chained select expression, evaluated step by step per row record.

    Unlike a plain `FieldAccess` (which reads a whole dot path at once), a
    chain applies each `Step` to the real value produced by the previous one,
    so it supports method calls / subscripts: `tag_ids[0].name`,
    `partner.mapped('name')`, `read(['id'])[0].id` (the head call is carried
    as a `StepHead(FuncCall)`; without further steps it stays a FuncCall).
    """

    def __init__(self, model: models.Model, meta, steps: List[Step],
                 as_: Optional[str] = None):
        self.model = model
        self.meta = meta
        self.steps = list(steps)
        self._as = as_ or self.text

    # -- IRecsReader ------------------------------------------------
    @property
    def is_agg(self) -> bool:
        return False

    @property
    def as_(self) -> str:
        return self._as

    @as_.setter
    def as_(self, value: str):
        self._as = value

    # -- diagnostics ------------------------------------------------
    @property
    def text(self) -> str:
        """Approximate source text of the chain, e.g. `tag_ids[0].name`."""
        return ''.join(step.chip() for step in self.steps).lstrip('.')

    @property
    def path(self) -> str:
        return self.text

    # -- read -------------------------------------------------------
    def read(self, recs, load='_classic_read') -> list:
        if recs._name != self.model._name:  # noqa
            raise Exception(_("Expect `%s` records, got `%s`.")
                            % (self.model._name, recs._name))  # noqa
        # Pre-evaluate whole-recordset inputs, aligned per row: `StepHead` head
        # calls and `IRecsReader` args of `StepCall` become per-row columns.
        preps = []
        for step in self.steps:
            if isinstance(step, StepHead):
                data = step.func.read(recs, load)
                if len(data) != len(recs):
                    raise Exception(_("OQL chain `%s`: head call `%s(...)` yields one "
                                      "aggregate value, it can't be followed by steps.")
                                    % (self.text, step.func.name))
                preps.append(data)
            elif isinstance(step, StepCall):
                cols = []
                for arg in step.args:
                    if isinstance(arg, IRecsReader):
                        col = arg.read(recs, load)
                        if len(col) != len(recs):
                            raise Exception(_("OQL chain `%s`: an argument of method "
                                              "call is not aligned with the records.")
                                            % self.text)
                        cols.append((True, col))
                    else:
                        cols.append((False, arg))
                preps.append(cols)
            else:
                preps.append(None)
        # Evaluate step by step per row record.
        rows = []
        for i, rec in enumerate(recs):
            value = rec
            for si, step in enumerate(self.steps):
                if isinstance(step, StepHead):
                    value = preps[si][i]
                elif isinstance(step, StepAttr):
                    value = _chain_attr(value, step.name, self.text)
                elif isinstance(step, StepIndex):
                    value = _chain_index(value, step.index, self.text)
                else:  # StepCall
                    argv = [data[i] if flag else data for (flag, data) in preps[si]]
                    value = _chain_call(value, argv, self.text)
            rows.append(value)
        return rows

    # -- ACL ---------------------------------------------------------
    def gather_acl_units(self, res: List[AclUnit], mode):
        """Best-effort static ACL gathering.

        Field steps fold into a `FieldAccess`; an attribute directly followed
        by a call is a METHOD unit on the record model receiving the call.
        Note: after a method call the result model isn't statically known, so
        later steps aren't gathered (documented limitation).
        """
        cur = self.model  # model of the current value; `None` if unknown / scalar
        names: List[str] = []  # consecutive field attributes under `cur`
        steps = self.steps
        i, n = 0, len(steps)
        while i < n:
            step = steps[i]
            if isinstance(step, StepHead):
                # Gather the receiver-less head call (method + its field args),
                # then stop: the returned value's model isn't statically known.
                step.func.gather_acl_units(res, mode)
                break
            if isinstance(step, StepAttr):
                is_method = i + 1 < n and isinstance(steps[i + 1], StepCall)
                if is_method:
                    rmodel = self._gather_fields(res, mode, cur, names)
                    if rmodel is not None:
                        res.append(AclUnit(rmodel, step.name, UnitKind.METHOD, "invoke"))
                    cur, names = None, []
                    i += 2  # skip the call step (it belongs to the method)
                    continue
                names.append(step.name)
            elif isinstance(step, StepIndex):
                pass  # Subscript on a recordset does not change the model.
            i += 1
        if cur is not None and names:
            self._gather_fields(res, mode, cur, names)

    def _gather_fields(self, res, mode, cur, names) -> Optional[models.Model]:
        """Gather FIELD units of `names` relative to model `cur`.

        Returns the rear model after reading the path, or `None` when the
        path ends on a non-relational value (or is not resolvable).
        """
        if cur is None or not names:
            return cur
        try:
            fa = FieldAccess(cur, names, self.meta)
        except Exception:  # noqa: BLE001  not statically resolvable
            return None
        fa.gather_acl_units(res, mode)
        return fa.rear_model

    def __str__(self):
        return f"{type(self).__name__}({self.text})"

    def __repr__(self):
        return str(self)
