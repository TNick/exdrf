import pytest

from exdrf_al.calc_q import FieldRef, JoinLoad


class DummyResource:
    def __init__(self, name):
        self.name = name


class DummyField:
    def __init__(self, is_list):
        self.is_list = is_list


class DummyModel:
    def __init__(self, name, fields):
        self.name = name
        self._fields = fields

    def __getitem__(self, key):
        return self._fields[key]


class TestJoinLoad:

    def make_join(self, resource_name, field_name, is_list=False):
        """Helper to create a JoinLoad with a single FieldRef container."""
        res = DummyResource(resource_name)
        fr = FieldRef(
            resource=res, name=field_name, is_list=is_list  # type: ignore
        )
        return JoinLoad(container=fr)

    def test_get_child_returns_none_when_no_children(self):
        parent = self.make_join("ParentRes", "parent_field")
        # No children added yet
        assert parent.get_child("ChildRes", "child_field") is None

    def test_get_child_returns_child_when_present(self):
        parent = self.make_join("ParentRes", "parent_field")
        # Create and add a matching child
        child = self.make_join("ChildRes", "child_field")
        parent.children.append(child)
        # Should find the exact child
        found = parent.get_child("ChildRes", "child_field")
        assert found is child

    def test_get_child_returns_none_for_non_matching_name(self):
        parent = self.make_join("ParentRes", "parent_field")
        # Add a child with different resource name and field
        other = self.make_join("OtherRes", "other_field")
        parent.children.append(other)
        # Look up mismatched combinations
        assert parent.get_child("ChildRes", "child_field") is None
        assert parent.get_child("OtherRes", "child_field") is None
        assert parent.get_child("ChildRes", "other_field") is None

    def test_get_child_returns_correct_among_multiple_children(self):
        parent = self.make_join("ParentRes", "parent_field")
        child1 = self.make_join("Res1", "field1")
        child2 = self.make_join("Res2", "field2")
        child3 = self.make_join("Res3", "field3")
        parent.children.extend([child1, child2, child3])
        # Should return the second child when searched by its resource and field
        assert parent.get_child("Res2", "field2") is child2
        # Ensure others still found correctly
        assert parent.get_child("Res1", "field1") is child1
        assert parent.get_child("Res3", "field3") is child3

    class TestJoinLoadGetJoin:
        def test_get_join_creates_new_child(self):
            parent = JoinLoad(
                container=FieldRef(
                    resource=DummyModel("P", {}),  # type: ignore
                    name="p",
                    is_list=False,
                )
            )
            # prepare a model with a field 'child' marked as list
            model = DummyModel("ChildRes", {"child": DummyField(is_list=True)})
            # call get_join
            new_join = parent.get_join(model, "child")  # type: ignore
            # should add exactly one child
            assert len(parent.children) == 1
            assert new_join is parent.children[0]
            # the container of the new join must reference the model and field
            fr = new_join.container
            assert fr.resource is model
            assert fr.name == "child"
            assert fr.is_list is True

        def test_get_join_returns_existing_child(self):
            # create parent and an existing join for the same model.field
            model = DummyModel("ResX", {"f": DummyField(is_list=False)})
            existing = JoinLoad(
                container=FieldRef(
                    resource=model, name="f", is_list=False  # type: ignore
                )
            )
            parent = JoinLoad(
                container=FieldRef(
                    resource=DummyModel("P", {}),  # type: ignore
                    name="p",
                    is_list=False,
                )
            )
            parent.children.append(existing)
            # calling get_join again should return the same object without
            # adding new
            result = parent.get_join(model, "f")  # type: ignore
            assert result is existing
            assert len(parent.children) == 1

        def test_get_join_raises_key_error_for_missing_field(self):
            parent = JoinLoad(
                container=FieldRef(
                    resource=DummyModel("P", {}),  # type: ignore
                    name="p",
                    is_list=False,
                )
            )
            model = DummyModel("M", {})  # no fields
            with pytest.raises(KeyError):
                parent.get_join(model, "nonexistent")  # type: ignore

    class TestCollectResources:

        def test_single_node(self):
            # A single JoinLoad node with no children or load_only
            root_res = DummyResource("root")
            root = JoinLoad(
                container=FieldRef(
                    resource=root_res, name="f", is_list=False  # type: ignore
                )
            )
            result = []
            returned = root.collect_resources(result)
            # Should return the same list and contain only the root resource
            assert returned is result
            assert result == [root_res]

        def test_with_children_and_load_only(self):
            # Build a tree: root -> child, with load_only on both
            root_res = DummyResource("root")
            child_res = DummyResource("child")
            lo_child_res = DummyResource("lo_child")
            lo_root_res = DummyResource("lo_root")

            root = JoinLoad(
                container=FieldRef(
                    resource=root_res, name="f", is_list=False  # type: ignore
                )
            )
            child = JoinLoad(
                container=FieldRef(resource=child_res, name="g", is_list=False)
            )  # type: ignore
            # child has one load_only
            child.load_only.append(
                FieldRef(
                    resource=lo_child_res, name="x", is_list=False  # type: ignore
                )
            )
            # root has one load_only
            root.load_only.append(
                FieldRef(
                    resource=lo_root_res, name="y", is_list=False  # type: ignore
                )
            )
            # attach child to root
            root.children.append(child)

            result = []
            root.collect_resources(result)
            # The order is: root, then child, then child's load_only, then
            # root's load_only
            assert result == [root_res, child_res, lo_child_res, lo_root_res]

    class TestStringify:

        def test_no_children_no_load_only(self):
            root_res = DummyResource("R")
            root = JoinLoad(
                container=FieldRef(
                    resource=root_res, name="f", is_list=False  # type: ignore
                )
            )
            result = root.stringify()
            expected = (
                "                joinedload(\n"
                "                    DbR.f,\n"
                "                )\n"
            )
            assert result == expected

        def test_with_load_only(self):
            root_res = DummyResource("Root")
            lo_res = DummyResource("Lo")
            root = JoinLoad(
                container=FieldRef(
                    resource=root_res, name="fld", is_list=False  # type: ignore
                )
            )
            root.load_only.append(
                FieldRef(
                    resource=lo_res, name="x", is_list=True  # type: ignore
                )
            )
            result = root.stringify()
            expected = (
                "                joinedload(\n"
                "                    DbRoot.fld,\n"
                "                ).load_only(\n"
                "                    DbLo.x,\n"
                "                )\n"
            )
            assert result == expected

        def test_with_child_and_load_only(self):
            root_res = DummyResource("Root")
            child_res = DummyResource("Child")
            root = JoinLoad(
                container=FieldRef(
                    resource=root_res, name="fld", is_list=False  # type: ignore
                )
            )
            child = JoinLoad(
                container=FieldRef(
                    resource=child_res, name="fld2", is_list=True  # type: ignore
                )
            )
            child.load_only.append(
                FieldRef(
                    resource=child_res, name="sub", is_list=False  # type: ignore
                )
            )
            root.children.append(child)
            result = root.stringify()
            expected = (
                "                joinedload(\n"
                "                    DbRoot.fld,\n"
                "                ).selectinload(\n"
                "                    DbChild.fld2,\n"
                "                ).load_only(\n"
                "                    DbChild.sub,\n"
                "                )\n"
            )
            assert result == expected
