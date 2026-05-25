from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_mail import Mail, Message
from reportlab.pdfgen import canvas

import bcrypt
import random
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ==========================================
# EMAIL CONFIGURATION
# ==========================================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yourgmail@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'

mail = Mail(app)

otp_storage = {}

# ==========================================
# MONGODB CONNECTION
# ==========================================

#client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/"))
import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("mongodb+srv://cchaithanya651_db_user:tCt1RN73PO50hSbW@cluster0.mongodb.net/?retryWrites=true&w=majority")

client = MongoClient(MONGO_URI)

db = client["novabank"]

users = db["users"]
transactions = db["transactions"]
loans = db["loans"]
admins = db["admins"]

# ==========================================
# DEFAULT ADMINS
# ==========================================

if admins.count_documents({}) == 0:

    admins.insert_many([

        {
            "adminId": "admin",
            "password": "admin123",
            "role": "Super Admin"
        },

        {
            "adminId": "manager",
            "password": "manager123",
            "role": "Manager"
        }

    ])

# ==========================================
# SIGNUP API
# ==========================================

@app.route("/signup", methods=["POST"])
def signup():

    try:

        data = request.json

        username = data.get("username")
        email = data.get("email")
        accountNumber = data.get("accountNumber")
        pin = data.get("pin")
        password = data.get("password")

        if users.find_one({
            "accountNumber": accountNumber
        }):

            return jsonify({

                "success": False,
                "message": "Account already exists"

            })

        hashed_password = bcrypt.hashpw(

            password.encode("utf-8"),
            bcrypt.gensalt()

        )

        card_number = "".join(

            [str(random.randint(0,9))
            for i in range(16)]

        )

        cvv = random.randint(100,999)

        user = {

            "username": username,
            "email": email,
            "accountNumber": accountNumber,
            "pin": pin,
            "password": hashed_password,

            "balance": 1000000,
            "status": "Active",

            "upi_id": f"{username}@novabank",

            "card_number": card_number,
            "cvv": cvv,
            "expiry": "12/30"

        }

        users.insert_one(user)

        return jsonify({

            "success": True,
            "message": "Account Created Successfully"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# ADMIN LOGIN API
# ==========================================

@app.route("/admin-login", methods=["POST"])
def admin_login():

    try:

        data = request.json

        adminId = data.get("adminId")
        password = data.get("password")

        admin = admins.find_one({

            "adminId": adminId,
            "password": password

        })

        if not admin:

            return jsonify({

                "success": False,
                "message": "Invalid Admin Credentials"

            })

        return jsonify({

            "success": True,
            "message": "Admin Login Successful",
            "role": admin["role"]

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# USER LOGIN API
# ==========================================

@app.route("/login", methods=["POST"])
def login():

    try:

        data = request.json

        accountNumber = data.get("accountNumber")
        pin = data.get("pin")

        user = users.find_one({

            "accountNumber": accountNumber,
            "pin": pin

        })

        if not user:

            return jsonify({

                "success": False,
                "message": "Invalid Account Number or PIN"

            })

        if user.get("status") == "Frozen":

            return jsonify({

                "success": False,
                "message": "Account Frozen By Admin"

            })

        return jsonify({

            "success": True,
            "message": "Login Successful",

            "user": {

                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "accountNumber": user.get("accountNumber", ""),
                "balance": user.get("balance", 0),

                "upi_id": user.get("upi_id", ""),
                "card_number": user.get("card_number", ""),
                "cvv": user.get("cvv", ""),
                "expiry": user.get("expiry", "")

            }

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# GET USER API
# ==========================================

@app.route("/user/<accountNumber>", methods=["GET"])
def get_user(accountNumber):

    try:

        user = users.find_one({

            "accountNumber": accountNumber

        })

        if not user:

            return jsonify({

                "success": False,
                "message": "User Not Found"

            })

        return jsonify({

            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "balance": user.get("balance", 0),

            "upi_id": user.get("upi_id", ""),
            "card_number": user.get("card_number", ""),
            "cvv": user.get("cvv", ""),
            "expiry": user.get("expiry", ""),
            "status": user.get("status", "")

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# TRANSACTION API
# ==========================================

@app.route("/transaction", methods=["POST"])
def transaction():

    try:

        data = request.json

        accountNumber = data.get("accountNumber")
        txn_type = data.get("type")
        amount = int(data.get("amount"))
        receiver = data.get("receiver", "")

        user = users.find_one({

            "accountNumber": accountNumber

        })

        if not user:

            return jsonify({

                "success": False,
                "message": "User Not Found"

            })

        if user.get("status") == "Frozen":

            return jsonify({

                "success": False,
                "message": "Account Frozen"

            })

        # ======================================
        # DEPOSIT
        # ======================================

        if txn_type == "Deposit":

            users.update_one(

                {"accountNumber": accountNumber},

                {"$inc": {"balance": amount}}

            )

            transactions.insert_one({

                "accountNumber": accountNumber,
                "type": "Deposit",
                "amount": amount,
                "receiver": "",
                "status": "Successful",

                "description":
                f"Deposited ₹{amount}",

                "date": datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                )

            })

        # ======================================
        # WITHDRAW
        # ======================================

        elif txn_type == "Withdraw":

            if user["balance"] < amount:

                return jsonify({

                    "success": False,
                    "message": "Insufficient Balance"

                })

            users.update_one(

                {"accountNumber": accountNumber},

                {"$inc": {"balance": -amount}}

            )

            transactions.insert_one({

                "accountNumber": accountNumber,
                "type": "Withdraw",
                "amount": amount,
                "receiver": "",
                "status": "Successful",

                "description":
                f"Withdrawn ₹{amount}",

                "date": datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                )

            })

        # ======================================
        # TRANSFER
        # ======================================

        elif txn_type == "Transfer":

            receiver_user = users.find_one({

                "accountNumber": receiver

            })

            if not receiver_user:

                return jsonify({

                    "success": False,
                    "message": "Receiver Not Found"

                })

            if receiver_user.get("status") == "Frozen":

                return jsonify({

                    "success": False,
                    "message": "Receiver Account Frozen"

                })

            if user["balance"] < amount:

                return jsonify({

                    "success": False,
                    "message": "Insufficient Balance"

                })

            # Sender Balance Update

            users.update_one(

                {"accountNumber": accountNumber},

                {"$inc": {"balance": -amount}}

            )

            # Receiver Balance Update

            users.update_one(

                {"accountNumber": receiver},

                {"$inc": {"balance": amount}}

            )

            # Sender Transaction

            transactions.insert_one({

                "accountNumber": accountNumber,

                "type": "Transfer Sent",

                "amount": amount,

                "receiver": receiver,

                "status": "Successful",

                "description":
                f"Sent ₹{amount} to {receiver}",

                "date": datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                )

            })

            # Receiver Transaction

            transactions.insert_one({

                "accountNumber": receiver,

                "type": "Transfer Received",

                "amount": amount,

                "receiver": accountNumber,

                "status": "Successful",

                "description":
                f"Received ₹{amount} from {accountNumber}",

                "date": datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                )

            })

        else:

            return jsonify({

                "success": False,
                "message": "Invalid Transaction Type"

            })

        updated_user = users.find_one({

            "accountNumber": accountNumber

        })

        return jsonify({

            "success": True,

            "message": f"{txn_type} Successful",

            "updatedBalance":
            updated_user["balance"]

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# TRANSACTION HISTORY API
# ==========================================

@app.route("/transactions/<accountNumber>", methods=["GET"])
def get_transactions(accountNumber):

    try:

        txn_list = list(

            transactions.find({

                "accountNumber": accountNumber

            })

        )

        result = []

        for txn in txn_list:

            result.append({

                "type": txn.get("type", ""),
                "amount": txn.get("amount", 0),

                "receiver": txn.get(
                    "receiver", ""
                ),

                "status": txn.get(
                    "status",
                    "Successful"
                ),

                "description": txn.get(
                    "description",
                    ""
                ),

                "date": txn.get("date", "")

            })

        result.reverse()

        return jsonify(result)

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# APPLY LOAN API
# ==========================================

@app.route("/apply-loan", methods=["POST"])
def apply_loan():

    try:

        data = request.json

        loans.insert_one({

            "accountNumber": data["accountNumber"],
            "amount": data["amount"],
            "status": "Pending",

            "date": datetime.now().strftime(
                "%d-%m-%Y"
            )

        })

        return jsonify({

            "success": True,
            "message": "Loan Applied Successfully"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# APPROVE LOAN API
# ==========================================

@app.route("/approve-loan/<loan_id>", methods=["PUT"])
def approve_loan(loan_id):

    try:

        loan = loans.find_one({

            "_id": ObjectId(loan_id)

        })

        if not loan:

            return jsonify({

                "success": False,
                "message": "Loan Not Found"

            })

        users.update_one(

            {
                "accountNumber":
                loan["accountNumber"]
            },

            {
                "$inc": {
                    "balance":
                    int(loan["amount"])
                }
            }

        )

        loans.update_one(

            {
                "_id": ObjectId(loan_id)
            },

            {
                "$set": {
                    "status": "Approved"
                }
            }

        )

        return jsonify({

            "success": True,
            "message": "Loan Approved"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# FREEZE USER API
# ==========================================

@app.route("/freeze-user/<account>", methods=["PUT"])
def freeze_user(account):

    try:

        users.update_one(

            {"accountNumber": account},

            {"$set": {
                "status": "Frozen"
            }}

        )

        return jsonify({

            "success": True,
            "message": "User Frozen"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# ADD ADMIN API
# ==========================================

@app.route("/add-admin", methods=["POST"])
def add_admin():

    try:

        data = request.json

        admins.insert_one({

            "adminId": data["adminId"],
            "password": data["password"],
            "role": data["role"]

        })

        return jsonify({

            "success": True,
            "message": "Admin Added"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# ADMIN STATS API
# ==========================================

@app.route("/admin-stats")
def admin_stats():

    try:

        total_users = users.count_documents({})
        total_transactions = transactions.count_documents({})
        total_loans = loans.count_documents({})

        revenue = 0

        for txn in transactions.find():

            revenue += int(txn["amount"])

        return jsonify({

            "users": total_users,
            "transactions": total_transactions,
            "loans": total_loans,
            "revenue": revenue

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# ALL TRANSACTIONS API
# ==========================================

@app.route("/all-transactions")
def all_transactions():

    try:

        txn_list = list(transactions.find())

        result = []

        for txn in txn_list:

            result.append({

                "accountNumber":
                txn.get("accountNumber", ""),

                "type":
                txn.get("type", ""),

                "amount":
                txn.get("amount", 0),

                "status":
                txn.get("status", ""),

                "description":
                txn.get("description", ""),

                "date":
                txn.get("date", "")

            })

        result.reverse()

        return jsonify(result)

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# SEND OTP API
# ==========================================

@app.route("/send-otp", methods=["POST"])
def send_otp():

    try:

        data = request.json

        email = data["email"]

        otp = random.randint(100000,999999)

        otp_storage[email] = otp

        msg = Message(

            "NovaBank OTP Verification",

            sender="yourgmail@gmail.com",

            recipients=[email]

        )

        msg.body = f"Your OTP is {otp}"

        mail.send(msg)

        return jsonify({

            "success": True,
            "message": "OTP Sent"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# VERIFY OTP API
# ==========================================

@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    try:

        data = request.json

        email = data["email"]
        otp = int(data["otp"])

        if otp_storage.get(email) == otp:

            return jsonify({

                "success": True,
                "message": "OTP Verified"

            })

        return jsonify({

            "success": False,
            "message": "Invalid OTP"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# PDF STATEMENT API
# ==========================================

@app.route("/download-statement/<account>")
def download_statement(account):

    try:

        pdf = canvas.Canvas(f"{account}.pdf")

        pdf.drawString(
            220,
            800,
            "NovaBank Statement"
        )

        txns = transactions.find({

            "accountNumber": account

        })

        y = 760

        for txn in txns:

            line = f"{txn['date']} | {txn['description']}"

            pdf.drawString(50, y, line)

            y -= 25

        pdf.save()

        return send_file(

            f"{account}.pdf",

            as_attachment=True

        )

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    app.run(debug=True, port=5000)
