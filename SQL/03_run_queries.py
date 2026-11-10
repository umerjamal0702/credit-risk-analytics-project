"""
Run every query in 02_analytical_queries.sql against the warehouse and write
the results to 04_query_results.md.

The file is split on the `-- Qn.` banner comments, so the results file stays in
step with the query file: add a query there and it appears here on the next run.
Long result sets are truncated in the written output, with the full row count
stated, so the results file stays readable.
"""
import re
import sqlite3
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / 'credit_risk_warehouse.db'
SRC = HERE / '02_analytical_queries.sql'
OUT = HERE / '04_query_results.md'

MAX_ROWS = 25  # rows written per result set before truncating


def split_queries(text):
    """Yield (number, title, sql) for each `-- Qn.` banner section."""
    banner = re.compile(r'^--\s*Q(\d+)\.\s*(.*)$', re.M)
    marks = list(banner.finditer(text))
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[start:end]

        # continuation lines of the title comment, before the rule line
        title = m.group(2).strip()
        for line in block.split('\n'):
            s = line.strip()
            if s.startswith('--') and set(s) != {'-'} and not s.strip('- '):
                break
            if s.startswith('--') and s.strip('- '):
                title += ' ' + s.lstrip('- ').strip()
            elif s and not s.startswith('--'):
                break

        sql = '\n'.join(l for l in block.split('\n')
                        if not l.strip().startswith('--')).strip()
        if sql:
            yield int(m.group(1)), title.strip(), sql


def fmt(v, col=''):
    """Format one cell. Year and period columns keep no thousands separator,
    since 2,007 reads as a quantity rather than a year."""
    if v is None:
        return ''
    plain = col.endswith('year') or col.endswith('month') or 'yyyymm' in col
    if isinstance(v, float):
        if plain:
            return f'{v:.0f}'
        return f'{v:,.4f}'.rstrip('0').rstrip('.') if abs(v) < 1 else f'{v:,.2f}'
    if isinstance(v, int):
        return str(v) if plain else f'{v:,}'
    return str(v)


def main():
    conn = sqlite3.connect(DB)
    text = SRC.read_text()
    lines = [
        '# Query Results',
        '',
        'Output of every query in `02_analytical_queries.sql`, run against the '
        'warehouse built by `00_build_warehouse.py` over the full 2007-2018 '
        'LendingClub data: 2,260,668 funded loans and 27,648,741 declined '
        'applications.',
        '',
        f'Regenerate with `python SQL/03_run_queries.py`. Result sets longer than '
        f'{MAX_ROWS} rows are truncated here; the full row count is stated above each table.',
        '',
        '---',
        '',
    ]

    for num, title, sql in split_queries(text):
        t0 = time.time()
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        elapsed = time.time() - t0

        lines.append(f'## Q{num}. {title}')
        lines.append('')
        lines.append(f'{len(rows):,} rows returned in {elapsed:.1f}s.'
                     + (f' First {MAX_ROWS} shown.' if len(rows) > MAX_ROWS else ''))
        lines.append('')
        lines.append('| ' + ' | '.join(cols) + ' |')
        lines.append('|' + '|'.join('---' for _ in cols) + '|')
        for r in rows[:MAX_ROWS]:
            lines.append('| ' + ' | '.join(fmt(v, c) for v, c in zip(r, cols)) + ' |')
        lines.append('')
        print(f'Q{num}: {len(rows):,} rows in {elapsed:.1f}s - {title[:60]}')

    OUT.write_text('\n'.join(lines) + '\n')
    conn.close()
    print(f'\nWrote {OUT}')


if __name__ == '__main__':
    main()
