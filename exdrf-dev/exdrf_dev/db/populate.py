import datetime
import random
from typing import Any, Dict, List

from factory.alchemy import SQLAlchemyModelFactory
from factory.declarations import LazyFunction, Sequence, SubFactory
from faker import Faker
from sqlalchemy.orm import Session, sessionmaker

from exdrf_dev.db.models import (
    Child,
    CompositeKeyModel,
    Parent,
    Profile,
    RelatedItem,
    StatusEnum,
    Tag,
    print_db_content,
)

# Initialize faker
fake = Faker()


class TagFactory(SQLAlchemyModelFactory):
    class Meta:  # type: ignore[no-redef]
        model = Tag
        sqlalchemy_session_persistence = "commit"

    id = Sequence(lambda n: n + 1)
    name = LazyFunction(
        lambda: f"{fake.word()}_{fake.random_int(min=1, max=9999999)}"
    )


class ParentFactory(SQLAlchemyModelFactory):
    class Meta:  # type: ignore[no-redef]
        model = Parent
        sqlalchemy_session_persistence = "commit"

    id = Sequence(lambda n: n + 1)
    name = LazyFunction(lambda: fake.company())
    created_at = LazyFunction(
        lambda: fake.date_time_between(
            start_date=datetime.datetime(2020, 1, 1),
            end_date=datetime.datetime(2030, 12, 31),
        )
    )
    is_active = LazyFunction(lambda: random.choice([True, False]))


class ProfileFactory(SQLAlchemyModelFactory):
    class Meta:  # type: ignore[no-redef]
        model = Profile
        sqlalchemy_session_persistence = "commit"

    id = Sequence(lambda n: n + 1)
    bio = LazyFunction(lambda: fake.paragraph(nb_sentences=3))
    parent = SubFactory(ParentFactory)


class ChildFactory(SQLAlchemyModelFactory):
    class Meta:  # type: ignore[no-redef]
        model = Child
        sqlalchemy_session_persistence = "commit"

    id = Sequence(lambda n: n + 1)
    data = LazyFunction(lambda: fake.text(max_nb_chars=200))
    parent = SubFactory(ParentFactory)


class CompositeKeyModelFactory(SQLAlchemyModelFactory):
    class Meta:  # type: ignore[no-redef]
        model = CompositeKeyModel
        sqlalchemy_session_persistence = "commit"

    key_part1 = LazyFunction(
        lambda: (
            "ITEM_"
            + fake.random_letter().upper()
            + str(fake.random_int(min=1, max=999999))
        )
    )
    key_part2 = Sequence(lambda n: n + 100)
    description = LazyFunction(lambda: fake.sentence())
    some_float = LazyFunction(lambda: round(random.uniform(0, 100), 2))
    some_date = LazyFunction(
        lambda: fake.date_between(
            start_date=datetime.date(2020, 1, 1),
            end_date=datetime.date(2030, 12, 31),
        )
    )
    some_time = LazyFunction(lambda: fake.time_object())
    some_enum = LazyFunction(lambda: random.choice(list(StatusEnum)))
    some_json = LazyFunction(
        lambda: {
            "config": random.choice([True, False]),
            "values": [random.randint(1, 100) for _ in range(3)],
            "label": fake.word(),
        }
    )
    some_binary = LazyFunction(lambda: fake.binary(length=16))


class RelatedItemFactory(SQLAlchemyModelFactory):
    class Meta:  # type: ignore[no-redef]
        model = RelatedItem
        sqlalchemy_session_persistence = "commit"

    id = Sequence(lambda n: n + 1)
    item_data = LazyFunction(lambda: fake.text(max_nb_chars=200))
    some_int = LazyFunction(lambda: random.randint(0, 1000))
    # comp_key_part1 and comp_key_part2 will be set later


def populate_session(
    session: Session,
    num_parents: int = 10,
    num_tags: int = 15,
    max_children_per_parent: int = 5,
    max_tags_per_parent: int = 3,
    num_composite_models: int = 8,
    max_related_items_per_comp_model: int = 3,
) -> Dict[str, List[Any]]:
    """
    Populate the database with fake data.

    Args:
        session: SQLAlchemy session
        num_parents: Number of parent records to create
        num_tags: Number of tag records to create
        max_children_per_parent: Maximum number of children per parent
        max_tags_per_parent: Maximum number of tags that can be associated
            with a parent
        num_composite_models: Number of composite key models to create
        max_related_items_per_comp_model: Maximum number of related items
            per composite key model

    Returns:
        A dictionary containing the created objects
    """
    created_objects = {}

    # Configure factories to use the session
    factories = [
        TagFactory,
        ParentFactory,
        ProfileFactory,
        ChildFactory,
        CompositeKeyModelFactory,
        RelatedItemFactory,
    ]
    for factory_class in factories:
        factory_class._meta.sqlalchemy_session = session

    # Create tags
    tags = [TagFactory() for _ in range(num_tags)]
    created_objects["tags"] = tags

    # Create parents with their relationships
    parents = []
    for _ in range(num_parents):
        parent = ParentFactory()

        # Create a profile for this parent
        profile = ProfileFactory(parent_id=parent.id, parent=parent)
        session.add(profile)

        # Create children for this parent
        num_children = random.randint(0, max_children_per_parent)
        children = [
            ChildFactory(parent_id=parent.id, parent=parent)
            for _ in range(num_children)
        ]
        session.add_all(children)

        # Associate tags with this parent
        num_parent_tags = random.randint(0, min(max_tags_per_parent, len(tags)))
        selected_tags = random.sample(tags, num_parent_tags)
        parent.tags = selected_tags

        parents.append(parent)

    created_objects["parents"] = parents

    # Create composite key models with related items
    composite_models = []
    for _ in range(num_composite_models):
        comp_model = CompositeKeyModelFactory()

        # Create related items for this composite key model
        num_related_items = random.randint(0, max_related_items_per_comp_model)
        for _ in range(num_related_items):
            RelatedItemFactory(
                comp_key_part1=comp_model.key_part1,
                comp_key_part2=comp_model.key_part2,
                comp_key_owner=comp_model,
            )

        composite_models.append(comp_model)

    created_objects["composite_models"] = composite_models

    # Commit all changes
    session.commit()

    return created_objects


def populate_database(
    num_parents: int = 10,
    num_tags: int = 15,
    max_children_per_parent: int = 5,
    max_tags_per_parent: int = 3,
    num_composite_models: int = 8,
    max_related_items_per_comp_model: int = 3,
    conn_string: str = "sqlite:///:memory:",
    verbose: bool = False,
):
    """
    Main function to populate the database with fake data.

    Args:
        num_parents: Number of parent records to create
        num_tags: Number of tag records to create
        max_children_per_parent: Maximum number of children per parent
        max_tags_per_parent: Maximum number of tags that can be associated
            with a parent
        num_composite_models: Number of composite key models to create
        max_related_items_per_comp_model: Maximum number of related items per
            composite key model
        use_in_memory_db: Use an in-memory SQLite database if True, otherwise
            use a file-based DB
    """
    # Create engine and session
    from exdrf_al.base import Base
    from sqlalchemy import create_engine

    engine = create_engine(conn_string)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        if verbose:
            print("Populating database with:")
            print(f"- {num_parents} parents")
            print(f"- {num_tags} tags")
            print(f"- Up to {max_children_per_parent} children per parent")
            print(f"- Up to {max_tags_per_parent} tags per parent")
            print(f"- {num_composite_models} composite key models")
            print(
                f"- Up to {max_related_items_per_comp_model} related items "
                "per composite model"
            )

        # Populate database
        created_objects = populate_session(
            session=session,
            num_parents=num_parents,
            num_tags=num_tags,
            max_children_per_parent=max_children_per_parent,
            max_tags_per_parent=max_tags_per_parent,
            num_composite_models=num_composite_models,
            max_related_items_per_comp_model=max_related_items_per_comp_model,
        )

        print("\nDatabase populated successfully!")

        # Print a summary of created objects
        total_children = sum(
            len(parent.children) for parent in created_objects["parents"]
        )
        total_parent_tags = sum(
            len(parent.tags) for parent in created_objects["parents"]
        )
        total_related_items = sum(
            len(comp_model.related_items)
            for comp_model in created_objects["composite_models"]
        )

        if verbose:
            print("\nSummary of created objects:")
            print(f"- {len(created_objects['parents'])} parents")
            print(f"- {len(created_objects['tags'])} tags")
            print(f"- {total_children} children")
            print(f"- {total_parent_tags} parent-tag associations")
            print(
                f"- {len(created_objects['composite_models'])} composite "
                "key models"
            )
            print(f"- {total_related_items} related items")

            # Print database content
            if (
                input(
                    "\nDo you want to see all database content? (y/n): "
                ).lower()
                == "y"
            ):
                print_db_content(engine)

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Populate database with fake data"
    )
    parser.add_argument(
        "--parents", type=int, default=10, help="Number of parent records"
    )
    parser.add_argument(
        "--tags", type=int, default=15, help="Number of tag records"
    )
    parser.add_argument(
        "--max-children",
        type=int,
        default=5,
        help="Maximum children per parent",
    )
    parser.add_argument(
        "--max-tags", type=int, default=3, help="Maximum tags per parent"
    )
    parser.add_argument(
        "--composite-models",
        type=int,
        default=8,
        help="Number of composite key models",
    )
    parser.add_argument(
        "--max-related-items",
        type=int,
        default=3,
        help="Maximum related items per composite model",
    )
    parser.add_argument(
        "--conn-string",
        type=str,
        default="sqlite:///:memory:",
        help="The database to populate",
    )

    args = parser.parse_args()

    populate_database(
        num_parents=args.parents,
        num_tags=args.tags,
        max_children_per_parent=args.max_children,
        max_tags_per_parent=args.max_tags,
        num_composite_models=args.composite_models,
        max_related_items_per_comp_model=args.max_related_items,
        conn_string=args.conn_string,
        verbose=True,
    )
