# SQL

## Explain the different JOIN types.
Tags: joins

- INNER: rows with a match on both sides.
- LEFT: every row from the left, NULLs where the right has no match. Filter `WHERE right.id IS NULL` for an anti-join.
- RIGHT: mirror of LEFT (rarely used — swap the tables instead).
- FULL OUTER: everything from both sides.
- CROSS: Cartesian product.
- Watch out: putting a right-table condition in `WHERE` turns a LEFT JOIN into an INNER JOIN; put it in `ON`.

## WHERE vs HAVING?
Tags: aggregation

`WHERE` filters rows before grouping; `HAVING` filters groups after aggregation. `SELECT dept, COUNT(*) FROM emp GROUP BY dept HAVING COUNT(*) > 5`.

## Find the second-highest salary (and the Nth).
Tags: window functions

```sql
SELECT salary FROM (
  SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk
  FROM employees
) t WHERE rnk = 2;
```
`DENSE_RANK` handles ties; mention the `LIMIT 1 OFFSET 1` approach and its tie problem.

## What are window functions? Give a real example.
Tags: window functions

They compute across related rows without collapsing them. Running totals, rankings, and comparing to the previous row:

```sql
SELECT day, revenue,
       SUM(revenue) OVER (ORDER BY day) AS running_total,
       revenue - LAG(revenue) OVER (ORDER BY day) AS change
FROM daily_sales;
```

## How do indexes work, and when do they hurt?
Tags: indexes, performance

- A B-tree index keeps keys sorted so lookups/range scans are O(log n) instead of a full scan.
- Composite index `(a, b)` helps queries filtering on `a` or `a AND b`, not `b` alone (leftmost-prefix rule).
- Costs: slower INSERT/UPDATE, more storage; low-selectivity columns (booleans) rarely benefit.
- Use `EXPLAIN ANALYZE` to confirm the planner uses it.

## Explain ACID and transaction isolation levels.
Tags: transactions

Atomicity, Consistency, Isolation, Durability. Isolation levels trade anomalies for concurrency: Read Uncommitted (dirty reads), Read Committed (Postgres default; non-repeatable reads), Repeatable Read (phantoms in the standard; Postgres prevents them), Serializable (transactions behave as if run one by one; may abort with serialization errors — retry).

## What is the N+1 query problem?
Tags: orm, performance

Loading a list then issuing one query per row for a relationship (1 + N queries). Fix with joins or eager loading — in SQLAlchemy `selectinload`/`joinedload`, in Django `select_related`/`prefetch_related`.

## Normalisation vs denormalisation?
Tags: modelling

Normalise (1NF–3NF) to remove duplication and update anomalies; denormalise deliberately for read-heavy paths (reporting tables, caches, materialized views) and accept the cost of keeping copies in sync.

## DELETE vs TRUNCATE vs DROP?
Tags: basics

DELETE removes rows (filterable, fires triggers, logged row by row); TRUNCATE removes all rows fast and resets storage; DROP removes the table itself.

## How would you find duplicate emails in a users table?
Tags: aggregation

```sql
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
```
To delete all but the oldest: use `ROW_NUMBER() OVER (PARTITION BY email ORDER BY id)` and delete rows where it is > 1.

## What is a CTE and when is a recursive CTE useful?
Tags: cte

`WITH name AS (...)` names a subquery for readability and reuse. Recursive CTEs walk hierarchies — org charts, category trees, graph traversal.
