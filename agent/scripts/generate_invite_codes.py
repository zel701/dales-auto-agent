"""Invitation code admin tool — generate, list, annotate, revoke.

Run from the agent directory:

  # mint a batch of 100 and save them to a CSV you can mail-merge from
  uv run python -m scripts.generate_invite_codes --count 100 --label batch1 \
      --out invite-codes.csv

  # who has used what
  uv run python -m scripts.generate_invite_codes --list
  uv run python -m scripts.generate_invite_codes --list --status active

  # record who a code went to, after the fact
  uv run python -m scripts.generate_invite_codes --note batch1-007 "Mike (Reddit)"

  # kill a leaked code
  uv run python -m scripts.generate_invite_codes --revoke DALE-7K3M

Codes are stored in plaintext on purpose — they are access tokens for a closed
beta, not credentials, and being able to read them back is the whole point of
the tracking columns.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys

from dotenv import load_dotenv

load_dotenv()

from car_agent.db.database import init_db
from car_agent.db.repositories.invite_repo import (
    create_invite_codes,
    list_invite_codes,
    normalize_code,
    revoke_invite_code,
    set_note,
)


def _status(row) -> str:
    if row.revoked_at is not None:
        return "revoked"
    if row.consumed_at is not None:
        return "consumed"
    return "active"


async def do_generate(count: int, label: str, note: str | None, out: str | None) -> None:
    rows = await create_invite_codes(count, label, note)
    print(f"Created {len(rows)} invitation codes\n")
    for row in rows:
        print(f"  {row.label}  {row.code}")

    if out:
        with open(out, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["label", "code", "note"])
            for row in rows:
                writer.writerow([row.label, row.code, row.note or ""])
        print(f"\nWrote {out}")


async def do_list(status: str | None) -> None:
    rows = await list_invite_codes(status)
    if not rows:
        print("No invitation codes found.")
        return

    header = ("label", "code", "status", "consumed_at", "customer", "note")
    table = [header]
    for row, email in rows:
        table.append((
            row.label,
            row.code,
            _status(row),
            row.consumed_at.strftime("%Y-%m-%d %H:%M") if row.consumed_at else "—",
            email or "—",
            row.note or "—",
        ))

    widths = [max(len(r[i]) for r in table) for i in range(len(header))]
    for i, line in enumerate(table):
        print("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(line)))
        if i == 0:
            print("  ".join("-" * w for w in widths))

    consumed = sum(1 for row, _ in rows if row.consumed_at is not None)
    print(f"\n{len(rows)} codes — {consumed} consumed, {len(rows) - consumed} unspent")


async def do_note(label: str, text: str) -> None:
    if await set_note(label, text):
        print(f"Noted {label}: {text}")
    else:
        print(f"No code labelled {label}", file=sys.stderr)
        sys.exit(1)


async def do_revoke(raw: str) -> None:
    code = normalize_code(raw)
    if code is None:
        print(f"Not a valid code: {raw}", file=sys.stderr)
        sys.exit(1)
    if await revoke_invite_code(code):
        print(f"Revoked {code}")
    else:
        print(f"{code} is unknown or already revoked", file=sys.stderr)
        sys.exit(1)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, help="how many codes to generate")
    parser.add_argument("--label", help="label prefix, e.g. batch1")
    parser.add_argument(
        "--note", nargs="+", metavar=("LABEL", "TEXT"),
        help="with --count: a note applied to the whole batch. "
             "Alone: --note <label> \"<text>\" annotates one code.",
    )
    parser.add_argument("--out", help="write the batch to this CSV")
    parser.add_argument("--list", action="store_true", help="show all codes")
    parser.add_argument("--status", choices=["active", "consumed", "revoked"])
    parser.add_argument("--revoke", metavar="CODE")
    args = parser.parse_args()

    await init_db()

    if args.revoke:
        await do_revoke(args.revoke)
    elif args.list:
        await do_list(args.status)
    elif args.count:
        if not args.label:
            parser.error("--count requires --label")
        note = " ".join(args.note) if args.note else None
        await do_generate(args.count, args.label, note, args.out)
    elif args.note:
        if len(args.note) < 2:
            parser.error('--note needs a label and text: --note batch1-007 "Mike"')
        await do_note(args.note[0], " ".join(args.note[1:]))
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
