from funcy import project

from redash import models
from redash.models import DataSource, Group, db
from tests import BaseTestCase


class TestGroupMemberResources(BaseTestCase):
    def test_add_member(self):
        group = self.factory.create_group()
        user = self.factory.create_user()
        admin = self.factory.create_admin()
        
        rv = self.make_request(
            "post", 
            "/api/groups/{}/members".format(group.id),
            data={"user_id": user.id},
            user=admin
        )
        self.assertEqual(rv.status_code, 200)
        self.assertIn(group.id, user.group_ids)

    def test_list_members(self):
        group = self.factory.create_group()
        user = self.factory.create_user()
        user.group_ids.append(group.id)
        db.session.commit()
        
        admin = self.factory.create_admin()

        rv = self.make_request(
            "get", 
            "/api/groups/{}/members".format(group.id), 
            user=admin
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(len(rv.json), 1)
        self.assertEqual(rv.json[0]["id"], user.id)

    def test_remove_member(self):
        group = self.factory.create_group()
        user = self.factory.create_user()
        user.group_ids.append(group.id)
        db.session.commit()
        
        admin = self.factory.create_admin()

        rv = self.make_request(
            "delete",
            "/api/groups/{}/members/{}".format(group.id, user.id),
            user=admin
        )
        self.assertEqual(rv.status_code, 200)
        
        # reload user
        # user = models.User.get_by_id(user.id) # get_by_id might be cached or session bound?
        # db.session.expire_all()
        user = models.User.query.get(user.id)
        self.assertNotIn(group.id, user.group_ids)


class TestGroupDataSourceResources(BaseTestCase):
    def test_add_data_source(self):
        group = self.factory.create_group()
        ds = self.factory.create_data_source()
        admin = self.factory.create_admin()

        rv = self.make_request(
            "post",
            "/api/groups/{}/data_sources".format(group.id),
            data={"data_source_id": ds.id},
            user=admin
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["id"], ds.id)
        
        # Verify persistence
        ds_group = models.DataSourceGroup.query.filter_by(group_id=group.id, data_source_id=ds.id).first()
        self.assertIsNotNone(ds_group)

class TestGroupDataSourceListResource(BaseTestCase):
    def test_returns_only_groups_for_current_org(self):
        group = self.factory.create_group(org=self.factory.create_org())
        self.factory.create_data_source(group=group)
        db.session.flush()
        response = self.make_request(
            "get",
            "/api/groups/{}/data_sources".format(group.id),
            user=self.factory.create_admin(),
        )
        self.assertEqual(response.status_code, 404)

    def test_list(self):
        group = self.factory.create_group()
        ds = self.factory.create_data_source(group=group)
        db.session.flush()
        response = self.make_request(
            "get",
            "/api/groups/{}/data_sources".format(group.id),
            user=self.factory.create_admin(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]["id"], ds.id)


class TestGroupResourceList(BaseTestCase):
    def test_list_admin(self):
        self.factory.create_group(org=self.factory.create_org())
        response = self.make_request("get", "/api/groups", user=self.factory.create_admin())
        g_keys = ["type", "id", "name", "permissions"]

        def filtergroups(gs):
            return [project(g, g_keys) for g in gs]

        self.assertEqual(
            filtergroups(response.json),
            filtergroups(g.to_dict() for g in [self.factory.admin_group, self.factory.default_group]),
        )

    def test_list(self):
        group1 = self.factory.create_group(org=self.factory.create_org(), permissions=["view_dashboard"])
        db.session.flush()
        u = self.factory.create_user(group_ids=[self.factory.default_group.id, group1.id])
        db.session.flush()
        response = self.make_request("get", "/api/groups", user=u)
        g_keys = ["type", "id", "name", "permissions"]

        def filtergroups(gs):
            return [project(g, g_keys) for g in gs]

        self.assertEqual(
            filtergroups(response.json),
            filtergroups(g.to_dict() for g in [self.factory.default_group, group1]),
        )





class TestGroupResourceDelete(BaseTestCase):
    def test_allowed_only_to_admin(self):
        group = self.factory.create_group()

        response = self.make_request("delete", "/api/groups/{}".format(group.id))
        self.assertEqual(response.status_code, 403)

        response = self.make_request(
            "delete",
            "/api/groups/{}".format(group.id),
            user=self.factory.create_admin(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Group.query.get(group.id))

    def test_cant_delete_builtin_group(self):
        for group in [self.factory.default_group, self.factory.admin_group]:
            response = self.make_request(
                "delete",
                "/api/groups/{}".format(group.id),
                user=self.factory.create_admin(),
            )
            self.assertEqual(response.status_code, 400)

    def test_can_delete_group_with_data_sources(self):
        group = self.factory.create_group()
        data_source = self.factory.create_data_source(group=group)

        response = self.make_request(
            "delete",
            "/api/groups/{}".format(group.id),
            user=self.factory.create_admin(),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(data_source, DataSource.query.get(data_source.id))


class TestGroupResourceGet(BaseTestCase):
    def test_returns_group(self):
        rv = self.make_request("get", "/api/groups/{}".format(self.factory.default_group.id))
        self.assertEqual(rv.status_code, 200)

    def test_doesnt_return_if_user_not_member_or_admin(self):
        rv = self.make_request("get", "/api/groups/{}".format(self.factory.admin_group.id))
        self.assertEqual(rv.status_code, 403)


class TestGroupListResourcePost(BaseTestCase):
    def test_admins_can_create_groups(self):
        admin = self.factory.create_admin()
        data = {"name": "New Group"}
        rv = self.make_request("post", "/api/groups", data=data, user=admin)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["name"], "New Group")
        self.assertIsNotNone(Group.query.get(rv.json["id"]))

    def test_non_admins_cannot_create_groups(self):
        data = {"name": "New Group"}
        rv = self.make_request("post", "/api/groups", data=data)
        self.assertEqual(rv.status_code, 403)


class TestGroupResourcePost(BaseTestCase):
    def test_doesnt_change_builtin_groups(self):
        current_name = self.factory.default_group.name

        response = self.make_request(
            "post",
            "/api/groups/{}".format(self.factory.default_group.id),
            user=self.factory.create_admin(),
            data={"name": "Another Name"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(current_name, Group.query.get(self.factory.default_group.id).name)

    def test_admins_can_modify_groups(self):
        group = self.factory.create_group(name="Old Name")
        admin = self.factory.create_admin()
        data = {"name": "New Name"}
        
        rv = self.make_request(
            "post", 
            "/api/groups/{}".format(group.id), 
            data=data, 
            user=admin
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["name"], "New Name")
        self.assertEqual(Group.query.get(group.id).name, "New Name")



