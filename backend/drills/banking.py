"""Drill 1 — Banking System (the canonical Ramp ICA archetype)."""

from harness import ANY, Pred  # noqa: F401  (available to test authors)

SLUG = "banking"
TITLE = "Banking System"
DIFFICULTY = "Ramp ICA archetype · 4 levels"
ENTRYPOINT = "Bank"

MARKDOWN = r"""
# Banking System

Timestamps arrive **non-decreasing**. All amounts are positive integers unless
stated. Design the state object once — the later levels will punish a scalar
balance.

---

## Level 1 — Accounts & transfers

- **`create_account(ts, account_id) -> bool`** — `True` if created, `False` if it
  already exists.
- **`deposit(ts, account_id, amount) -> int | None`** — new balance, or `None`
  if the account doesn't exist.
- **`transfer(ts, source_id, target_id, amount) -> int | None`** — source's new
  balance, or `None` if: source or target missing, `source_id == target_id`, or
  insufficient funds.

## Level 2 — Ranking

- **`top_spenders(ts, n) -> list[str]`** — the top `n` accounts by **total
  outgoing** (transfers out + payments out), formatted `"account_id(outgoing)"`,
  sorted by outgoing **descending**, ties broken by `account_id` **ascending**.
  Fewer than `n` accounts → return all.

## Level 3 — Scheduled cashback

- **`pay(ts, account_id, amount) -> str | None`** — withdraw `amount`, return an
  ordinal id `"payment1"`, `"payment2"`, … (global counter). `None` if account
  missing or insufficient funds. **Counts toward outgoing.** Schedules **2%
  cashback (floored)** to be credited back **24h later** (`86_400_000` ms).
- **`get_payment_status(ts, account_id, payment_id) -> str | None`** —
  `"IN_PROGRESS"` or `"CASHBACK_RECEIVED"`; `None` if account missing, payment id
  unknown, or the payment doesn't belong to that account.
- Cashback must be applied **lazily** based on the current timestamp, before each
  operation is handled.

## Level 4 — Merge & history

- **`merge_accounts(ts, id_1, id_2) -> bool`** — merge `id_2` **into** `id_1`.
  Combine balances and outgoing totals; re-point any pending cashback from `id_2`
  to `id_1`; remove `id_2`. `False` if either is missing or `id_1 == id_2`.
  Payment status queries for a merged payment must work under `id_1`.
- **`get_balance(ts, account_id, time_at) -> int | None`** — the account's
  balance **as of `time_at`**, reflecting any cashback that had landed by
  `time_at`. `None` if the account didn't exist at `time_at` (or doesn't exist
  now). `time_at <= ts`.

---

> **Read all four levels before writing one line.** L4 (`get_balance` at an
> arbitrary time, `merge`) tells you balance can't be an `int` — store a
> checkpoint log, and cashbacks become re-pointable events.
"""

STARTER = '''\
import bisect

DAY = 86_400_000   # 24h in ms


class Bank:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def create_account(self, ts, account_id):
        pass

    def deposit(self, ts, account_id, amount):
        pass

    def transfer(self, ts, source_id, target_id, amount):
        pass

    # ---- Level 2 ----
    def top_spenders(self, ts, n):
        pass

    # ---- Level 3 ----
    def pay(self, ts, account_id, amount):
        pass

    def get_payment_status(self, ts, account_id, payment_id):
        pass

    # ---- Level 4 ----
    def merge_accounts(self, ts, id_1, id_2):
        pass

    def get_balance(self, ts, account_id, time_at):
        pass
'''

REFERENCE = '''\
import bisect

DAY = 86_400_000          # 24h in ms
CASHBACK_RATE = 2         # percent, floored


class Account:
    __slots__ = ("created", "balance", "outgoing", "h_ts", "h_bal")

    def __init__(self, ts):
        self.created = ts
        self.balance = 0
        self.outgoing = 0
        self.h_ts = [ts]      # checkpoint timestamps (non-decreasing)
        self.h_bal = [0]      # resulting balance at each checkpoint

    def _record(self, ts):
        if self.h_ts[-1] == ts:
            self.h_bal[-1] = self.balance      # same-ts change overwrites
        else:
            self.h_ts.append(ts)
            self.h_bal.append(self.balance)

    def balance_at(self, time_at):
        i = bisect.bisect_right(self.h_ts, time_at) - 1
        return None if i < 0 else self.h_bal[i]


class Bank:
    def __init__(self):
        self.accts = {}
        self.payment_counter = 0
        self.pending = []          # (exec_t, seq, acct_id, amount, pid)
        self.pending_keys = []     # parallel exec_t list for bisect
        self.pay_status = {}       # pid -> IN_PROGRESS | CASHBACK_RECEIVED
        self.pay_owner = {}        # pid -> account_id (mutated on merge)

    # lazy cashback engine — run before EVERY op
    def _advance(self, t):
        while self.pending and self.pending_keys[0] <= t:
            self.pending_keys.pop(0)
            exec_t, _seq, acc_id, amount, pid = self.pending.pop(0)
            owner = self.pay_owner.get(pid, acc_id)
            a = self.accts.get(owner)
            if a is not None:
                a.balance += amount
                a._record(exec_t)              # checkpoint at LANDING time
            self.pay_status[pid] = "CASHBACK_RECEIVED"

    def _schedule(self, exec_t, acc_id, amount, pid):
        i = bisect.bisect_right(self.pending_keys, exec_t)
        self.pending_keys.insert(i, exec_t)
        self.pending.insert(i, (exec_t, len(self.pending), acc_id, amount, pid))

    # ---- Level 1 ----
    def create_account(self, t, acc_id):
        self._advance(t)
        if acc_id in self.accts:
            return False
        self.accts[acc_id] = Account(t)
        return True

    def deposit(self, t, acc_id, amount):
        self._advance(t)
        a = self.accts.get(acc_id)
        if a is None:
            return None
        a.balance += amount
        a._record(t)
        return a.balance

    def transfer(self, t, src, dst, amount):
        self._advance(t)
        if src == dst:
            return None
        s = self.accts.get(src)
        d = self.accts.get(dst)
        if s is None or d is None or s.balance < amount:
            return None
        s.balance -= amount
        s.outgoing += amount
        s._record(t)
        d.balance += amount
        d._record(t)
        return s.balance

    # ---- Level 2 ----
    def top_spenders(self, t, n):
        self._advance(t)
        ranked = sorted(self.accts.items(), key=lambda kv: (-kv[1].outgoing, kv[0]))
        return [f"{aid}({a.outgoing})" for aid, a in ranked[:n]]

    # ---- Level 3 ----
    def pay(self, t, acc_id, amount):
        self._advance(t)
        a = self.accts.get(acc_id)
        if a is None or a.balance < amount:
            return None
        a.balance -= amount
        a.outgoing += amount
        a._record(t)
        self.payment_counter += 1
        pid = f"payment{self.payment_counter}"
        self.pay_status[pid] = "IN_PROGRESS"
        self.pay_owner[pid] = acc_id
        cashback = (amount * CASHBACK_RATE) // 100
        self._schedule(t + DAY, acc_id, cashback, pid)
        return pid

    def get_payment_status(self, t, acc_id, pid):
        self._advance(t)
        if acc_id not in self.accts or pid not in self.pay_status:
            return None
        if self.pay_owner.get(pid) != acc_id:
            return None
        return self.pay_status[pid]

    # ---- Level 4 ----
    def merge_accounts(self, t, id1, id2):
        self._advance(t)
        if id1 == id2:
            return False
        a1 = self.accts.get(id1)
        a2 = self.accts.get(id2)
        if a1 is None or a2 is None:
            return False
        a1.balance += a2.balance
        a1.outgoing += a2.outgoing
        a1._record(t)
        for pid, owner in self.pay_owner.items():
            if owner == id2:
                self.pay_owner[pid] = id1
        del self.accts[id2]
        return True

    def get_balance(self, t, acc_id, time_at):
        self._advance(t)
        a = self.accts.get(acc_id)
        if a is None or time_at < a.created:
            return None
        return a.balance_at(time_at)
'''

DAY = 86_400_000


# ------------------------------------------------------------------ Level 1
def l1_create(C):
    b = C()
    return [
        ("create A -> True", True, b.create_account(1, "A")),
        ("create A again -> False", False, b.create_account(2, "A")),
        ("create B -> True", True, b.create_account(3, "B")),
    ]


def l1_deposit(C):
    b = C()
    b.create_account(1, "A")
    return [
        ("deposit missing acct -> None", None, b.deposit(2, "Z", 50)),
        ("deposit A 100 -> 100", 100, b.deposit(3, "A", 100)),
        ("deposit A 50 -> 150", 150, b.deposit(4, "A", 50)),
    ]


def l1_transfer(C):
    b = C()
    b.create_account(1, "A")
    b.create_account(1, "B")
    b.deposit(2, "A", 100)
    return [
        ("self transfer -> None", None, b.transfer(3, "A", "A", 10)),
        ("missing source -> None", None, b.transfer(3, "Z", "A", 10)),
        ("missing target -> None", None, b.transfer(3, "A", "Z", 10)),
        ("insufficient funds -> None", None, b.transfer(3, "A", "B", 1000)),
        ("A->B 40 -> new balance 60", 60, b.transfer(4, "A", "B", 40)),
        ("B received (deposit 0 reads bal) -> 40", 40, b.deposit(5, "B", 0)),
    ]


# ------------------------------------------------------------------ Level 2
def l2_ranking(C):
    b = C()
    for a in ["A", "B", "C", "D"]:
        b.create_account(1, a)
    b.deposit(1, "A", 1000)
    b.deposit(1, "B", 1000)
    b.deposit(1, "C", 1000)
    b.transfer(2, "A", "B", 100)   # A out 100
    b.transfer(3, "B", "C", 300)   # B out 300
    b.transfer(4, "C", "A", 100)   # C out 100
    return [
        ("top 2 -> [B(300), A(100)]", ["B(300)", "A(100)"], b.top_spenders(5, 2)),
        (
            "top 10 (all; A,C tie broken by id, D last)",
            ["B(300)", "A(100)", "C(100)", "D(0)"],
            b.top_spenders(5, 10),
        ),
    ]


# ------------------------------------------------------------------ Level 3
def l3_pay_and_cashback(C):
    b = C()
    b.create_account(1, "A")
    b.deposit(1, "A", 1000)
    out = []
    pid = b.pay(2, "A", 100)          # 2% of 100 = 2, lands at 2 + DAY
    out.append(("pay returns payment1", "payment1", pid))
    out.append(("status IN_PROGRESS", "IN_PROGRESS", b.get_payment_status(3, "A", pid)))
    out.append(("balance after pay = 900", 900, b.deposit(4, "A", 0)))
    out.append(
        ("status after 24h -> CASHBACK_RECEIVED",
         "CASHBACK_RECEIVED", b.get_payment_status(2 + DAY, "A", pid))
    )
    out.append(("balance now 902 (cashback landed)", 902, b.deposit(2 + DAY + 1, "A", 0)))
    return out


def l3_status_ownership(C):
    b = C()
    b.create_account(1, "A")
    b.deposit(1, "A", 50)
    b.create_account(1, "B")
    pid = b.pay(2, "A", 50)           # cashback floor(50*2/100)=1
    return [
        ("pay ok -> payment1", "payment1", pid),
        ("status under wrong owner B -> None", None, b.get_payment_status(3, "B", pid)),
        ("status unknown pid -> None", None, b.get_payment_status(3, "A", "paymentX")),
        ("status under A -> IN_PROGRESS", "IN_PROGRESS", b.get_payment_status(3, "A", pid)),
        ("pay missing acct -> None", None, b.pay(4, "Z", 10)),
        ("pay insufficient -> None", None, b.pay(4, "A", 10_000)),
    ]


def l3_pay_counts_outgoing(C):
    b = C()
    b.create_account(1, "A")
    b.deposit(1, "A", 1000)
    b.create_account(1, "B")
    b.deposit(1, "B", 1000)
    b.transfer(2, "B", "A", 10)       # B out 10
    b.pay(3, "A", 100)                # A out 100
    return [("payments count as outgoing -> [A(100), B(10)]",
             ["A(100)", "B(10)"], b.top_spenders(4, 2))]


# ------------------------------------------------------------------ Level 4
def l4_merge_basic(C):
    b = C()
    b.create_account(1, "A")
    b.create_account(1, "B")
    b.deposit(1, "A", 100)
    b.deposit(1, "B", 50)
    b.transfer(2, "A", "B", 10)       # A bal 90 (out 10), B bal 60
    return [
        ("merge with missing id -> False", False, b.merge_accounts(3, "A", "Z")),
        ("merge id into itself -> False", False, b.merge_accounts(3, "A", "A")),
        ("merge B into A -> True", True, b.merge_accounts(3, "A", "B")),
        ("A balance combined -> 150", 150, b.deposit(4, "A", 0)),
        ("B removed: deposit B -> None", None, b.deposit(4, "B", 0)),
        ("outgoing combined -> [A(10)]", ["A(10)"], b.top_spenders(4, 5)),
    ]


def l4_cashback_after_merge(C):
    b = C()
    b.create_account(1, "A")
    b.create_account(1, "B")
    b.deposit(1, "B", 1000)
    pid = b.pay(2, "B", 100)          # B out 100, cashback 2 lands 2+DAY, owner B
    return [
        ("pay -> payment1", "payment1", pid),
        ("merge B into A -> True", True, b.merge_accounts(3, "A", "B")),
        ("A balance pre-cashback -> 900", 900, b.get_balance(3, "A", 3)),
        ("status under A after 24h -> CASHBACK_RECEIVED",
         "CASHBACK_RECEIVED", b.get_payment_status(2 + DAY, "A", pid)),
        ("A balance after cashback -> 902", 902, b.deposit(2 + DAY, "A", 0)),
        ("status under removed B -> None", None, b.get_payment_status(2 + DAY, "B", pid)),
    ]


def l4_balance_history(C):
    b = C()
    b.create_account(100, "A")
    b.deposit(200, "A", 100)          # bal 100 @200
    b.deposit(300, "A", 50)           # bal 150 @300
    return [
        ("as-of before created -> None", None, b.get_balance(400, "A", 50)),
        ("as-of created ts -> 0", 0, b.get_balance(400, "A", 100)),
        ("as-of 250 -> 100", 100, b.get_balance(400, "A", 250)),
        ("as-of 350 -> 150", 150, b.get_balance(400, "A", 350)),
        ("as-of missing acct -> None", None, b.get_balance(400, "Z", 350)),
    ]


def l4_balance_cashback_timing(C):
    b = C()
    b.create_account(1, "A")
    b.deposit(1, "A", 1000)
    b.pay(10, "A", 100)               # bal 900 @10, cashback 2 lands @10+DAY
    return [
        ("as-of just before cashback -> 900",
         900, b.get_balance(10 + DAY + 5, "A", 10 + DAY - 1)),
        ("as-of at cashback landing -> 902",
         902, b.get_balance(10 + DAY + 5, "A", 10 + DAY)),
    ]


LEVELS = [
    {"name": "Level 1 — Accounts & transfers",
     "tests": [l1_create, l1_deposit, l1_transfer]},
    {"name": "Level 2 — Ranking",
     "tests": [l2_ranking]},
    {"name": "Level 3 — Scheduled cashback",
     "tests": [l3_pay_and_cashback, l3_status_ownership, l3_pay_counts_outgoing]},
    {"name": "Level 4 — Merge & history",
     "tests": [l4_merge_basic, l4_cashback_after_merge,
               l4_balance_history, l4_balance_cashback_timing]},
]
