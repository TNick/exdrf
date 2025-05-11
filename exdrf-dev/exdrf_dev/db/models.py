import datetime
import enum
from typing import Any, Dict, List, Optional

from exdrf_al.base import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Time,
    create_engine,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)


class StatusEnum(enum.Enum):
    """Enumeration for various status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Association Table for Many-to-Many ---


class ParentTagAssociation(Base):
    """Association object for the many-to-many relationship between Parent and
    Tag.
    """

    __tablename__ = "parent_tag_association"
    __table_args__ = (
        PrimaryKeyConstraint("parent_id", "tag_id"),
        {"info": {"label": """(concat "Parent:" parent_id " Tag:" tag_id)"""}},
    )

    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parents.id"),
        primary_key=True,
        doc="Foreign key to the parents table.",
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id"),
        primary_key=True,
        doc="Foreign key to the tags table.",
    )

    def __repr__(self) -> str:
        return (
            f"<ParentTagAssociation("
            f"parent_id={self.parent_id}, "
            f"tag_id={self.tag_id})>"
        )


# --- Model Definitions ---


class Parent(Base):
    """Represents a parent entity with various relationships."""

    __tablename__ = "parents"
    __table_args__ = {"info": {"label": """(concat "ID:" id " Name:" name)"""}}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, doc="Primary key for the parent."
    )
    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        doc="Name of the parent.",
        info={
            "min_length": 1,
            "multiline": False,
            "visible": True,
            "sortable": True,
            "filterable": True,
        },
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        doc="Timestamp when the parent was created.",
        info={
            "min": datetime.datetime(2020, 1, 1, 0, 0),
            "max": datetime.datetime(2030, 12, 31, 23, 59),
        },
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Flag indicating if the parent is active.",
        info={
            "true_str": "Active",
            "false_str": "Inactive",
        },
    )

    # One-to-Many relationship with Child
    children: Mapped[List["Child"]] = relationship(
        "Child",
        back_populates="parent",
        cascade="all, delete-orphan",
        info={
            "doc": "Children associated with this parent.",
            "direction": "OneToMany",
        },
    )

    # One-to-One relationship with Profile
    profile: Mapped[Optional["Profile"]] = relationship(
        "Profile",
        back_populates="parent",
        uselist=False,
        cascade="all, delete-orphan",
        info={
            "doc": "Profile associated with this parent (one-to-one).",
            "direction": "OneToOne",
        },
    )

    # Many-to-Many relationship with Tag
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="parent_tag_association",
        back_populates="parents",
        info={
            "doc": "Tags associated with this parent (many-to-many).",
            "direction": "ManyToMany",
        },
    )

    def __repr__(self) -> str:
        return f"<Parent(id={self.id}, name='{self.name}')>"


class Child(Base):
    """Represents a child entity linked to a parent."""

    __tablename__ = "children"
    __table_args__ = {
        "info": {
            "label": """
            (concat "ID:" id " Parent " parent.name " Data:" data)
            """
        }
    }

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, doc="Primary key for the child."
    )
    data: Mapped[Optional[str]] = mapped_column(
        String,
        doc="Some data associated with the child.",
        info={
            "min_length": 1,
            "max_length": 200,
            "multiline": True,
            "visible": True,
            "sortable": True,
            "filterable": True,
        },
    )
    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parents.id"),
        doc="Foreign key linking to the parent.",
    )

    # Many-to-One relationship with Parent
    parent: Mapped["Parent"] = relationship(
        "Parent",
        back_populates="children",
        info={
            "doc": "The parent associated with this child.",
            "direction": "ManyToOne",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<Child(id={self.id}, data='{self.data}', "
            f"parent_id={self.parent_id})>"
        )


class Profile(Base):
    """Represents a profile entity linked one-to-one with a parent."""

    __tablename__ = "profiles"
    __table_args__ = {"info": {"label": """(concat "ID:" id " Bio:" bio)"""}}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, doc="Primary key for the profile."
    )
    bio: Mapped[Optional[str]] = mapped_column(
        String, doc="Biography text for the profile."
    )
    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parents.id"),
        unique=True,  # Ensures one-to-one relationship at the DB level
        doc="Foreign key linking to the parent (must be unique).",
    )

    # One-to-One relationship back to Parent
    parent: Mapped["Parent"] = relationship(
        "Parent",
        back_populates="profile",
        info={
            "doc": "The parent associated with this profile.",
            "direction": "OneToOne",
        },
    )

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, parent_id={self.parent_id})>"


class Tag(Base):
    """Represents a tag entity for many-to-many relationships."""

    __tablename__ = "tags"
    __table_args__ = {"info": {"label": """(concat "ID:" id " Name:" name)"""}}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, doc="Primary key for the tag."
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, doc="Unique name of the tag."
    )

    # Many-to-Many relationship back to Parent
    parents: Mapped[List["Parent"]] = relationship(
        "Parent",
        secondary="parent_tag_association",
        back_populates="tags",
        info={
            "doc": "Parents associated with this tag.",
            "direction": "ManyToMany",
        },
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"


class CompositeKeyModel(Base):
    """Demonstrates a model with a composite primary key and various data
    types.
    """

    __tablename__ = "comp_key_models"

    # Composite Primary Key
    key_part1: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        doc="First part of the composite primary key (string).",
    )
    key_part2: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        doc="Second part of the composite primary key (integer).",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String,
        doc="A description for this record.",
        info={
            "multiline": True,
        },
    )
    some_float: Mapped[Optional[float]] = mapped_column(
        Float,
        doc="A floating-point number.",
        info={
            "min": 0.0,
            "max": 100.0,
            "precision": 2,
            "scale": 2,
            "unit": "units",
            "unit_symbol": "u",
        },
    )
    some_date: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        doc="A date value.",
        info={
            "min": datetime.date(2020, 1, 1),
            "max": datetime.date(2030, 12, 31),
        },
    )
    some_time: Mapped[Optional[datetime.time]] = mapped_column(
        Time,
        doc="A time value.",
    )
    some_enum: Mapped[Optional[StatusEnum]] = mapped_column(
        Enum(StatusEnum), doc="An enum value representing status."
    )
    some_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, doc="A JSON object."
    )
    some_binary: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary,
        doc="Binary data.",
        info={
            "visible": False,
            "sortable": False,
            "filterable": False,
            "mime_type": "application/octet-stream",
        },
    )

    # One-to-Many relationship with RelatedItem using composite foreign key
    related_items: Mapped[List["RelatedItem"]] = relationship(
        "RelatedItem",
        back_populates="comp_key_owner",
        cascade="all, delete-orphan",
        foreign_keys="[RelatedItem.comp_key_part1, RelatedItem.comp_key_part2]",
        info={
            "doc": "Items related to this composite key model.",
            "direction": "OneToMany",
        },
    )

    __table_args__ = (
        PrimaryKeyConstraint("key_part1", "key_part2", name="composite_pk"),
        {"info": {"label": """(concat "Description:" description)"""}},
    )

    def __repr__(self) -> str:
        return (
            f"<CompositeKeyModel(key_part1='{self.key_part1}', "
            f"key_part2={self.key_part2})>"
        )


class RelatedItem(Base):
    """Model related to CompositeKeyModel via its composite key."""

    __tablename__ = "related_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, doc="Primary key for the related item."
    )
    item_data: Mapped[Optional[str]] = mapped_column(
        String(200), doc="Data specific to the related item."
    )
    some_int: Mapped[Optional[int]] = mapped_column(
        Integer,
        doc="An integer value associated with the related item.",
        info={
            "min": 0,
            "max": 1000,
            "unit": "units",
            "unit_symbol": "u",
        },
    )

    # Composite Foreign Key parts
    comp_key_part1: Mapped[str] = mapped_column(
        String(50), doc="Foreign key part 1 referencing CompositeKeyModel."
    )
    comp_key_part2: Mapped[int] = mapped_column(
        Integer, doc="Foreign key part 2 referencing CompositeKeyModel."
    )

    # Many-to-One relationship back to CompositeKeyModel
    comp_key_owner: Mapped["CompositeKeyModel"] = relationship(
        "CompositeKeyModel",
        back_populates="related_items",
        foreign_keys=[comp_key_part1, comp_key_part2],
        info={
            "doc": "The owner model with the composite key.",
            "direction": "ManyToOne",
        },
    )

    # Define the composite foreign key constraint
    __table_args__ = (
        ForeignKeyConstraint(
            ["comp_key_part1", "comp_key_part2"],
            ["comp_key_models.key_part1", "comp_key_models.key_part2"],
            name="related_item_composite_fk",
        ),
        {"info": {"label": """(concat "ID:" id)"""}},
    )

    def __repr__(self) -> str:
        return (
            f"<RelatedItem(id={self.id}, "
            f"key1='{self.comp_key_part1}', key2={self.comp_key_part2})>"
        )


def get_dev_engine():
    """Creates an in-memory SQLite database engine for development/testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def get_populated_dev_engine(engine=None):
    """Creates an in-memory SQLite database engine and populates it with
    sample data.
    """
    if engine is None:
        engine = get_dev_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as session:
        # Create instances
        tag1 = Tag(name="Urgent")
        tag2 = Tag(name="Project Alpha")

        parent1 = Parent(name="Parent One")
        parent1.profile = Profile(bio="Profile for Parent One")
        parent1.children.append(Child(data="Child A data"))
        parent1.children.append(Child(data="Child B data"))
        parent1.tags.extend([tag1, tag2])

        parent2 = Parent(name="Parent Two", is_active=False)
        parent2.children.append(Child(data="Child C data"))
        parent2.tags.append(tag1)

        comp_key_obj1 = CompositeKeyModel(
            key_part1="ITEM_A",
            key_part2=101,
            description="First composite item",
            some_float=3.14,
            some_date=datetime.date(2023, 1, 15),
            some_time=datetime.time(10, 30, 0),
            some_enum=StatusEnum.PROCESSING,
            some_json={"config": True, "values": [1, 2, 3]},
            some_binary=b"\x01\x02\x03\x04",
        )
        comp_key_obj1.related_items.append(
            RelatedItem(item_data="Related data 1", some_int=42)
        )
        comp_key_obj1.related_items.append(
            RelatedItem(item_data="Related data 2", some_int=84)
        )

        comp_key_obj2 = CompositeKeyModel(
            key_part1="ITEM_B",
            key_part2=202,
            description="Second composite item",
            some_enum=StatusEnum.COMPLETED,
        )

        # Add to session and commit
        session.add_all([parent1, parent2, comp_key_obj1, comp_key_obj2])
        session.commit()

    return engine


def print_db_content(engine):
    """Prints the content of all tables defined in Base.metadata."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models_to_print = [
        Parent,
        Child,
        Profile,
        Tag,
        CompositeKeyModel,
        RelatedItem,
    ]

    with SessionLocal() as session:
        for model_cls in models_to_print:
            table_name = model_cls.__tablename__
            print(f"\n--- Table: {table_name} ---")
            try:
                instances = session.query(model_cls).all()
                if instances:
                    for instance in instances:
                        print(instance)
                else:
                    print("(empty)")
            except Exception as e:
                print(f"Error querying table {table_name}: {e}")


if __name__ == "__main__":
    # Example usage
    engine = get_populated_dev_engine()
    print_db_content(engine)
    print("Database populated and printed successfully.")
