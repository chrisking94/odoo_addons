# @Time         : 09:30 2026/9/4
# @Author       : Chris
# @Description  : Test OQL field ACL (oql.acl.field) and view visibility (ir.ui.view patch).
#
# These tests exercise the three-layer field access control described in
# `oql.models.oql_acl_field.OqlAclField`, plus the view-visibility patch in
# `oql.models.ir_ui_view` that aligns `<field>` node visibility with the same
# read verdict.
#
# Field matrix on `test.oql.fac` (see `TestOqlFac` in `test_model_defs.py`):
#   * name / active / root_id     -- no groups: layer 3 (oql default) decides.
#   * internal                    -- groups=base.group_user: layer 2 allows a
#                                     plain internal user, whatever the default.
#   * topsecret                   -- groups=base.group_system: layer 2 denies a
#                                     plain internal user; the oql default must
#                                     not grant past it, only layer 1 can.
#   * root_topsecret              -- related to root_id.topsecret (groups=system):
#                                     inherits the restriction; layer 1 can break it.
#   * root_name                   -- related to root_id.name (no groups): layer 3.
#
# The tail of this file (`TestOqlAclField`) also hosts the product-based
# field/path ACL API cases (`check_field` / `perm_fields` / `perm_paths`,
# temporary `oql.acl.field` records, inherited fields) that were split out of
# the former `test_acl.py`; they share the `test.oql.product` fixture in
# `test_acl_common.py`.
from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests import tagged, TransactionCase

from .test_model_defs import ensure_model_meta, ensure_model_access, post_test
from .test_acl_common import OqlAclProductCase
from ..acl import OqlAcl
from ..compatible import res_users_data


@tagged("oql_fac", "-at_install", "post_install")
class TestOqlFacFieldAcl(TransactionCase):
    """Field-level ACL for `test.oql.fac` across the three layers.

    Layer precedence (highest first):
      1. oql.acl.field override row (relax OR tighten).
      2. native field.groups attribute.
      3. ir.model.access perm_oql_fac_default_{read,write}.
    """

    def setUp(self):
        super().setUp()
        env = self.env
        ensure_model_meta(env)
        # Admin-only access so fixtures can be created; the test user's access
        # is granted per test below.
        ensure_model_access(env)

        self.metaFac = env["ir.model"].search([("model", "=", "test.oql.fac")], limit=1)
        self.metaRoot = env["ir.model"].search([("model", "=", "test.oql.fac.root")], limit=1)

        self.root = env["test.oql.fac.root"].create({"name": "Root", "topsecret": "R-X"})
        self.fac = env["test.oql.fac"].create({
            "name": "Fac",
            "root_id": self.root.id,
            "internal": "I",
            "topsecret": "T",
            "root_name": "Root",
            "root_topsecret": "R-X",
        })

        self.test_user = env['res.users'].create(res_users_data({
            'name': 'FAC Test User',
            'login': 'fac_test_user',
            'email': 'fac@example.com',
            'groups_id': [(6, 0, [env.ref('base.group_user').id])],  # Internal User only
        }))
        self.user_group = env.ref('base.group_user')

    # ---- helpers ----------------------------------------------------------

    def _grant_fac(self, model_name, perm_read=True, perm_write=False,
                   default_read=True, default_write=False, group=None):
        """Create an ir.model.access row for the test user's group on `model_name`."""
        env = self.env
        meta = env["ir.model"].search([("model", "=", model_name)], limit=1)
        return env["ir.model.access"].create({
            'name': f'FAC Test Access {model_name}',
            'model_id': meta.id,
            'group_id': (group or self.user_group).id,
            'perm_read': perm_read,
            'perm_write': perm_write,
            'perm_create': False,
            'perm_unlink': False,
            'perm_oql_fac_default_read': default_read,
            'perm_oql_fac_default_write': default_write,
        })

    def _grant_field(self, model_name, field_name, perm_read=None, perm_write=None):
        """Create an oql.acl.field override row for `field_name` of `model_name`."""
        env = self.env
        meta = env["ir.model"].search([("model", "=", model_name)], limit=1)
        access = env["ir.model.access"].search([
            ('model_id', '=', meta.id), ('group_id', '=', self.user_group.id)
        ], limit=1)
        field = env["ir.model.fields"].search([
            ('model_id', '=', meta.id), ('name', '=', field_name)
        ], limit=1)
        vals = {'mac_id': access.id, 'field_id': field.id}
        if perm_read is not None:
            vals['perm_read'] = perm_read
        if perm_write is not None:
            vals['perm_write'] = perm_write
        return env["oql.acl.field"].create(vals)

    def _readable(self):
        user_env = self.env(user=self.test_user)
        acl = OqlAcl(user_env)
        return acl["test.oql.fac"].perm_fields("read")

    def _writable(self):
        user_env = self.env(user=self.test_user)
        acl = OqlAcl(user_env)
        return acl["test.oql.fac"].perm_fields("write")

    # ---- layer 3: oql default --------------------------------------------

    @post_test("fac.layer3")
    def test_layer3_default_read_true(self):
        """default_read=True grants the unrestricted fields (layer 3)."""
        self._grant_fac("test.oql.fac", default_read=True)
        readable = self._readable()
        # No-groups fields -> layer 3 -> granted by default True.
        for f in ["id", "name", "active", "root_id", "root_name"]:
            self.assertIn(f, readable, f"{f} should be readable with default_read=True")
        # groups=group_user -> layer 2 allows.
        self.assertIn("internal", readable)
        # groups=group_system -> layer 2 is a ceiling, the default must not grant past it.
        self.assertNotIn("topsecret", readable)
        self.assertNotIn("root_topsecret", readable)

    @post_test("fac.layer3")
    def test_layer3_default_read_false(self):
        """default_read=False denies the unrestricted fields (layer 3)."""
        self._grant_fac("test.oql.fac", default_read=False)
        readable = self._readable()
        # Layer-2 granted: `internal` (groups=group_user), plus `id` (always readable).
        self.assertIn("id", readable)
        self.assertIn("internal", readable)
        # No-groups fields -> layer 3 -> denied by default False.
        for f in ["name", "active", "root_id", "root_name"]:
            self.assertNotIn(f, readable, f"{f} should be denied with default_read=False")
        # groups=group_system -> denied by layer 2 as well.
        self.assertNotIn("topsecret", readable)
        self.assertNotIn("root_topsecret", readable)

    @post_test("fac.layer3")
    def test_layer3_write_default_false(self):
        """Write default behaves the same way, and `id` is read-only by default."""
        self._grant_fac("test.oql.fac", perm_write=True, default_write=False)
        writable = self._writable()
        # Layer-2 granted (groups=group_user).
        self.assertIn("internal", writable)
        for f in ["name", "active", "root_id", "root_name"]:
            self.assertNotIn(f, writable)
        self.assertNotIn("topsecret", writable)
        self.assertNotIn("root_topsecret", writable)
        # `id` is force-granted for the read mode only.
        self.assertNotIn("id", writable)

    # ---- layer 2: native field.groups ------------------------------------

    @post_test("fac.layer2")
    def test_layer2_groups_ceiling(self):
        """field.groups is a hard ceiling: it allows `internal` and denies
        `topsecret` for a plain internal user, whatever the oql default is."""
        # Even default_read=True must not grant past a groups restriction.
        self._grant_fac("test.oql.fac", default_read=True)
        readable = self._readable()
        self.assertIn("internal", readable)
        self.assertNotIn("topsecret", readable)
        self.assertNotIn("root_topsecret", readable)

    # ---- layer 1: oql.acl.field override (relax) ------------------------

    @post_test("fac.layer1")
    def test_layer1_relax_topsecret(self):
        """An explicit allow row relaxes a group_system field (layer 1)."""
        self._grant_fac("test.oql.fac", default_read=False)
        self._grant_field("test.oql.fac", "topsecret", perm_read=True)
        readable = self._readable()
        self.assertIn("topsecret", readable)
        # root_topsecret still denied (no override).
        self.assertNotIn("root_topsecret", readable)

    @post_test("fac.layer1")
    def test_layer1_relax_related(self):
        """An explicit allow row breaks related-field restriction inheritance."""
        self._grant_fac("test.oql.fac", default_read=False)
        self._grant_field("test.oql.fac", "root_topsecret", perm_read=True)
        readable = self._readable()
        self.assertIn("root_topsecret", readable)

    # ---- layer 1: oql.acl.field override (tighten) -----------------------

    @post_test("fac.layer1")
    def test_layer1_tighten_name(self):
        """An explicit deny row tightens an unrestricted field below layer 3."""
        self._grant_fac("test.oql.fac", default_read=True)
        self._grant_field("test.oql.fac", "name", perm_read=False)
        readable = self._readable()
        self.assertNotIn("name", readable)
        # Other unrestricted fields unaffected.
        self.assertIn("active", readable)
        self.assertIn("root_name", readable)
        self.assertIn("internal", readable)

    @post_test("fac.layer1")
    def test_layer1_sticky_denial(self):
        """Once an explicit row exists, a field whose rows are all False stays denied
        even though another group path would default to True (tightening is sticky)."""
        env = self.env
        # Two groups: internal user (group_user) and a brand-new group.
        extra_group = env['res.groups'].create({
            'name': 'FAC Extra', 'category_id': env.ref('base.module_category_hidden').id})
        self.test_user.write({'groups_id': [(4, extra_group.id)]})

        # group_user path: default deny, with an explicit DENY row on topsecret.
        self._grant_fac("test.oql.fac", default_read=False)
        self._grant_field("test.oql.fac", "topsecret", perm_read=False)
        # extra group path: default allow, no override row.
        self._grant_fac("test.oql.fac", default_read=True, group=extra_group)

        readable = self._readable()
        # The explicit deny from group_user wins -> still denied.
        self.assertNotIn("topsecret", readable)

    # ---- enforcement via check_field -------------------------------------

    @post_test("fac.enforce")
    def test_check_field_denies_topsecret(self):
        """OqlAcl.check_field raises AccessError for a denied field."""
        self._grant_fac("test.oql.fac", default_read=False)
        user_env = self.env(user=self.test_user)
        acl = OqlAcl(user_env)
        recs = user_env["test.oql.fac"].browse([self.fac.id])
        # Allowed: `internal` is granted by layer 2 (groups=base.group_user).
        acl.check_field(recs, "internal", "read")
        # Denied by layer 3: no groups, but the oql default is False.
        with self.assertRaises(AccessError):
            acl.check_field(recs, "name", "read")
        # Denied by layer 2: groups=base.group_system.
        with self.assertRaises(AccessError):
            acl.check_field(recs, "topsecret", "read")


@tagged("oql_fac_view", "-at_install", "post_install")
class TestOqlFacViewVisibility(TransactionCase):
    """View `<field>` node visibility aligned with oql.acl.field read verdict.

    The patch in `oql.models.ir_ui_view` swaps the field's `groups` for ''
    (allowed, the native postprocessor keeps the node) or '.' (denied, a group
    nobody has, so `user_has_groups('.')` is False and the native postprocessor
    removes the node from the arch).

    The view is fetched through the model's view API as the test user -- the
    production path (`get_view` on Odoo 16+, `fields_view_get` on Odoo 15).
    NOTE: it must be called on the MODEL, not on the view recordset; on Odoo 15
    `fields_view_get` checks read access on `self`, and a plain internal user
    has no read access on `ir.ui.view` (granted to `group_system` only), while
    the view itself is browsed with `sudo()` internally.
    """

    def setUp(self):
        super().setUp()
        env = self.env
        ensure_model_meta(env)
        ensure_model_access(env)

        self.test_user = env['res.users'].create(res_users_data({
            'name': 'FAC View User',
            'login': 'fac_view_user',
            'email': 'facview@example.com',
            'groups_id': [(6, 0, [env.ref('base.group_user').id])],
        }))
        self.user_group = env.ref('base.group_user')

        self.view = env['ir.ui.view'].create({
            'name': 'test oql fac form',
            'model': 'test.oql.fac',
            'type': 'form',
            'arch': '''<form>
                <field name="name"/>
                <field name="active"/>
                <field name="root_id"/>
                <field name="internal"/>
                <field name="topsecret"/>
                <field name="root_name"/>
                <field name="root_topsecret"/>
            </form>''',
        })

    # ---- helpers ----------------------------------------------------------

    def _postprocessed_arch(self, user):
        """Return the postprocessed arch (lxml Element) for `self.view` as `user`."""
        model = self.env(user=user)["test.oql.fac"]
        if hasattr(model, "get_view"):  # Odoo 16+
            res = model.get_view(self.view.id, "form")
        else:  # Odoo 15
            res = model.fields_view_get(view_id=self.view.id, view_type="form")
        arch = res.get("arch")
        if isinstance(arch, str):
            return etree.fromstring(arch)
        return arch

    def _field_names(self, user):
        """Names of `<field>` nodes that survived postprocessing as `user`."""
        arch = self._postprocessed_arch(user)
        return {f.get('name') for f in arch.iter('field')}

    def _grant_fac(self, default_read=True):
        env = self.env
        meta = env["ir.model"].search([("model", "=", "test.oql.fac")], limit=1)
        return env["ir.model.access"].create({
            'name': 'FAC View Access',
            'model_id': meta.id,
            'group_id': self.user_group.id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
            'perm_oql_fac_default_read': default_read,
            'perm_oql_fac_default_write': False,
        })

    # ---- tests ------------------------------------------------------------

    @post_test("fac.view.default_true")
    def test_view_default_read_true(self):
        """default_read=True: unrestricted fields stay visible, while
        group_system fields stay hidden (field.groups is a hard ceiling)."""
        self._grant_fac(default_read=True)
        names = self._field_names(self.test_user)
        for f in ["name", "active", "root_id", "root_name", "internal"]:
            self.assertIn(f, names, f"{f} should be visible with default_read=True")
        self.assertNotIn("topsecret", names)
        self.assertNotIn("root_topsecret", names)

    @post_test("fac.view.default_false")
    def test_view_default_read_false(self):
        """default_read=False: unrestricted fields are removed too; only the
        layer-2 granted `internal` survives postprocessing."""
        self._grant_fac(default_read=False)
        names = self._field_names(self.test_user)
        self.assertIn("internal", names)
        for f in ["name", "active", "root_id", "root_name", "topsecret", "root_topsecret"]:
            self.assertNotIn(f, names, f"{f} should be hidden with default_read=False")

    @post_test("fac.view.override")
    def test_view_override_relaxes(self):
        """An oql.acl.field allow row restores visibility of a denied field."""
        access = self._grant_fac(default_read=False)
        meta = self.env["ir.model"].search([("model", "=", "test.oql.fac")], limit=1)
        field = self.env["ir.model.fields"].search([
            ('model_id', '=', meta.id), ('name', '=', 'topsecret')], limit=1)
        self.env["oql.acl.field"].create({
            'mac_id': access.id, 'field_id': field.id, 'perm_read': True})

        names = self._field_names(self.test_user)
        # topsecret now visible; the others stay hidden.
        self.assertIn("topsecret", names)
        self.assertNotIn("root_topsecret", names)
        self.assertNotIn("name", names)


@tagged("oql_acl", "-at_install", 'post_install')
class TestOqlAclField(OqlAclProductCase):
    """Product-based field / path ACL API tests.

    These were split out of the original `TestOqlAcl` and live here because
    they exercise the same field-level API (`check_field` / `perm_fields` /
    `perm_paths`, temporary `oql.acl.field` creation & cleanup, inherited
    fields) as the `test.oql.fac` matrix above, only on `test.oql.product`.
    """

    # ---- superuser field access ----------------------------------------

    @post_test("acl.field")
    def test_acl_field_check_read(self):
        """Test field-level read access check."""
        # In superuser mode, all fields should be accessible
        product_acl = self.acl()["test.oql.product"]

        # Check individual field ACL
        name_acl = product_acl["name"]
        self.assertTrue(name_acl.check("read"))
        self.assertTrue(name_acl.perm_read)

        active_acl = product_acl["active"]
        self.assertTrue(active_acl.check("read"))

    @post_test("acl.field")
    def test_acl_field_check_write(self):
        """Test field-level write access check."""
        product_acl = self.acl()["test.oql.product"]

        # In superuser mode, all fields should be writable
        name_acl = product_acl["name"]
        self.assertTrue(name_acl.check("write"))
        self.assertTrue(name_acl.perm_write)

    @post_test("acl.fields")
    def test_acl_perm_fields(self):
        """Test getting permitted fields for a model."""
        product_acl = self.acl()["test.oql.product"]

        # Get all readable fields
        readable_fields = product_acl.perm_fields("read")
        self.assertIsInstance(readable_fields, set)
        self.assertIn("name", readable_fields)
        self.assertIn("id", readable_fields)  # ID is always readable

        # Get all writable fields
        writable_fields = product_acl.perm_fields("write")
        self.assertIsInstance(writable_fields, set)
        self.assertIn("name", writable_fields)

    # ---- perm_paths with a restricted user -----------------------------

    @post_test("acl.path_permission")
    def test_acl_perm_paths_with_user(self):
        """Test path permission checking with a regular user."""
        # Grant read on the product (default field deny), then explicitly allow
        # `name` and `tag_ids`; `active` stays denied.
        self.grant_model("test.oql.product", default_read=False)
        self.grant_field("test.oql.product", "name", perm_read=True)
        self.grant_field("test.oql.product", "tag_ids", perm_read=True)

        # Also grant read access to the tag model with its default field read.
        self.grant_model("test.oql.tag", default_read=True)

        # Switch to test user
        user_env = self.user_env()
        acl = self.acl(user_env)

        # Test paths
        paths = [
            "name",  # Should be allowed
            "active",  # Should NOT be allowed (not granted)
            "tag_ids.name",  # Should be allowed (both levels granted)
        ]

        allowed_paths = acl.perm_paths("test.oql.product", paths, "read")

        self.assertIn("name", allowed_paths)
        self.assertNotIn("active", allowed_paths)
        self.assertIn("tag_ids.name", allowed_paths)

    @post_test("acl.check_field")
    def test_acl_check_field_with_user(self):
        """Test field access check with a regular user."""
        # Create access record, default field read denied.
        self.grant_model("test.oql.product", default_read=False)
        # Grant read access to 'name' field only
        self.grant_field("test.oql.product", "name", perm_read=True)

        # Switch to test user
        user_env = self.user_env()
        acl = self.acl(user_env)

        # Should not raise for accessible field
        recs = user_env["test.oql.product"].browse([self.prod_cold.id])
        acl.check_field(recs, "name", "read")

        # Should raise AccessError for non-accessible field
        with self.assertRaises(AccessError):
            acl.check_field(recs, "active", "read")

    # ---- relational / multi-model field access -------------------------

    @post_test("acl.multi_model")
    def test_acl_multiple_models_with_user(self):
        """Test ACL across multiple models with a regular user."""
        # Create access for product, attribute and tag models (default field read).
        self.grant_model("test.oql.product", default_read=True)
        self.grant_model("test.oql.attribute", default_read=True)
        self.grant_model("test.oql.tag", default_read=True)

        # Switch to test user
        user_env = self.user_env()
        acl = self.acl(user_env)

        # Test different models
        product_acl = acl["test.oql.product"]
        attribute_acl = acl["test.oql.attribute"]
        tag_acl = acl["test.oql.tag"]

        # All should have read access to name field
        self.assertIn("name", product_acl.perm_fields("read"))
        self.assertIn("name", attribute_acl.perm_fields("read"))
        self.assertIn("name", tag_acl.perm_fields("read"))

    @post_test("acl.relational")
    def test_acl_relational_fields_with_user(self):
        """Test ACL for relational fields with a regular user."""
        # Create access with default deny
        self.grant_model("test.oql.product", default_read=False)
        # Grant access only to tag_ids, not attribute_value_ids
        self.grant_field("test.oql.product", "tag_ids", perm_read=True)

        # Switch to test user
        user_env = self.user_env()
        acl = self.acl(user_env)
        product_acl = acl["test.oql.product"]

        readable_fields = product_acl.perm_fields("read")

        # Should have access to tag_ids (granted)
        self.assertIn("tag_ids", readable_fields)

        # Should NOT have access to attribute_value_ids (not granted)
        self.assertNotIn("attribute_value_ids", readable_fields)

    # ---- restricted field defaults -------------------------------------

    @post_test("acl.field_restriction")
    def test_acl_field_level_restriction(self):
        """Test field-level ACL restrictions with a regular user."""
        # Create access with default deny for read
        self.grant_model("test.oql.product", perm_read=True, perm_write=False,
                         default_read=False, default_write=False)
        # Grant explicit read access only to 'name' field
        self.grant_field("test.oql.product", "name", perm_read=True, perm_write=False)

        # Switch to test user
        user_env = self.user_env()
        acl = self.acl(user_env)
        product_acl = acl["test.oql.product"]

        # Check field permissions
        readable_fields = product_acl.perm_fields("read")

        # Should have access to 'name' (explicitly granted)
        self.assertIn("name", readable_fields)

        # Should NOT have access to 'active' (not granted and default is False)
        self.assertNotIn("active", readable_fields)

        # ID should always be readable
        self.assertIn("id", readable_fields)

    @post_test("acl.temp_with_check")
    def test_acl_with_temp_records_user_context(self):
        """Test ACL checking with temporary access records in user context."""
        # Create temporary model access with restrictive defaults
        self.grant_model("test.oql.product", perm_read=True, perm_write=False,
                         default_read=False, default_write=False)
        # Grant explicit read access only to 'name' field
        self.grant_field("test.oql.product", "name", perm_read=True, perm_write=False)

        # Switch to test user and verify ACL
        user_env = self.user_env()
        acl = self.acl(user_env)
        product_acl = acl["test.oql.product"]

        # Verify field permissions for the user
        readable_fields = product_acl.perm_fields("read")
        writable_fields = product_acl.perm_fields("write")

        # Should have read access to 'name' (explicitly granted)
        self.assertIn("name", readable_fields)

        # Should NOT have read access to 'active' (not granted)
        self.assertNotIn("active", readable_fields)

        # Should NOT have write access to any field
        self.assertNotIn("name", writable_fields)
        self.assertNotIn("active", writable_fields)

    @post_test("acl.multiple_temp_records")
    def test_multiple_temp_acl_fields_user_context(self):
        """Test creating multiple temporary ACL field records with user context."""
        # Create model access with default deny
        self.grant_model("test.oql.product", perm_read=True, perm_write=False,
                         default_read=False, default_write=False)
        # Grant read access to 'name' and 'active' fields
        self.grant_field("test.oql.product", "name", perm_read=True, perm_write=False)
        self.grant_field("test.oql.product", "active", perm_read=True, perm_write=False)

        # Switch to test user and verify permissions
        user_env = self.user_env()
        acl = self.acl(user_env)
        product_acl = acl["test.oql.product"]

        readable_fields = product_acl.perm_fields("read")
        writable_fields = product_acl.perm_fields("write")

        # Should have read access to granted fields
        self.assertIn("name", readable_fields)
        self.assertIn("active", readable_fields)

        # Should NOT have write access
        self.assertNotIn("name", writable_fields)
        self.assertNotIn("active", writable_fields)

        # Should NOT have access to non-granted relational fields
        self.assertNotIn("attribute_value_ids", readable_fields)
        self.assertNotIn("tag_ids", readable_fields)

    # ---- temporary oql.acl.field records (admin) -----------------------

    @post_test("acl.temp_acl_field")
    def test_create_temp_acl_field(self):
        """Test creating temporary oql.acl.field records."""
        env = self.env

        # First create a model access record
        temp_access = env["ir.model.access"].create({
            'name': 'Test Access for ACL Field',
            'model_id': self.metaProduct.id,
            'perm_read': True,
            'perm_write': True,
            'perm_oql_fac_default_read': False,  # Default to false
            'perm_oql_fac_default_write': False,
        })

        # Get field metadata
        name_field = self.field("test.oql.product", "name")
        active_field = self.field("test.oql.product", "active")

        self.assertTrue(name_field.exists())
        self.assertTrue(active_field.exists())

        # Create ACL field records
        acl_name = env["oql.acl.field"].create({
            'mac_id': temp_access.id,
            'field_id': name_field.id,
            'perm_read': True,
            'perm_write': True,
        })

        acl_active = env["oql.acl.field"].create({
            'mac_id': temp_access.id,
            'field_id': active_field.id,
            'perm_read': True,
            'perm_write': False,
        })

        # Verify creation
        self.assertTrue(acl_name.exists())
        self.assertTrue(acl_active.exists())
        self.assertEqual(acl_name.mac_id, temp_access)
        self.assertEqual(acl_name.field_id, name_field)
        self.assertTrue(acl_name.perm_read)
        self.assertTrue(acl_name.perm_write)
        self.assertTrue(acl_active.perm_read)
        self.assertFalse(acl_active.perm_write)

    @post_test("acl.cleanup")
    def test_temp_records_cleanup(self):
        """Test that temporary records can be properly cleaned up."""
        env = self.env

        # Create temporary records
        temp_access = env["ir.model.access"].create({
            'name': 'Cleanup Test Access',
            'model_id': self.metaProduct.id,
            'perm_read': True,
            'perm_write': True,
        })

        name_field = self.field("test.oql.product", "name")
        acl_field = env["oql.acl.field"].create({
            'mac_id': temp_access.id,
            'field_id': name_field.id,
            'perm_read': True,
            'perm_write': True,
        })

        # Verify records exist
        self.assertTrue(temp_access.exists())
        self.assertTrue(acl_field.exists())

        # Delete the access record (should cascade delete ACL fields)
        temp_access.unlink()

        # Verify both are deleted
        self.assertFalse(temp_access.exists())
        self.assertFalse(acl_field.exists())

    # ---- inherited (delegated) fields ----------------------------------

    @post_test("acl.inheritance")
    def test_acl_inherited_model_permissions(self):
        """Test that permissions on parent model fields are inherited by child model."""
        # Create access for template model with default deny
        self.grant_model("test.oql.template", perm_read=True, perm_write=False,
                         default_read=False, default_write=False)
        # Grant read access to tag_ids field in template model
        self.grant_field("test.oql.template", "tag_ids", perm_read=True, perm_write=False)

        # Switch to test user
        user_env = self.user_env()
        acl = self.acl(user_env)

        # Check that product model (which inherits template) has access to tag_ids
        product_acl = acl["test.oql.product"]
        readable_fields = product_acl.perm_fields("read")

        # tag_ids should be readable in product model due to inheritance
        self.assertIn("tag_ids", readable_fields,
                      "tag_ids field should be readable in product model through inheritance")

        # Also verify we can check the field without raising an error
        recs = user_env["test.oql.product"].browse([self.prod_cold.id])
        acl.check_field(recs, "tag_ids", "read")

    # ---- end-to-end ----------------------------------------------------

    @post_test("acl.comprehensive")
    def test_acl_complete_workflow(self):
        """Test complete ACL workflow with paths and fields."""
        acl = self.acl()

        # 1. Check model ACL exists
        product_acl = acl["test.oql.product"]
        self.assertIsNotNone(product_acl)

        # 2. Check field permissions
        readable = product_acl.perm_fields("read")
        self.assertIn("name", readable)
        self.assertIn("id", readable)

        # 3. Check path permissions
        paths = ["name", "attribute_value_ids.name", "tag_ids.name"]
        allowed = acl.perm_paths("test.oql.product", paths, "read")
        self.assertEqual(len(allowed), len(paths))

        # 4. Verify field check doesn't raise
        recs = self.env["test.oql.product"].browse([self.prod_cold.id])
        acl.check_field(recs, "name", "read")
