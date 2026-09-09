# @Description  : Shared fixtures & helpers for the split product-model ACL tests.
#
# The ACL test files split out of `test_acl.py` (model / term / records / the
# product-based field cases inside `test_acl_field.py`) all exercise
# `test.oql.product` and its attribute/tag neighbors with a restricted user.
# Subclassing `OqlAclProductCase` gives:
#   * `ensure_model_meta` / `ensure_model_access` (admin-only, so fixtures and
#     ACL configuration never leak permissions to the restricted user);
#   * model meta lookups for product / template / attribute / attribute.value /
#     tag (also kept as `self.meta*`);
#   * a small catalog:
#       - products: `prod_cold`, `prod_hot` (active) and `prod_inactive`;
#       - Size (5/6/7) and Width (D/EE) attribute values on the active products;
#       - `tag_waterproof` + `tag_cold` on the cold template, `tag_hot` on the
#         hot template;
#   * a `test_user` holding only `base.group_user`;
#   * ACL-configuration helpers (`grant_model` / `grant_field`) that write on
#     the admin env `self.env` (kept as the TransactionCase superuser env).
#
# NOTE: like `test_model_defs.py`, this module is intentionally NOT imported
# from `tests/__init__.py` -- it only provides building blocks for the test
# modules that are listed there.
from odoo.tests import TransactionCase

from .test_model_defs import ensure_model_meta, ensure_model_access
from ..acl import OqlAcl
from ..compatible import res_users_data


class OqlAclProductCase(TransactionCase):
    """Shared `test.oql.product` fixture + restricted-user harness.

    `self.env` is the admin (superuser) env handed over by TransactionCase and
    is used for fixtures and ACL configuration; run queries as the restricted
    user through `self.user_env()`.
    """

    def setUp(self):
        super().setUp()
        env = self.env
        # 1. Load model meta (admin-only access for fixtures).
        ensure_model_meta(env)
        ensure_model_access(env)

        # 2. Model meta lookups.
        self.metaProduct = self.meta("test.oql.product")
        self.metaTemplate = self.meta("test.oql.template")
        self.metaAttribute = self.meta("test.oql.attribute")
        self.metaAttributeValue = self.meta("test.oql.attribute.value")
        self.metaTag = self.meta("test.oql.tag")

        # 3. Create test records (as admin for setup).
        self.prod_cold = env["test.oql.product"].create({"spu_name": "Cold Boot"})
        self.prod_hot = env["test.oql.product"].create({"spu_name": "Hot Boot"})
        self.prod_inactive = env["test.oql.product"].create(
            {"spu_name": "Inactive Boot", "active": False})

        self.attr_size = env["test.oql.attribute"].create({"name": "Size"})
        self.attr_width = env["test.oql.attribute"].create({"name": "Width"})
        for prod in (self.prod_cold, self.prod_hot):
            for attr, values in ((self.attr_size, ["5", "6", "7"]),
                                 (self.attr_width, ["D", "EE"])):
                for value in values:
                    env["test.oql.attribute.value"].create({
                        "name": value,
                        "product_id": prod.id,
                        "attribute_id": attr.id,
                    })

        self.tag_waterproof = env["test.oql.tag"].create(
            {"name": "Waterproof:GTX", "tmpl_id": self.prod_cold.tmpl_id.id})
        self.tag_cold = env["test.oql.tag"].create(
            {"name": "Weather:Cold", "tmpl_id": self.prod_cold.tmpl_id.id})
        self.tag_hot = env["test.oql.tag"].create(
            {"name": "Weather:Hot", "tmpl_id": self.prod_hot.tmpl_id.id})

        # 4. Create a test user with Internal User group only.
        self.user_group = env.ref('base.group_user')
        self.test_user = env['res.users'].create(res_users_data({
            'name': 'OQL ACL Test User',
            'login': 'oql_acl_test_user',
            'email': 'oql_acl@example.com',
            'groups_id': [(6, 0, [self.user_group.id])],
        }))

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def meta(self, model_name):
        """`ir.model` row describing `model_name`."""
        return self.env["ir.model"].search([("model", "=", model_name)], limit=1)

    def field(self, model_name, field_name):
        """`ir.model.fields` row for `field_name` of `model_name`."""
        return self.env["ir.model.fields"].search([
            ('model_id', '=', self.meta(model_name).id),
            ('name', '=', field_name),
        ], limit=1)

    # ------------------------------------------------------------------
    # Env / ACL helpers
    # ------------------------------------------------------------------

    def user_env(self, user=None):
        """Env bound to the restricted user (out of superuser mode)."""
        return self.env(user=user or self.test_user)

    def acl(self, env=None):
        """`OqlAcl` bound to `env` (defaults to the admin env `self.env`)."""
        return OqlAcl(env if env is not None else self.env)

    # ------------------------------------------------------------------
    # ACL configuration (admin operations)
    # ------------------------------------------------------------------

    def grant_model(self, model_name, perm_read=True, perm_write=False,
                    perm_create=False, perm_unlink=False,
                    default_read=True, default_write=False, group=None):
        """Create an `ir.model.access` row for the test user's group on
        `model_name`. Field-level ACL of the model is defaulted with
        `default_read` / `default_write`."""
        meta = self.meta(model_name)
        return self.env["ir.model.access"].create({
            'name': f'Test Access {model_name}',
            'model_id': meta.id,
            'group_id': (group or self.user_group).id,
            'perm_read': perm_read,
            'perm_write': perm_write,
            'perm_create': perm_create,
            'perm_unlink': perm_unlink,
            'perm_oql_fac_default_read': default_read,
            'perm_oql_fac_default_write': default_write,
        })

    def grant_field(self, model_name, field_name, perm_read=None, perm_write=None):
        """Create an `oql.acl.field` override row for `field_name` of
        `model_name`, bound to the test user's `ir.model.access` row.

        Only the permissions given are written; the others keep their default
        (False), because an explicit row governs the field on its own.
        """
        mac = self.env["ir.model.access"].search([
            ('model_id', '=', self.meta(model_name).id),
            ('group_id', '=', self.user_group.id),
        ], limit=1)
        f_meta = self.field(model_name, field_name)
        vals = {'mac_id': mac.id, 'field_id': f_meta.id}
        if perm_read is not None:
            vals['perm_read'] = perm_read
        if perm_write is not None:
            vals['perm_write'] = perm_write
        return self.env["oql.acl.field"].create(vals)
