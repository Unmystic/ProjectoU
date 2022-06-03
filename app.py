import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    db.execute("CREATE TABLE IF NOT EXISTS portfolio (user_id INTEGER, symbol TEXT NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash = cash[0]["cash"]
    #portf = db.execute("SELECT symbol, SUM(quantity) FROM buys WHERE user_id = ? ORDER BY symbol", session["user_id"])
    portf = db.execute("SELECT * FROM portfolio WHERE user_id = ? ORDER BY symbol", session["user_id"])
    symbols = db.execute("SELECT symbol FROM portfolio WHERE user_id = ? ORDER BY symbol", session["user_id"])
    currentprice = {}
    symlist = []
    for symbol in range(len(symbols)):
        symlist.append(symbols[symbol]["symbol"])

    for symbol in range(len(symlist)):
        quotes = lookup(symlist[symbol])
        currentprice[symlist[symbol]] = quotes["price"]

    activesumm = 0
    for symbol in range(len(portf)):
        x=portf[symbol]["symbol"]
        activesumm = activesumm + portf[symbol]["quantity"] * currentprice[x]

    total = usd(cash + activesumm)
    cash = usd(cash)



    return render_template("index.html", cash=cash, portf=portf, currentprice=currentprice, total=total ,usd=usd)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":

        return render_template("buy.html")

    else:

        if not request.form.get("symbol"):
            return apology("must provide symbol")

        if not request.form.get("shares"):
            return apology("must provide number of shares to buy")

        shares = request.form.get("shares", type=int)
        if not(isinstance(shares, int) and shares > 0):
            return apology("must enter whole positive number")

        symbol = request.form.get("symbol")

        if lookup(symbol) == None:
            return apology("Incorrect symbol")

        quotes = lookup(symbol)
        stockprice = quotes["price"]
        dealprice = stockprice * shares
        bal = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        balance = bal[0]["cash"]

        if dealprice > balance:
            return apology("Not enough money on your account")

        db.execute("CREATE TABLE IF NOT EXISTS buys (user_id INTEGER, username TEXT NOT NULL, symbol TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, summ REAL NOT NULL, time TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        db.execute("INSERT INTO buys (user_id, username, symbol, price, quantity, summ, time) VALUES(?, ?, ?, ?, ?, ?, ?)", session["user_id"], username, symbol, stockprice, shares, dealprice, dt_string )

        balance = balance - dealprice

        db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"] )

        db.execute("CREATE TABLE IF NOT EXISTS portfolio (user_id INTEGER, symbol TEXT NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
        portfolio = db.execute("SELECT * FROM portfolio WHERE user_id = ?", session["user_id"])
        InorNot = False
        for element in range(len(portfolio)):
            if symbol in portfolio[element].values():
                current = db.execute("SELECT quantity FROM portfolio WHERE symbol = ? AND user_id = ?", symbol, session["user_id"])
                current = current[0]["quantity"] + shares
                db.execute("UPDATE portfolio SET quantity = ? WHERE symbol = ? AND user_id = ?", current, symbol, session["user_id"])
                InorNot = True
                break

        if len(portfolio) < 1:
            db.execute("INSERT INTO portfolio (user_id, symbol, name, quantity) VALUES(?, ?, ?, ?)", session["user_id"], symbol, quotes["name"], shares )
            InorNot = True
        if InorNot == False:
            db.execute("INSERT INTO portfolio (user_id, symbol, name, quantity) VALUES(?, ?, ?, ?)", session["user_id"], symbol, quotes["name"], shares )


        db.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, username TEXT NOT NULL, deal TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, summ REAL NOT NULL, time TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
        db.execute("INSERT INTO history (user_id, username, deal, symbol, name, price, quantity, summ, time) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", session["user_id"], username, "BUY", symbol, quotes["name"], stockprice, shares, dealprice, dt_string )

        return redirect("/")



    # return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    db.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, username TEXT NOT NULL, deal TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, summ REAL NOT NULL, time TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")

    history = db.execute("SELECT * FROM history WHERE user_id = ?", session["user_id"])

    return render_template("history.html", history=history, usd=usd)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":

        return render_template("quote.html")

    else:

        if not request.form.get("symbol"):
            return apology("must provide symbol")

        symbol = request.form.get("symbol")


        if lookup(symbol) == None:
            return apology("Incorrect symbol")

        quotes = lookup(symbol)

        return render_template("quoted.html",quotes=quotes, usd=usd)



    #return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure username is unique
        us = db.execute("SELECT username FROM users")
        users = []
        for symbol in range(len(us)):
            users.append(us[symbol]["username"])

        if request.form.get("username") in users:
            return apology("username already exists")

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password")

        # Ensure password and confirmation matching
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match")

        password = request.form.get("password")
        username = request.form.get("username")
        hash = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)



        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    #return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "GET":

        symbols = db.execute("SELECT symbol FROM portfolio WHERE user_id = ? ORDER BY symbol", session["user_id"])

        symlist = []
        for s in range(len(symbols)):
            symlist.append(symbols[s]["symbol"])

        return render_template("sell.html", symlist=symlist)

    else:

        symbol = request.form.get("symbol")

        if not request.form.get("symbol"):
            return apology("must provide symbol")

        symbols = db.execute("SELECT symbol FROM portfolio WHERE user_id = ? ORDER BY symbol", session["user_id"])

        symlist = []
        for s in range(len(symbols)):
            symlist.append(symbols[s]["symbol"])

        if symbol not in symlist:
            return apology("Sorry, you dont have this stock")



        if not request.form.get("shares"):
            return apology("must provide number of shares to sell")

        shares = request.form.get("shares", type=int)
        if not(isinstance(shares, int) and shares > 0):
            return apology("must enter whole positive number")

        portQ = db.execute("SELECT quantity FROM portfolio WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        quantity = portQ[0]["quantity"]

        if shares > quantity:
            return apology("you dont own that much stoke")


        quotes = lookup(symbol)
        stockprice = quotes["price"]
        dealprice = stockprice * shares
        bal = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        balance = bal[0]["cash"]


        db.execute("CREATE TABLE IF NOT EXISTS sells (user_id INTEGER, username TEXT NOT NULL, symbol TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, summ REAL NOT NULL, time TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = username[0]["username"]
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        db.execute("INSERT INTO sells (user_id, username, symbol, price, quantity, summ, time) VALUES(?, ?, ?, ?, ?, ?, ?)", session["user_id"], username, symbol, stockprice, shares, dealprice, dt_string )

        balance = balance + dealprice

        db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"] )


        portfolio = db.execute("SELECT * FROM portfolio WHERE user_id = ?", session["user_id"])

        for element in range(len(portfolio)):
            if symbol in portfolio[element].values():
                current = db.execute("SELECT quantity FROM portfolio WHERE symbol = ? AND user_id = ?", symbol, session["user_id"])

                if current[0]["quantity"] == shares:
                    db.execute("DELETE FROM portfolio WHERE symbol = ? AND user_id = ?", symbol, session["user_id"])

                else:
                    current = current[0]["quantity"] - shares
                    db.execute("UPDATE portfolio SET quantity = ? WHERE symbol = ? AND user_id = ?", current, symbol, session["user_id"])

        db.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, username TEXT NOT NULL, deal TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, summ REAL NOT NULL, time TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
        db.execute("INSERT INTO history (user_id, username, deal, symbol, name, price, quantity, summ, time) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", session["user_id"], username, "SELL", symbol, quotes["name"], stockprice, shares, dealprice, dt_string )

        return redirect("/")

    #return apology("TODO")
