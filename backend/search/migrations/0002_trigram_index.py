"""Trigram index for middle-of-word search. PostgreSQL only.

The token index answers "starts with", which covers almost everything a guard
types. It cannot answer "contains": searching `gish` will never find
`Mugisha`, because a B-tree has no idea where mid-word matches live.

`pg_trgm` fills exactly that gap. It is a genuine complement rather than a
replacement: prefix search stays faster and is tried first (see
search/indexer.py); trigram is the fallback when a prefix finds nothing.

Every operation here is a no-op on SQLite, so the demo database still migrates
cleanly with no Postgres anywhere.
"""

from django.db import migrations


class TrigramIfPostgres(migrations.RunPython):
    """RunPython that simply does nothing on a non-Postgres backend."""


def create_trigram(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        # Requires the extension to be installable: a superuser or a database
        # where it is already whitelisted. If this fails, the token index still
        # works and only mid-word search is unavailable.
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS search_token_trgm_idx "
            "ON search_searchtoken USING gin (token gin_trgm_ops)"
        )


def drop_trigram(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS search_token_trgm_idx")


class Migration(migrations.Migration):
    dependencies = [("search", "0001_initial")]

    operations = [migrations.RunPython(create_trigram, drop_trigram)]
