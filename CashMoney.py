from ofxtools.Parser import OFXTree
import os
import glob
import pandas as pd

statements_dir_fp = "statements/"
storage_dir_fp = "storage/"

account_name_map_fp = storage_dir_fp + "account_name_map.csv"
bucket_list_fp = storage_dir_fp + "bucket_list.csv"
bucket_transaction_map_fp = storage_dir_fp + "bucket_transaction_map.csv"

# PARSE ====================================================

ofx_parser = OFXTree()

for statement_fp in glob.glob(os.path.join(statements_dir_fp, "*.ofx")):
    with open(statement_fp, 'rb') as statement:
        ofx_parser.parse(statement)

ofx = ofx_parser.convert()

if len(ofx.statements) == 0:
    exit("No Statements Found")

statements = []

for statement in ofx.statements:

    r_statement = {"type": statement.account.accttype,
                   "account_num": int(statement.account.acctid),
                   "balance": statement.balance.balamt,
                   "transactions": []
                   }

    for transaction in statement.transactions:

        r_statement["transactions"].append({"type": transaction.trntype,
                                            "datetime": transaction.dtposted.year,
                                            "amount": transaction.trnamt,
                                            "name": transaction.name,
                                            "memo": transaction.memo
                                            })
    statements.append(r_statement)

# Map account_names to account_numbers ====================================================

try:
    account_name_map = pd.read_csv(account_name_map_fp)
except:
    account_name_map = pd.DataFrame(columns=["account_num", "account_name"])

account_nums = account_name_map["account_num"].to_list()
account_names = account_name_map["account_name"].to_list()

print(account_nums)

for statement in statements:
    if not statement["account_num"] in account_nums:
        account_names.append(input(f"Name account {statement["account_num"]}: "))
        account_nums.append(statement["account_num"])

account_name_map = pd.DataFrame({"account_num": account_nums,
                                 "account_name": account_names})

account_name_map.to_csv(account_name_map_fp)

# Define Buckets ====================================================
