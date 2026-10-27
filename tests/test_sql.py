from dryer.extract import entries_in_source
from dryer.shape import jaccard

LEFT = """with orders as (
    select id, coalesce(amount, 0) as amount, status
    from {{ ref('raw_orders') }}
    where status != 'void' and amount > 0
)
select * from orders
"""

RIGHT = """with invoices as (
    select key, coalesce(total, 0) as total, state
    from {{ ref('raw_invoices') }}
    where state != 'cancelled' and total > 0
)
select * from invoices
"""

OTHER = """with people as (
    select p.name, row_number() over (partition by p.team order by p.started desc) as rank
    from {{ ref('people') }} p
    left join {{ ref('teams') }} t on t.id = p.team
)
select * from people where rank = 1
"""


def _first(source, file):
    entries, warning = entries_in_source("sql", source, file, file)
    assert warning is None
    return entries[0]


def test_renamed_ctes_are_identical():
    left = _first(LEFT, "models/a.sql")
    right = _first(RIGHT, "models/b.sql")
    assert (left.start_line, left.end_line) == (1, 5)
    assert jaccard(left.fingerprints, right.fingerprints) == 1.0


def test_different_ctes_score_low():
    left = _first(LEFT, "models/a.sql")
    other = _first(OTHER, "models/c.sql")
    assert jaccard(left.fingerprints, other.fingerprints) < 0.5


def test_import_ctes_are_not_compared():
    source = "with a as (\n  select x,\n  y,\n  z\n  from {{ ref('r') }}\n)\nselect * from a\n"
    entries, _warning = entries_in_source("sql", source, "m.sql", "m.sql")
    assert [(entry.start_line, entry.end_line) for entry in entries] == [(7, 7)]
