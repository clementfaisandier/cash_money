# This CLI application is a personal finance app.

# It aims to fulfill the following features:
# 1. Parses Statements Automatically.
# 2. Allows the user to define "buckets"
#     Buckets are transaction categories from groceries, to investments.
#     Buckets have target for total value, or montly spendings.StopIteration
#     Buckets have rules that automatically sort transactions from statements into the appropriate bucket.
# 3. Charts bucket in/out and balance over time.
# 4. Describes how user spends their money

# These are the starting features for this applications, additional features will be:

# 5. Retirement plan modeling and comparison.
#     Enables user to simulate their income, investments, and retirement income/spending through various retirement plans (growing at average S&P 500 rate)
#         Roth/Tranditional 401k/IRA
#         ...

from ofxtools.Parser import OFXTree
import os
import glob
import pandas as pd
import json
from decimal import Decimal
import sys
from colorama import Fore
import msvcrt

statements_dir_fp = "statements/"
storage_dir_fp = "storage/"

account_name_map_fp = storage_dir_fp + "account_name_map.csv"
bucket_list_fp = storage_dir_fp + "bucket_list.json"
bucket_transaction_map_fp = storage_dir_fp + "bucket_transaction_map.csv"

# PARSE ====================================================

ofx_parser = OFXTree()

for statement_fp in glob.glob(os.path.join(statements_dir_fp, "*.ofx")):
    with open(statement_fp, 'rb') as account:
        ofx_parser.parse(account)

ofx = ofx_parser.convert()

if len(ofx.statements) == 0:
    exit("No Statements Found")

accounts = []
transactions = []

for account in ofx.statements:

    accounts.append({"type": account.account.accttype,
                   "account_num": int(account.account.acctid),
                   "balance": account.balance.balamt,
                   "transactions": []
                   })

    for transaction in account.transactions:
        transactions.append({"type": transaction.trntype,
                             "datetime": transaction.dtposted.year,
                             "amount": transaction.trnamt,
                             "id": transaction.fitid,
                             "name": transaction.name,
                             "memo": transaction.memo
                             })
        
accounts_df = pd.DataFrame(accounts)
transactions_df = pd.DataFrame(transactions)

# Map account_names to account_numbers ====================================================

try:
    account_name_map = pd.read_csv(account_name_map_fp)
    print("Found existing accounts.")
except:
    account_name_map = pd.DataFrame(columns=["account_num", "account_name"])
    print("No existing accounts found.")

account_nums = account_name_map["account_num"].to_list()
account_names = account_name_map["account_name"].to_list()

for account in accounts:
    if not account["account_num"] in account_nums:
        account_names.append(input(f"Name account {account["account_num"]}: "))
        account_nums.append(account["account_num"])

account_name_map = pd.DataFrame({"account_num": account_nums,
                                 "account_name": account_names})

account_name_map.to_csv(account_name_map_fp)
print("Accounts saved to storage.")

# Define Buckets ====================================================

# What is a bucket?
# A bucket is an allocation of funds.
# Buckets therefore have:
# key:Name
#     Description
#     Balance Amount
#     List of associated transactions
#         These transactions could be defined by:
#             Transaction ID
#             Name
#             Memo
#         Ideally, these entries can be used as regex functions.

# In the future they may also have:
#     Target Balance Amount
#     Target Spending Amount per period
#     Period Length

try:
    with open(bucket_list_fp, 'rt') as bucket_file:
        buckets = json.load(bucket_file)
        print("Found existing buckets.")
except:
    buckets = []
    print("No buckets found.")

buckets_df = pd.DataFrame(buckets)

if input(f"You have defined the following buckets:\n{buckets_df["name"]}\nWould you like to define new buckets?[y/(n)] ") == "y":
    print("Enter 'done' to exit:")
    while True:
        bucket_name = input("\tNew bucket name: ")
        if bucket_name == "done": break
        bucket_description = input("\tNew bucket description: ")
        if bucket_description == "done": break
        try:
            bucket_balance_in = input("\tBucket initial balance: ")
            bucket_balance = float(bucket_balance_in) # Wish this was decimal.
        except:
            if bucket_balance_in == "done": break
            print("\t\tNot a decimal amount, please try again.")
            continue
        buckets.append({"name": bucket_name,
                        "description": bucket_description,
                        "balance": bucket_balance,
                        "transaction_rules": []})
        print("\tBucket Saved.")

buckets_df = pd.DataFrame(buckets)

with open(bucket_list_fp, 'wt') as bucket_file:
    json.dump(buckets, bucket_file)
print("Buckets saved to storage dir.")

# Map transactions and buckets ====================================================

# Notes on Transactions, things that aren't self evident:
    
#     FITID is not standarized by ofx. It is used to identify duplicates and is defined by the financial institution. Note that depending on your institution, different transaction types may have different transaction ID formats. Hence I don't recommend using it.

#     NAME seems to always start with a description of the type of transaction, followed by the other account the transaction is with, followed by as much of the memo as can be included within character limits.

#         This is probably the field to use to map transactions and buckets etc.

#     MEMO seems to be the NAME plus the rest of the memo added by user.

#         This may be a better version of NAME if we care about the memo?

# First, we're gonna go through our transactions, and map all our transactions to a bucket.

transaction_to_match = {}

print("Matching bucket rules and transactions:")
for transaction in transactions:
    rule_match_count = 0
    for bucket in buckets:
        for rule in bucket["transaction_rules"]:
            if rule in transaction["name"]:
                if rule_match_count != 0:
                    print(f"\tTransaction rule conflict for transaction {transaction["name"]}: {transaction["bucket"]} vs {bucket["name"]}")
                transaction["bucket"] = bucket["name"] # TODO: do this at the end instead
                rule_match_count += 1
    
    transaction_to_match[transaction["name"]] = rule_match_count

transactions_df = pd.DataFrame(transactions)

# Now we're gonna prompt the user to generate bucket rules.

transaction_names = sorted(list(transaction_to_match.keys()))
filter = ""

print("Defining bucket rules.\n\n")
while True:
    count = 0
    for name in transaction_names:
        if filter in name:
            if transaction_to_match[name] == 0:
                print(Fore.YELLOW + name, end=" ")
            elif transaction_to_match[name] == 1:
                print(Fore.GREEN + name, end=" ")
            elif transaction_to_match[name] > 1:
                print(Fore.RED + name, end=" ")

            for i in range(34-len(name)):
                print(end=" ")
            
            if count == 3:
                print()
                count = 0
            else:
                print(end="   ")
                count += 1

    print(Fore.WHITE)

    index = 0
    for bucket in buckets:
        print(str(index) + ": " + bucket["name"], end="")
        for i in range(15-len(bucket["name"])-int(index/10)):
            print(end=" ")
        if index == 5:
            print()
        index += 1

    print("\n\nGreen means already in bucket, Yellow means not in a bucket, Red means in multiple buckets.")
    print("Available commands:")
    print("bucket_# ADD bucket_rule | bucket_# RM bucket_rule | FIND tentative_bucket_rule")

    cmd_str = input("What do you think? ")
    cmd = cmd_str.split(" ")

    if len(cmd) < 1:
        print("Invalid command")
        continue

    elif cmd[0] == "FIND":
        filter = cmd_str.strip().strip(cmd[0]).strip()
        continue

    elif cmd[0].isdigit():
        if len(cmd) < 3:
            print("Invalid command")
            continue
        rule = cmd_str.strip().strip(cmd[0]).strip().strip(cmd[1]).strip()

        change = 0

        if cmd[1] == "ADD":
            buckets[int(cmd[0])]["transaction_rules"].append(rule)
            change = 1
        elif cmd[1] == "RM":
            try:
                buckets[int(cmd[0])]["transaction_rules"].remove(rule)
                change = -1
            except: pass
        else:
            print("Invalid command.")
            continue

        for name in transaction_names:
            if rule in name:
                transaction_to_match[name] = transaction_to_match[name] + change

        continue
    
    elif cmd[0] == "DONE":
        for name in transaction_to_match:
            if transaction_to_match[name] != 1:
                print("Not all transaction are properly matched.")
                continue
        break

    elif cmd[0] == "SAVE":
        buckets_df = pd.DataFrame(buckets)
        with open(bucket_list_fp, 'wt') as bucket_file:
            json.dump(buckets, bucket_file)
        print("Bucket rules saved to storage dir.")
        continue
        
    else:
        print("Invalid command.")
        continue

buckets_df = pd.DataFrame(buckets)

with open(bucket_list_fp, 'wt') as bucket_file:
    json.dump(buckets, bucket_file)
print("Bucket rules saved to storage dir.")


print("Calculating bucket balances...")

for bucket in buckets:
    for rule in bucket["transaction_rules"]:
        for transaction in transactions:
            if rule in transaction["name"]:
                bucket["balance"] += float(transaction["amount"])
    
    print(f"{bucket["name"]} {bucket["balance"]}")


