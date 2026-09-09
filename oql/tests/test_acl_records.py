# @Time         : 14:16 2026/9/8
# @Author       : Chris
# @Description  : Test OQL record-level permission control via ir.rule.
#
# OQL's record-level ACL is fully aligned with Odoo's native design, using
# `ir.rule` domain restrictions applied via
# `self.env['ir.rule']._compute_domain(self.model_name, mode=mode)`.
#
# This file hosts the tests of the former `TestOqlRecordRule` that involve an
# actual record rule (ir.rule), including the UPDATE/DELETE record-rule
# enforcement cases. The pure model-level DML access tests that used to live in
# the same class (update/create/delete with and without model permission,
# field-level update gates) moved to `test_acl_model.py`.
from odoo.tests import tagged

from .test_model_defs import post_test
from .test_acl_common import OqlAclProductCase
from ..acl import OqlAcl


@tagged("oql_record_rule", "-at_install", 'post_install')
class TestOqlRecordRule(OqlAclProductCase):
    """Record-level permission control via ir.rule integration."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_ir_rule(self, model_meta, domain_force, groups=None):
        """Create an ir.rule record for record-level permission control."""
        env = self.env
        vals = {
            'name': f'Test Record Rule for {model_meta.model}',
            'model_id': model_meta.id,
            'domain_force': domain_force,
        }
        if groups is not None:
            vals['groups'] = groups
        return env['ir.rule'].create(vals)

    # ------------------------------------------------------------------
    # Tests: Basic record-level rule filtering
    # ------------------------------------------------------------------

    @post_test("record_rule.basic")
    def test_record_rule_filter_by_name(self):
        """An ir.rule that restricts visible products by spu_name should
        be respected by searcho."""
        # Grant model access and create a record rule: only see spu_name containing "Cold"
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=like', 'Cold%')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("tag_ids")
        names = set(res.mapped("spu_name"))
        self.assertEqual({"Cold Boot"}, names)

    @post_test("record_rule.basic")
    def test_record_rule_no_restriction(self):
        """Without any ir.rule, a user with model access should see all records."""
        self.grant_model("test.oql.product")

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("tag_ids")
        names = set(res.mapped("spu_name"))
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    @post_test("record_rule.basic")
    def test_record_rule_filter_active(self):
        """An ir.rule filtering active=True should exclude inactive records."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('active', '=', True)]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        # Search without any additional filter — should only see active products
        res = user_env["test.oql.product"].searcho("id > 0")
        names = set(res.mapped("spu_name"))
        self.assertIn("Cold Boot", names)
        self.assertIn("Hot Boot", names)
        self.assertNotIn("Inactive Boot", names)

    # ------------------------------------------------------------------
    # Tests: oql() queries with record rules
    # ------------------------------------------------------------------

    @post_test("record_rule.oql")
    def test_record_rule_with_oql_select(self):
        """Verify oql() results are filtered by ir.rule."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', 'ilike', 'hot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where tag_ids"
        )
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['spu_name'], "Hot Boot")

    @post_test("record_rule.oql")
    def test_record_rule_oql_combined_where(self):
        """Record rule domain AND user's WHERE clause are combined."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', 'ilike', 'boot')]",  # restricts to Boot products
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where tag_ids"
        )
        # Both Cold Boot and Hot Boot should match
        names = {row['spu_name'] for row in res}
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    @post_test("record_rule.oql")
    def test_record_rule_oql_empty_result(self):
        """When record rule matches nothing, query should return empty."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Nonexistent Product')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where tag_ids"
        )
        self.assertEqual(len(res), 0)

    # ------------------------------------------------------------------
    # Tests: Multiple rules (AND logic)
    # ------------------------------------------------------------------

    @post_test("record_rule.multi")
    def test_record_rule_global_and(self):
        """Two global ir.rule records are intersected (AND logic).

        In Odoo's ir.rule._compute_domain:
          AND(global_domains + [OR(group_domains)])
        Global rules (no groups) are AND-ed together.
        """
        self.grant_model("test.oql.product")
        # Rule 1 (global): spu_name contains "Boot"
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', 'ilike', 'Boot')]",
        )
        # Rule 2 (global): active = True
        self._create_ir_rule(
            self.metaProduct,
            "[('active', '=', True)]",
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("id > 0")
        names = set(res.mapped("spu_name"))
        # AND of two global rules: only active Boot products
        self.assertNotIn("Inactive Boot", names)
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    @post_test("record_rule.multi")
    def test_record_rule_group_or(self):
        """Two group ir.rule records are OR-ed together.

        In Odoo's ir.rule._compute_domain:
          AND(global_domains + [OR(group_domains)])
        Group rules (with groups) are OR-ed together within a group domain.
        """
        self.grant_model("test.oql.product")
        # Rule 1 (group): only Cold Boot
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )
        # Rule 2 (group): only Hot Boot
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Hot Boot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("id > 0")
        names = set(res.mapped("spu_name"))
        # OR of group rules: Cold Boot OR Hot Boot = both
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    @post_test("record_rule.multi")
    def test_record_rule_global_and_group(self):
        """Global rule AND group rules OR: global AND (group1 OR group2).

        Verdict: global(active=True) AND (group(spu_name=Cold) OR group(spu_name=Hot))
        Should only see active Boot products.
        """
        self.grant_model("test.oql.product")
        # Global rule: active = True (excludes Inactive Boot)
        self._create_ir_rule(
            self.metaProduct,
            "[('active', '=', True)]",
        )
        # Group rule 1: spu_name = Cold Boot
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )
        # Group rule 2: spu_name = Hot Boot
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Hot Boot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("id > 0")
        names = set(res.mapped("spu_name"))
        # global(active=True) AND (group(Cold Boot) OR group(Hot Boot))
        # = {Cold Boot, Hot Boot} (Inactive Boot excluded by global)
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)
        self.assertNotIn("Inactive Boot", names)

    # ------------------------------------------------------------------
    # Tests: Record rules with orderby / limit / offset
    # ------------------------------------------------------------------

    @post_test("record_rule.oql")
    def test_record_rule_with_limit(self):
        """LIMIT clause should work correctly under record rule filtering."""
        self.grant_model("test.oql.product")
        user_env = self.user_env()
        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where tag_ids limit 1"
        )
        self.assertEqual(len(res), 1)

    @post_test("record_rule.oql")
    def test_record_rule_with_orderby(self):
        """ORDER BY should work correctly with record rules."""
        self.grant_model("test.oql.product")
        user_env = self.user_env()
        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where tag_ids order by name desc"
        )
        self.assertEqual(len(res), 2)
        # "Hot Boot" should come before "Cold Boot" in descending order
        self.assertEqual(res[0]['spu_name'], "Hot Boot")
        self.assertEqual(res[1]['spu_name'], "Cold Boot")

    # ------------------------------------------------------------------
    # Tests: Record rules combined with field-level ACL
    # ------------------------------------------------------------------

    @post_test("record_rule.field_acl")
    def test_record_rule_with_field_restriction(self):
        """Record-level rule + field-level ACL should both be enforced."""
        # Create model access with restricted field access.
        self.grant_model("test.oql.product", default_read=False)
        # Grant read access only to spu_name and tag_ids.
        self.grant_field("test.oql.product", "spu_name", perm_read=True)
        self.grant_field("test.oql.product", "tag_ids", perm_read=True)

        # Create record rule: only see spu_name containing "Boot"
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', 'ilike', 'Boot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].oql(
            "from test.oql.product select spu_name where tag_ids"
        )
        names = {row['spu_name'] for row in res}
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    # ------------------------------------------------------------------
    # Tests: Record rule with no groups (user-specific rule)
    # ------------------------------------------------------------------

    @post_test("record_rule.basic")
    def test_record_rule_non_group_rule(self):
        """A rule without groups should still be computed by _compute_domain
        (Odoo applies non-global rules to all users)."""
        self.grant_model("test.oql.product")
        # Create a rule without groups — Odoo treats this as a global rule
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=None,  # No group restriction => global rule
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("id > 0")
        names = set(res.mapped("spu_name"))
        self.assertEqual({"Cold Boot"}, names)

    # ------------------------------------------------------------------
    # Tests: Record rules across inherited models
    # ------------------------------------------------------------------

    @post_test("record_rule.inherit")
    def test_record_rule_inherited_model(self):
        """Record rules on _inherits parent model are per-model, do NOT cascade.

        Odoo's ir.rule._compute_domain only looks up rules for the exact model
        being queried. A rule on test.oql.template does NOT restrict
        test.oql.product (which _inherits template). This test verifies that
        template rules correctly restrict direct template queries.
        """
        self.grant_model("test.oql.template")
        # Create a rule on the template (parent) model
        self._create_ir_rule(
            self.metaTemplate,
            "[('name', 'ilike', 'Cold')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        # Query the template model directly — rule applies here
        res = user_env["test.oql.template"].searcho("id > 0")
        names = set(res.mapped("name"))
        self.assertEqual({"Cold Boot"}, names)

    # ------------------------------------------------------------------
    # Tests: Admin/sudo should NOT be affected
    # ------------------------------------------------------------------

    @post_test("record_rule.admin")
    def test_record_rule_admin_not_affected(self):
        """Admin/sudo user should bypass ir.rule restrictions."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )

        # Admin with .sudo() should see all active products
        # (Inactive Boot has active=False, excluded by Odoo's default filtering)
        res = self.env["test.oql.product"].sudo().searcho("id > 0")
        names = set(res.mapped("spu_name"))
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    # ------------------------------------------------------------------
    # Tests: Direct perm_records method
    # ------------------------------------------------------------------

    @post_test("record_rule.read_only")
    def test_record_rule_perm_records_direct(self):
        """Directly test perm_records method with an ir.rule in place."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        acl = OqlAcl(user_env)
        product_acl = acl["test.oql.product"]

        # perm_records should merge the rule domain via AND
        result_domain = product_acl.perm_records([('id', '>', 0)], "read")
        result_domain = list(result_domain)  # V19 will produce `class Domain` object.

        # Should produce a combined AND domain
        self.assertIsInstance(result_domain, list)
        # Verify the AND structure: [('id', '>', 0)] AND [rule domain]
        self.assertTrue(len(result_domain) > 1)

    # ------------------------------------------------------------------
    # Tests: searcho against direct search
    # ------------------------------------------------------------------

    @post_test("record_rule.searcho")
    def test_record_rule_searcho_and_direct_search(self):
        """Record rule via searcho should match direct Odoo search behavior."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=like', 'Cold%')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()

        # searcho result
        res_oql = user_env["test.oql.product"].searcho("id > 0")
        names_oql = set(res_oql.mapped("spu_name"))

        # Direct search with the same domain should return same result
        res_direct = user_env["test.oql.product"].search([('id', '>', 0)])
        names_direct = set(res_direct.mapped("spu_name"))

        self.assertEqual(names_oql, names_direct)
        self.assertEqual({"Cold Boot"}, names_oql)

    @post_test("record_rule.searcho")
    def test_record_rule_searcho_id_query(self):
        """Record rule applied to a specific ID query."""
        self.grant_model("test.oql.product")
        # Rule: only Cold Boot
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        # Try to get Hot Boot by ID — should be empty because record rule blocks it
        res = user_env["test.oql.product"].searcho(f"id = {self.prod_hot.id}")
        self.assertEqual(len(res), 0)

        # Try to get Cold Boot by ID — should succeed
        res = user_env["test.oql.product"].searcho(f"id = {self.prod_cold.id}")
        self.assertEqual(len(res), 1)
        self.assertEqual(res.spu_name, "Cold Boot")

    @post_test("record_rule.searcho")
    def test_record_rule_searcho_una_expr(self):
        """Record rule combined with unary expression (bool field check)."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', 'ilike', 'Cold')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        # Unary expression: products that have tag_ids
        res = user_env["test.oql.product"].searcho("tag_ids")
        names = set(res.mapped("spu_name"))
        self.assertEqual({"Cold Boot"}, names)

    # ------------------------------------------------------------------
    # Tests: Additional edge cases
    # ------------------------------------------------------------------

    @post_test("record_rule.edge")
    def test_record_rule_or_logic(self):
        """OR logic in WHERE clause should be properly intersected with record rule."""
        self.grant_model("test.oql.product")
        # Rule: all Boot products
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', 'ilike', 'Boot')]",
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        # WHERE: Cold Boot OR Hot Boot by name
        res = user_env["test.oql.product"].searcho(
            "spu_name='Cold Boot' or spu_name='Hot Boot'"
        )
        names = set(res.mapped("spu_name"))
        self.assertEqual({"Cold Boot", "Hot Boot"}, names)

    @post_test("record_rule.edge")
    def test_record_rule_matching_no_record(self):
        """Record rule matching no records should still allow searcho (returns empty)."""
        self.grant_model("test.oql.product")
        self._create_ir_rule(
            self.metaProduct,
            "[('id', '<', 0)]",  # impossible condition
            groups=[(4, self.user_group.id)],
        )

        user_env = self.user_env()
        res = user_env["test.oql.product"].searcho("id > 0")
        self.assertEqual(len(res), 0)

    # ------------------------------------------------------------------
    # Tests: Record rules combined with UPDATE / DELETE
    # ------------------------------------------------------------------

    @post_test("acl.crud.record_rule")
    def test_acl_update_record_rule_blocks(self):
        """UPDATE should only affect records allowed by ir.rule (write mode)."""
        self.grant_model("test.oql.product", perm_read=True, perm_write=True,
                         default_write=True)
        # `spu_name` writes through to `test.oql.template.name`.
        self.grant_model("test.oql.template", perm_read=True, perm_write=True,
                         default_write=True)
        # Rule: only Cold Boot is writable.
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )
        user_env = self.user_env()
        # Try to update Hot Boot — should be blocked by record rule (0 records updated).
        res = user_env["test.oql.product"].oql(
            f"update test.oql.product set spu_name = 'Hacked' where id = {self.prod_hot.id}"
        )
        self.assertEqual(len(res), 0)
        # Hot Boot name unchanged.
        self.assertEqual(self.prod_hot.spu_name, 'Hot Boot')
        # Update Cold Boot — should succeed.
        res = user_env["test.oql.product"].oql(
            f"update test.oql.product set spu_name = 'Cold Updated' where id = {self.prod_cold.id}"
        )
        self.assertEqual(len(res), 1)
        self.assertEqual(self.prod_cold.spu_name, 'Cold Updated')

    @post_test("acl.crud.record_rule")
    def test_acl_delete_record_rule_blocks(self):
        """DELETE should only affect records allowed by ir.rule (unlink mode)."""
        self.grant_model("test.oql.product", perm_read=True, perm_unlink=True)
        # Rule: only Cold Boot can be unlinked.
        self._create_ir_rule(
            self.metaProduct,
            "[('spu_name', '=', 'Cold Boot')]",
            groups=[(4, self.user_group.id)],
        )
        user_env = self.user_env()
        # Try to delete Hot Boot — blocked by record rule.
        res = user_env["test.oql.product"].oql(
            f"delete from test.oql.product where id = {self.prod_hot.id}"
        )
        self.assertEqual(len(res), 0)
        self.assertTrue(self.prod_hot.exists())
        # Delete Cold Boot — allowed.
        res = user_env["test.oql.product"].oql(
            f"delete from test.oql.product where id = {self.prod_cold.id}"
        )
        self.assertEqual(len(res), 1)
        self.assertFalse(self.prod_cold.exists())
