"""Keep separate group membership periods when an athlete rejoins."""
from alembic import op
import sqlalchemy as sa

revision = "8d9c211a40b2"
down_revision = "46500c8882f8"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "uq_training_group_memberships_club_id_group_id_athlete_id"
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s_%(column_2_name)s"}


def upgrade():
    # SQLite's original constraint was unnamed; PostgreSQL gives it a generated name.
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("training_group_memberships")
    original_name = next(
        item["name"] or CONSTRAINT_NAME
        for item in constraints
        if item["column_names"] == ["club_id", "group_id", "athlete_id"]
    )
    with op.batch_alter_table("training_group_memberships", naming_convention=NAMING) as batch:
        batch.drop_constraint(original_name, type_="unique")
        batch.create_index(
            "one_open_group_membership", ["club_id", "group_id", "athlete_id"],
            unique=True,
            sqlite_where=sa.text("left_on IS NULL"),
            postgresql_where=sa.text("left_on IS NULL"),
        )


def downgrade():
    duplicate = op.get_bind().execute(sa.text("""
        SELECT 1 FROM training_group_memberships
        GROUP BY club_id, group_id, athlete_id
        HAVING COUNT(*) > 1
        LIMIT 1
    """)).first()
    if duplicate:
        raise RuntimeError("No se puede revertir sin perder períodos de pertenencia; restaura una copia previa")
    with op.batch_alter_table("training_group_memberships") as batch:
        batch.drop_index("one_open_group_membership")
        batch.create_unique_constraint(CONSTRAINT_NAME, ["club_id", "group_id", "athlete_id"])
