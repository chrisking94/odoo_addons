# @Time         : 14:16 2026/9/8
# @Author       : Chris
# @Description  : Test OQL term ACL through queries.
#
# Terms (oql.term) are query sugar: `searcho("Size='5'")`, `searcho("Waterproof")`
# etc. resolve a term to the records that reference it (attributes / tags via
# `term_ids`, or `oql.term.domain` rows). FieldAccess adds a `UnitKind.TERM`
# unit on the model where the term is referenced (see `field.py`), and
# `_check_perms` checks it exactly like a model unit.
#
# These tests intentionally exercise terms ONLY through real queries
# (`searcho` / `oql`), never through bare ACL APIs, and assert the behaviour of
# the current implementation: a term query succeeds for whoever may read the
# referenced model, and is denied by an `AccessError` once that model read is
# taken away.
#
# Note: a term resolves to the *record sets* of the model that references it
# (an attribute `Size`, an attribute value `'5'`, or a tag `Waterproof`), and
# OQL links such a record set back to `test.oql.product` through the product
# model's shorthand alias rules (`AliasRule.from_orm` keeps only lines whose
# `enable_shorthand` is True, and `meta.get_path` raises "No field path rule
# found" when none matches the record set). The setUp below therefore creates
# the same shorthand aliases as `test_query.py`'s.
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .test_model_defs import post_test
from .test_acl_common import OqlAclProductCase

# Models involved while evaluating the term queries below. Granting these reads
# to the restricted user lets the term expansion search them under the user env.
_TERM_MODELS = ("test.oql.product", "test.oql.template", "test.oql.attribute",
                "test.oql.attribute.value", "test.oql.tag")


def _term_read_access(case, product_read=True):
    """Grant read on every model a term query touches, optionally keeping the
    product model itself inaccessible."""
    for model_name in _TERM_MODELS:
        case.grant_model(model_name, perm_read=product_read if model_name == "test.oql.product" else True)


@tagged("oql_acl_term", "-at_install", "post_install")
class TestOqlAclTerm(OqlAclProductCase):
    """Term queries honour model read access of the referencing model."""

    def setUp(self):
        super().setUp()
        env = self.env

        # Attribute terms: `Size` / `Width` are linked to the attributes that
        # carry their values, mirroring `test_query.py`'s setup.
        term_size = env["oql.term"].create({"name": "Size"})
        term_width = env["oql.term"].create({"name": "Width"})
        self.attr_size.term_ids = [Command.link(term_size.id)]
        self.attr_width.term_ids = [Command.link(term_width.id)]

        # Tag terms: `Waterproof` is attached to the cold tag via `term_ids`;
        # `WeatherAware` matches any `Weather:*` tag through a term domain.
        term_waterproof = env["oql.term"].create({"name": "Waterproof"})
        self.tag_waterproof.term_ids = [Command.link(term_waterproof.id)]

        self.term_weather = env["oql.term"].create({"name": "WeatherAware"})
        env["oql.term.domain"].create({
            "name": "WeatherSelector",
            "term_id": self.term_weather.id,
            "model_id": self.metaTag.id,
            "domain": "[('name', '=like', 'Weather:%')]",
        })

        # Terms are unique by name; the Waterproof/WeatherAware products are
        # found through their tags. `term_hot` is linked for completeness.
        term_hot = env["oql.term"].create({"name": "Hot"})
        self.tag_hot.term_ids = [Command.link(term_hot.id)]

        # Shorthand alias rules on the product model (mirroring `test_query.py`)
        # that say how `test.oql.product` reaches the models its terms reference:
        #   * `attribute_value_ids`           -- `Size='5'` compares against a
        #                                        record set of attribute values;
        #   * `attribute_value_ids.attribute_id` -- links back to the attribute
        #                                        carrying the `Size` term;
        #   * `tag_ids`                       -- `Waterproof` / `WeatherAware`
        #                                        compare against tag records.
        rule = env["oql.alias"].create({"model_id": self.metaProduct.id})
        for alias, path in (
                ("attr_val_records", "attribute_value_ids"),
                ("attrs_records", "attribute_value_ids.attribute_id"),
                ("tag_records", "tag_ids")):
            env["oql.alias.line"].create({
                "alias": alias, "rule_id": rule.id, "path": path,
                "enable_shorthand": True,
            })

    # ---- term queries as a user with model reads ------------------------

    @post_test("term.read_allowed")
    def test_term_queries_allowed_with_read(self):
        """A user allowed to read the referenced model runs term queries and
        gets exactly the same rows the admin sees."""
        _term_read_access(self)

        user_env = self.user_env()
        # Attribute term, binary.
        res = user_env["test.oql.product"].searcho("Size='5'")
        self.assertEqual({"Cold Boot", "Hot Boot"}, set(res.mapped("spu_name")))
        # Attribute term, IN.
        res = user_env["test.oql.product"].searcho("Width in ('D', 'EE')")
        self.assertEqual({"Cold Boot", "Hot Boot"}, set(res.mapped("spu_name")))
        # Tag term (unary), single hit.
        res = user_env["test.oql.product"].searcho("Waterproof")
        self.assertEqual({"Cold Boot"}, set(res.mapped("spu_name")))
        # Tag term through oql.term.domain (unary), both weather tags.
        res = user_env["test.oql.product"].searcho("WeatherAware")
        self.assertEqual({"Cold Boot", "Hot Boot"}, set(res.mapped("spu_name")))

    @post_test("term.read_allowed")
    def test_term_query_oql_statement(self):
        """A full `from ... select ... where <term>` statement is filtered the
        same way under the restricted user."""
        _term_read_access(self)
        user_env = self.user_env()

        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where Waterproof"
        )
        self.assertEqual([{'spu_name': 'Cold Boot'}], res)

        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where Size='6'"
        )
        names = {row['spu_name'] for row in res}
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    @post_test("term.admin")
    def test_term_query_superuser_sanity(self):
        """Admin runs the same term queries without any access configuration."""
        env = self.env
        res = env["test.oql.product"].searcho("Size='5'")
        self.assertEqual({"Cold Boot", "Hot Boot"}, set(res.mapped("spu_name")))
        res = env["test.oql.product"].searcho("Waterproof")
        self.assertEqual({"Cold Boot"}, set(res.mapped("spu_name")))
        res = env["test.oql.product"].searcho("WeatherAware")
        self.assertEqual({"Cold Boot", "Hot Boot"}, set(res.mapped("spu_name")))

    # ---- term queries denied without the referencing model read ---------

    @post_test("term.read_denied")
    def test_term_query_denied_without_model_read(self):
        """Without read access on the model the term is referenced from, a term
        query is rejected with AccessError (the TERM unit is checked exactly
        like a model unit)."""
        # Everything is readable except `test.oql.product` itself.
        _term_read_access(self, product_read=False)
        user_env = self.user_env()

        with self.assertRaises(AccessError):
            user_env["test.oql.product"].searcho("Size='5'")
        with self.assertRaises(AccessError):
            user_env["test.oql.product"].searcho("Waterproof")
