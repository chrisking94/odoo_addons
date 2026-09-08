# -*- coding: utf-8 -*-
# @Time         : 10:34 2026/9/8
# @Author       : Chris
# @Description  :
from abc import ABC, abstractmethod
from typing import List

from odoo import models

from .base import IAcl, AclUnit
from .recs import RecordSets, RecordSet
from .field import FieldAccess
from .term import OqlDomain


class Expr(IAcl, ABC):

    @classmethod
    def empty(cls, model: models.Model):
        """Empty expression has same meaning as odoo empty domain `[]`"""
        return EmptyExpr(model)

    @abstractmethod
    def eval_rec_sets(self):
        pass


class EmptyExpr(Expr):
    """NULL Design Pattern"""

    def __init__(self, model: models.Model):
        self.model = model

    def eval_rec_sets(self):
        return RecordSets([RecordSet(self.model, OqlDomain.all(self.model._name))])

    def gather_acl_units(self, res: List[AclUnit]):
        pass


class UnaExpr(Expr):
    def __init__(self, opr, operand: FieldAccess):
        self.opr = opr
        self.operand = operand

    def eval_rec_sets(self):
        return self.operand.eval_una("bool")

    def gather_acl_units(self, res: List[AclUnit]):
        self.operand.gather_acl_units(res, "read")


class BinExpr(Expr):
    def __init__(self, left: FieldAccess, opr, right):
        self.left = left
        self.opr = " ".join(opr.lower().split())  # Normalize spaces
        self.right = right

    def eval_rec_sets(self):
        return self.left.eval_bin(self.opr, self.right)

    def gather_acl_units(self, res: List[AclUnit]):
        self.left.gather_acl_units(res, "read")


class LogicExpr(Expr, ABC):
    def __init__(self, left: Expr, right: Expr):
        self.left = left
        self.right = right

    def gather_acl_units(self, res: List[AclUnit]):
        self.left.gather_acl_units(res)
        self.right.gather_acl_units(res)


class AndExpr(LogicExpr):

    def eval_rec_sets(self):
        left = self.left.eval_rec_sets()
        right = self.right.eval_rec_sets()
        return left & right


class OrExpr(LogicExpr):

    def eval_rec_sets(self):
        left = self.left.eval_rec_sets()
        right = self.right.eval_rec_sets()
        return left | right
