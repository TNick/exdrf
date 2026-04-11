"""Tests for ORM vs schema import name collision handling in al2r routers."""

from exdrf_gen_al2r.relation_specs import al2r_orm_schema_name_collisions


class TestAl2rOrmSchemaNameCollisions:
    """``al2r_orm_schema_name_collisions`` intersection rules."""

    def test_empty_when_no_overlap(self) -> None:
        """Unrelated ORM extras and list types produce no collisions."""

        assert (
            al2r_orm_schema_name_collisions(
                "Gender",
                ["Entity"],
                "Gender",
                ["Town"],
                True,
            )
            == frozenset()
        )

    def test_list_rel_overlap_with_extra_orm(self) -> None:
        """List-relation read models may share names with ORM imports."""

        assert al2r_orm_schema_name_collisions(
            "Gender",
            ["Entity"],
            "Gender",
            ["Entity", "Town"],
            False,
        ) == frozenset({"Entity"})

    def test_main_orm_overlap_with_list_rel(self) -> None:
        """Primary ORM name can match a related list schema name."""

        assert al2r_orm_schema_name_collisions(
            "IssItem",
            [],
            "IssItem",
            ["IssItem", "IssComment"],
            True,
        ) == frozenset({"IssItem"})
