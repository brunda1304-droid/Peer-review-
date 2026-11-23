"""
Bank Account Management System  (complete single-file version)

CO3 / CO4 : Customer / transaction data structures (list, dict, set, tuple),
            string operations (format, validate, search), CSV / JSON file
            handling with try/except
CO5       : Account hierarchy, inheritance and polymorphism

Run with:  python bank_management_system.py
"""

import csv
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime


# ===========================================================================
# Transaction
# ===========================================================================
class Transaction:
    _counter = 1000
    CSV_HEADER = ("txn_id", "type", "timestamp", "amount", "balance_after")  # tuple

    def __init__(self, txn_type, amount, balance_after, txn_id=None, timestamp=None):
        if txn_id is None:                      # brand-new transaction
            Transaction._counter += 1
            txn_id = f"TXN{Transaction._counter}"
        else:                                   # restored from a file
            if not (txn_id.startswith("TXN") and txn_id[3:].isdigit()):
                raise ValueError(f"Bad transaction id: {txn_id!r}")
            Transaction._counter = max(Transaction._counter, int(txn_id[3:]))
        self.txn_id = txn_id
        self.txn_type = txn_type
        self.amount = amount
        self.balance_after = balance_after
        self.timestamp = timestamp or datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # ---- conversion helpers for JSON / CSV ----
    def to_dict(self):
        return {"txn_id": self.txn_id, "type": self.txn_type, "timestamp": self.timestamp,
                "amount": self.amount, "balance_after": self.balance_after}

    @classmethod
    def from_dict(cls, d):
        return cls(d["type"], float(d["amount"]), float(d["balance_after"]),
                   txn_id=d["txn_id"], timestamp=d["timestamp"])

    def to_row(self):
        return (self.txn_id, self.txn_type, self.timestamp,
                f"{self.amount:.2f}", f"{self.balance_after:.2f}")

    def __str__(self):
        return (f"{self.txn_id:<8} | {self.txn_type:<14} | {self.timestamp:<19} | "
                f"{self.amount:>12.2f} | {self.balance_after:>12.2f}")


# ===========================================================================
# Customer
# ===========================================================================
class Customer:
    def __init__(self, customer_id, name, phone, email):
        self.customer_id = customer_id
        self.name = Customer.format_name(name)
        self.phone = phone.strip()
        self.email = email.strip().lower()

    # --- string operations ---
    @staticmethod
    def format_name(raw):
        """'  jOHN   doe ' -> 'John Doe'"""
        return " ".join(part.capitalize() for part in raw.split())

    @staticmethod
    def is_valid_name(name):
        return re.fullmatch(r"[A-Za-z ]{2,50}", name.strip()) is not None

    @staticmethod
    def is_valid_phone(phone):
        return re.fullmatch(r"[6-9][0-9]{9}", phone.strip()) is not None

    @staticmethod
    def is_valid_email(email):
        return re.fullmatch(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}", email.strip()) is not None

    def masked_phone(self):
        """9876543210 -> XXXXXX3210"""
        return "XXXXXX" + self.phone[-4:]

    # --- conversion helpers for JSON ---
    def to_dict(self):
        return {"customer_id": self.customer_id, "name": self.name,
                "phone": self.phone, "email": self.email}

    @classmethod
    def from_dict(cls, d):
        """Rebuild a customer from saved data, rejecting bad values."""
        if not (cls.is_valid_name(d["name"]) and cls.is_valid_phone(d["phone"])
                and cls.is_valid_email(d["email"])):
            raise ValueError(f"Invalid customer data for {d['customer_id']}")
        return cls(d["customer_id"], d["name"], d["phone"], d["email"])

    def __str__(self):
        return f"{self.customer_id} | {self.name} | {self.masked_phone()} | {self.email}"


# ===========================================================================
# Account : abstract base class
# ===========================================================================
class Account(ABC):
    def __init__(self, account_number, owner, opening_balance, history=None):
        self.account_number = account_number
        self.owner = owner
        self._balance = opening_balance
        if history is not None:                 # restored from a file
            self.history = list(history)
        else:                                   # new account
            self.history = []
            if opening_balance > 0:
                self.history.append(Transaction("OPENING", opening_balance, self._balance))

    # ---- behaviour shared by all accounts ----
    @property
    def balance(self):
        return self._balance

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self._balance += amount
        self.history.append(Transaction("DEPOSIT", amount, self._balance))

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if not self.can_withdraw(amount):
            raise ValueError(self.withdraw_rule())
        self._balance -= amount
        self.history.append(Transaction("WITHDRAWAL", amount, self._balance))

    def transfer_out(self, amount):
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if not self.can_withdraw(amount):
            raise ValueError(self.withdraw_rule())
        self._balance -= amount
        self.history.append(Transaction("TRANSFER-OUT", amount, self._balance))

    def transfer_in(self, amount):
        self._balance += amount
        self.history.append(Transaction("TRANSFER-IN", amount, self._balance))

    def get_statement(self):
        line = "-" * 75
        out = ["\n" + "=" * 28 + " ACCOUNT STATEMENT " + "=" * 28,
               f"Account No : {self.account_number}",
               f"Type       : {self.account_type()}",
               f"Holder     : {self.owner.name}",
               line,
               f"{'TxnID':<8} | {'Type':<14} | {'Date/Time':<19} | {'Amount':>12} | {'Balance':>12}",
               line]
        if not self.history:
            out.append("No transactions yet.")
        else:
            out.extend(str(t) for t in self.history)
        out.append(line)
        out.append(f"Current Balance: {self._balance:.2f}")
        return "\n".join(out)

    def to_dict(self):
        return {"account_number": self.account_number,
                "type": self.account_type(),
                "customer_id": self.owner.customer_id,
                "balance": self._balance,
                "history": [t.to_dict() for t in self.history]}

    # ---- behaviour each subclass defines differently (polymorphism) ----
    @abstractmethod
    def can_withdraw(self, amount):
        """Can this amount be withdrawn under the account's rules?"""

    @abstractmethod
    def withdraw_rule(self):
        """Message shown when the withdrawal rule is violated."""

    @abstractmethod
    def month_end_process(self):
        """Interest for savings, service fee for current."""

    @abstractmethod
    def account_type(self):
        """Name of the account type."""

    def __str__(self):
        return (f"{self.account_number:<12} | {self.account_type():<8} | "
                f"{self.owner.name:<20} | {self._balance:>12.2f}")


# ===========================================================================
# SavingsAccount : minimum balance + interest
# ===========================================================================
class SavingsAccount(Account):
    MIN_BALANCE = 500.0
    ANNUAL_INTEREST_RATE = 4.0  # percent

    def __init__(self, account_number, owner, opening_balance, history=None):
        if history is None and opening_balance < self.MIN_BALANCE:
            raise ValueError(
                f"Savings account needs a minimum opening balance of {self.MIN_BALANCE}")
        super().__init__(account_number, owner, opening_balance, history)

    def can_withdraw(self, amount):
        return (self._balance - amount) >= self.MIN_BALANCE

    def withdraw_rule(self):
        return (f"Withdrawal denied: Savings account must keep a minimum "
                f"balance of {self.MIN_BALANCE}")

    def month_end_process(self):
        interest = self._balance * (self.ANNUAL_INTEREST_RATE / 12) / 100
        self._balance += interest
        self.history.append(Transaction("INTEREST", interest, self._balance))
        return f"{self.account_number}: interest of {interest:.2f} credited."

    def account_type(self):
        return "SAVINGS"


# ===========================================================================
# CurrentAccount : overdraft facility + monthly service fee
# ===========================================================================
class CurrentAccount(Account):
    OVERDRAFT_LIMIT = 10000.0
    MONTHLY_FEE = 100.0

    def can_withdraw(self, amount):
        return (self._balance - amount) >= -self.OVERDRAFT_LIMIT

    def withdraw_rule(self):
        return f"Withdrawal denied: overdraft limit of {self.OVERDRAFT_LIMIT} exceeded."

    def month_end_process(self):
        self._balance -= self.MONTHLY_FEE
        self.history.append(Transaction("SERVICE-FEE", self.MONTHLY_FEE, self._balance))
        return f"{self.account_number}: monthly fee of {self.MONTHLY_FEE:.2f} charged."

    def account_type(self):
        return "CURRENT"


# ===========================================================================
# Bank : data structures + business operations
# ===========================================================================
# dict used as a factory: type name -> class
ACCOUNT_TYPES = {"SAVINGS": SavingsAccount, "CURRENT": CurrentAccount}
TYPE_CODES = {"S": "SAVINGS", "C": "CURRENT"}


class Bank:
    def __init__(self):
        self.accounts = {}    # account number -> Account
        self.customers = {}   # customer id    -> Customer
        self._phones = set()  # phone numbers already registered
        self._emails = set()  # email addresses already registered
        self._account_seq = 1
        self._customer_seq = 1

    def register(self, name, phone, email, acc_type, opening_balance):
        """Validate everything, then create a customer and an account together."""
        code = acc_type.strip().upper()
        if code not in TYPE_CODES:
            raise ValueError("Account type must be S or C.")
        if not Customer.is_valid_name(name):
            raise ValueError("Invalid name (letters and spaces only).")
        if not Customer.is_valid_phone(phone):
            raise ValueError("Invalid phone number (10 digits, starts with 6-9).")
        if not Customer.is_valid_email(email):
            raise ValueError("Invalid email address.")
        if opening_balance < 0:
            raise ValueError("Opening balance cannot be negative.")
        if phone.strip() in self._phones:
            raise ValueError("A customer with this phone number already exists.")
        if email.strip().lower() in self._emails:
            raise ValueError("A customer with this email already exists.")

        customer = Customer(f"CUST{self._customer_seq:03d}", name, phone, email)
        acc_no = f"{TYPE_CODES[code][:3]}{self._account_seq:06d}"
        account = ACCOUNT_TYPES[TYPE_CODES[code]](acc_no, customer, opening_balance)

        # everything succeeded - commit
        self._customer_seq += 1
        self._account_seq += 1
        self.customers[customer.customer_id] = customer
        self.accounts[acc_no] = account
        self._phones.add(customer.phone)
        self._emails.add(customer.email)
        return customer, account   # tuple

    def find_account(self, acc_no):
        account = self.accounts.get(acc_no.strip().upper())
        if account is None:
            raise KeyError(f"Account not found: {acc_no}")
        return account

    def transfer(self, from_no, to_no, amount):
        if from_no.strip().upper() == to_no.strip().upper():
            raise ValueError("Cannot transfer to the same account.")
        source = self.find_account(from_no)
        target = self.find_account(to_no)
        source.transfer_out(amount)  # raises if rules are violated, so target is untouched
        target.transfer_in(amount)

    def search_customers(self, keyword):
        """Case-insensitive partial match on customer name."""
        key = keyword.strip().lower()
        return [c for c in self.customers.values() if key in c.name.lower()]

    def run_month_end(self):
        """Polymorphism in action: same call, different behaviour per account type."""
        return [acc.month_end_process() for acc in self.accounts.values()]

    # ---- conversion for JSON storage ----
    def to_dict(self):
        return {"customer_seq": self._customer_seq,
                "account_seq": self._account_seq,
                "customers": [c.to_dict() for c in self.customers.values()],
                "accounts": [a.to_dict() for a in self.accounts.values()]}

    def from_dict(self, data):
        """Rebuild the bank from saved data. Raises KeyError / ValueError / TypeError
        on bad data and leaves the current bank untouched in that case."""
        customers = {}
        for item in data["customers"]:
            c = Customer.from_dict(item)
            customers[c.customer_id] = c

        accounts = {}
        for item in data["accounts"]:
            cls = ACCOUNT_TYPES[item["type"]]
            owner = customers[item["customer_id"]]
            history = [Transaction.from_dict(t) for t in item["history"]]
            acc = cls(item["account_number"], owner, float(item["balance"]), history=history)
            accounts[acc.account_number] = acc

        customer_seq = int(data["customer_seq"])
        account_seq = int(data["account_seq"])

        # all good - replace current state
        self.customers = customers
        self.accounts = accounts
        self._phones = {c.phone for c in customers.values()}
        self._emails = {c.email for c in customers.values()}
        self._customer_seq = customer_seq
        self._account_seq = account_seq


# ===========================================================================
# File storage : JSON + CSV with error handling
# ===========================================================================
ACCOUNT_CSV_HEADER = ("account_no", "type", "customer_id", "holder", "balance")      # tuple
IMPORT_CSV_COLUMNS = ("name", "phone", "email", "type", "opening_balance")           # tuple


class StorageError(Exception):
    """Raised with a user-friendly message when a file operation fails."""


# ---- JSON : save / load the whole bank ----
def save_json(bank, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(bank.to_dict(), f, indent=2)
    except FileNotFoundError:
        raise StorageError(f"Folder does not exist for '{path}'.")
    except PermissionError:
        raise StorageError(f"Permission denied while writing '{path}'.")
    except OSError as e:
        raise StorageError(f"Could not write '{path}': {e}")


def load_json(bank, path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise StorageError(f"File not found: '{path}'.")
    except PermissionError:
        raise StorageError(f"Permission denied while reading '{path}'.")
    except json.JSONDecodeError as e:
        raise StorageError(f"'{path}' is not valid JSON (line {e.lineno}, column {e.colno}).")
    except UnicodeDecodeError:
        raise StorageError(f"'{path}' is not a text file.")
    except OSError as e:
        raise StorageError(f"Could not read '{path}': {e}")

    try:
        bank.from_dict(data)
    except KeyError as e:
        raise StorageError(f"'{path}' is missing data or has an unknown value: {e}")
    except (ValueError, TypeError) as e:
        raise StorageError(f"'{path}' contains bad data: {e}")


# ---- CSV : export accounts / transactions ----
def _write_csv(path, header, rows):
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    except FileNotFoundError:
        raise StorageError(f"Folder does not exist for '{path}'.")
    except PermissionError:
        raise StorageError(f"Permission denied while writing '{path}' (is it open in Excel?).")
    except OSError as e:
        raise StorageError(f"Could not write '{path}': {e}")
    return len(rows)


def export_accounts_csv(bank, path):
    rows = [(a.account_number, a.account_type(), a.owner.customer_id,
             a.owner.name, f"{a.balance:.2f}") for a in bank.accounts.values()]
    return _write_csv(path, ACCOUNT_CSV_HEADER, rows)


def export_transactions_csv(bank, path):
    header = ("account_no",) + Transaction.CSV_HEADER      # tuple concatenation
    rows = [(a.account_number,) + t.to_row()
            for a in bank.accounts.values() for t in a.history]
    return _write_csv(path, header, rows)


# ---- CSV : import new customers + accounts ----
def import_accounts_csv(bank, path):
    """Create accounts from a CSV with columns: name, phone, email, type, opening_balance.
    Bad rows are skipped and reported. Returns (created_count, list_of_error_messages)."""
    created = 0
    errors = []
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise StorageError(f"'{path}' is empty.")
            reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
            missing = [c for c in IMPORT_CSV_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise StorageError(f"'{path}' is missing column(s): {', '.join(missing)}")

            for line_no, row in enumerate(reader, start=2):   # line 1 is the header
                if any(row.get(c) is None or not row[c].strip() for c in IMPORT_CSV_COLUMNS):
                    errors.append(f"Row {line_no}: one or more values are missing.")
                    continue
                try:
                    opening = float(row["opening_balance"])
                except ValueError:
                    errors.append(f"Row {line_no}: opening_balance must be a number.")
                    continue
                try:
                    bank.register(row["name"], row["phone"], row["email"],
                                  row["type"], opening)
                    created += 1
                except ValueError as e:
                    errors.append(f"Row {line_no}: {e}")
    except FileNotFoundError:
        raise StorageError(f"File not found: '{path}'.")
    except PermissionError:
        raise StorageError(f"Permission denied while reading '{path}'.")
    except UnicodeDecodeError:
        raise StorageError(f"'{path}' is not a valid UTF-8 text file.")
    except csv.Error as e:
        raise StorageError(f"'{path}' is not a valid CSV file: {e}")
    except OSError as e:
        raise StorageError(f"Could not read '{path}': {e}")
    return created, errors     # tuple


# ===========================================================================
# Console menu
# ===========================================================================
bank = Bank()


def print_menu():
    print("\n-------------- MENU --------------")
    print(" 1. Create new account")
    print(" 2. Deposit")
    print(" 3. Withdraw")
    print(" 4. Transfer")
    print(" 5. Check balance")
    print(" 6. Account statement")
    print(" 7. Search customer by name")
    print(" 8. List all accounts")
    print(" 9. Run month-end processing")
    print("10. Save data to JSON")
    print("11. Load data from JSON")
    print("12. Export accounts to CSV")
    print("13. Export transactions to CSV")
    print("14. Import accounts from CSV")
    print(" 0. Exit")


def ask_file(label, default):
    name = input(f"{label} [{default}]: ").strip()
    return name or default


def create_account():
    name = input("Customer name: ")
    phone = input("Phone (10 digits): ")
    email = input("Email: ")
    acc_type = input("Account type (S = Savings, C = Current): ")
    opening = float(input("Opening balance: "))
    customer, account = bank.register(name, phone, email, acc_type, opening)
    print("Account created successfully!")
    print(f"Customer ID : {customer.customer_id}")
    print(f"Account No  : {account.account_number} ({account.account_type()})")


def deposit():
    acc = bank.find_account(input("Account number: "))
    acc.deposit(float(input("Amount to deposit: ")))
    print(f"Deposit successful. New balance: {acc.balance:.2f}")


def withdraw():
    acc = bank.find_account(input("Account number: "))
    acc.withdraw(float(input("Amount to withdraw: ")))
    print(f"Withdrawal successful. New balance: {acc.balance:.2f}")


def transfer():
    src = input("From account: ")
    dst = input("To account: ")
    amount = float(input("Amount: "))
    bank.transfer(src, dst, amount)
    print("Transfer successful.")


def check_balance():
    acc = bank.find_account(input("Account number: "))
    print(f"Balance for {acc.account_number} ({acc.owner.name}): {acc.balance:.2f}")


def statement():
    acc = bank.find_account(input("Account number: "))
    print(acc.get_statement())


def search_customer():
    found = bank.search_customers(input("Enter name or part of name: "))
    if not found:
        print("No matching customers.")
    else:
        print("Matches:")
        for c in found:
            print("  " + str(c))


def list_accounts():
    if not bank.accounts:
        print("No accounts yet.")
        return
    print(f"{'Account No':<12} | {'Type':<8} | {'Holder':<20} | {'Balance':>12}")
    print("-" * 62)
    for acc in bank.accounts.values():
        print(acc)


def month_end():
    if not bank.accounts:
        print("No accounts to process.")
        return
    print("Month-end processing:")
    for line in bank.run_month_end():
        print("  " + line)


def do_save_json():
    path = ask_file("JSON file to save", "bank_data.json")
    save_json(bank, path)
    print(f"Saved {len(bank.accounts)} account(s) to '{path}'.")


def do_load_json():
    path = ask_file("JSON file to load", "bank_data.json")
    load_json(bank, path)
    print(f"Loaded {len(bank.accounts)} account(s) from '{path}'.")


def do_export_accounts():
    path = ask_file("CSV file to write", "accounts.csv")
    count = export_accounts_csv(bank, path)
    print(f"Exported {count} account(s) to '{path}'.")


def do_export_transactions():
    path = ask_file("CSV file to write", "transactions.csv")
    count = export_transactions_csv(bank, path)
    print(f"Exported {count} transaction(s) to '{path}'.")


def do_import_accounts():
    path = ask_file("CSV file to import", "new_accounts.csv")
    created, errors = import_accounts_csv(bank, path)
    print(f"Imported {created} account(s) from '{path}'.")
    if errors:
        print(f"{len(errors)} row(s) skipped:")
        for e in errors:
            print("  " + e)


def main():
    print("=" * 39)
    print("   BANK ACCOUNT MANAGEMENT SYSTEM")
    print("=" * 39)

    actions = {
        "1": create_account, "2": deposit, "3": withdraw, "4": transfer,
        "5": check_balance, "6": statement, "7": search_customer,
        "8": list_accounts, "9": month_end,
        "10": do_save_json, "11": do_load_json, "12": do_export_accounts,
        "13": do_export_transactions, "14": do_import_accounts,
    }

    while True:
        print_menu()
        choice = input("Enter choice: ").strip()
        if choice == "0":
            break
        action = actions.get(choice)
        if action is None:
            print("Invalid choice. Try again.")
            continue
        try:
            action()
        except ValueError as e:
            print(f"Error: {e}")
        except KeyError as e:
            print(f"Error: {e.args[0] if e.args else e}")
        except StorageError as e:
            print(f"File error: {e}")
    print("Thank you for banking with us. Goodbye!")


if __name__ == "__main__":
    main()
