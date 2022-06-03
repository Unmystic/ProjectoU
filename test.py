import os

from cs50 import SQL
from helpers import apology, login_required, lookup, usd

db = SQL("sqlite:///finance.db")

#if not os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")

symbols = db.execute("SELECT symbol FROM portfolio WHERE user_id = 1 ORDER BY symbol")

symlist = []
for s in range(len(symbols)):
    symlist.append(symbols[s]["symbol"])
print(symlist)

for s in range(len(symlist)):
    print(symlist[s])
