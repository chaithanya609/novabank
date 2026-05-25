const express = require("express");
const mongoose = require("mongoose");
const bcrypt = require("bcryptjs");
const cors = require("cors");
const fs = require("fs");
const createCsvWriter =
require("csv-writer").createObjectCsvWriter;

const app = express();

app.use(cors());
app.use(express.json());

/* MongoDB Connection */

mongoose.connect("mongodb://127.0.0.1:27017/novabank")

.then(() => {

    console.log("MongoDB Connected");

})

.catch((err) => {

    console.log(err);

});

/* User Schema */

const userSchema = new mongoose.Schema({

    username:String,

    email:String,

    accountNumber:String,

    pin:String,

    password:String,

    balance:{
        type:Number,
        default:100000
    }

});

const User = mongoose.model("User", userSchema);

/* Transaction Schema */

const transactionSchema = new mongoose.Schema({

    accountNumber:String,

    type:String,

    amount:Number,

    receiver:String,

    balance:Number,

    date:{
        type:Date,
        default:Date.now
    }

});

const Transaction =
mongoose.model("Transaction", transactionSchema);

/* CSV Function */

async function updateCSV(accountNumber){

    const transactions =
    await Transaction.find({ accountNumber });

    const csvWriter = createCsvWriter({

        path:`${accountNumber}_transactions.csv`,

        header:[

            {id:"type",title:"TYPE"},

            {id:"amount",title:"AMOUNT"},

            {id:"receiver",title:"RECEIVER"},

            {id:"balance",title:"BALANCE"},

            {id:"date",title:"DATE"}

        ]

    });

    await csvWriter.writeRecords(transactions);

}

/* Signup API */

app.post("/signup", async (req,res) => {

    try{

        const {

            username,
            email,
            accountNumber,
            pin,
            password

        } = req.body;

        const existingUser =
        await User.findOne({ accountNumber });

        if(existingUser){

            return res.json({

                success:false,
                message:"Account already exists"

            });

        }

        const hashedPassword =
        await bcrypt.hash(password,10);

        const hashedPin =
        await bcrypt.hash(pin,10);

        const user = new User({

            username,
            email,
            accountNumber,
            pin:hashedPin,
            password:hashedPassword

        });

        await user.save();

        res.json({

            success:true,
            message:"Signup Successful"

        });

    }

    catch(error){

        console.log(error);

        res.json({

            success:false,
            message:"Signup Failed"

        });

    }

});

/* Login API */

app.post("/login", async (req,res) => {

    try{

        const {

            accountNumber,
            pin

        } = req.body;

        const user =
        await User.findOne({ accountNumber });

        if(!user){

            return res.json({

                success:false,
                message:"Account Not Found"

            });

        }

        const isMatch =
        await bcrypt.compare(pin,user.pin);

        if(!isMatch){

            return res.json({

                success:false,
                message:"Invalid PIN"

            });

        }

        res.json({

            success:true,

            user:{

                username:user.username,

                email:user.email,

                accountNumber:user.accountNumber,

                balance:user.balance

            }

        });

    }

    catch(error){

        console.log(error);

        res.json({

            success:false,
            message:"Login Failed"

        });

    }

});

/* Get User */

app.get("/user/:accountNumber",
async (req,res)=>{

    const user =
    await User.findOne({

        accountNumber:req.params.accountNumber

    });

    res.json(user);

});

/* Transaction API */

app.post("/transaction", async (req,res)=>{

    try{

        const {

            accountNumber,
            type,
            amount,
            receiver

        } = req.body;

        const user =
        await User.findOne({ accountNumber });

        if(!user){

            return res.json({

                message:"User Not Found"

            });

        }

        const amt = Number(amount);

        /* Deposit */

        if(type === "Deposit"){

            user.balance += amt;

        }

        /* Withdraw */

        else if(type === "Withdraw"){

            if(user.balance < amt){

                return res.json({

                    message:"Insufficient Balance"

                });

            }

            user.balance -= amt;

        }

        /* Transfer */

        else if(type === "Transfer"){

            const receiverUser =
            await User.findOne({

                accountNumber:receiver

            });

            if(!receiverUser){

                return res.json({

                    message:"Receiver Account Not Found"

                });

            }

            if(user.balance < amt){

                return res.json({

                    message:"Insufficient Balance"

                });

            }

            user.balance -= amt;

            receiverUser.balance += amt;

            await receiverUser.save();

        }

        await user.save();

        /* Save Transaction */

        const transaction = new Transaction({

            accountNumber,

            type,

            amount:amt,

            receiver:receiver || "",

            balance:user.balance

        });

        await transaction.save();

        /* Update CSV */

        await updateCSV(accountNumber);

        res.json({

            success:true,

            message:"Transaction Successful",

            balance:user.balance

        });

    }

    catch(error){

        console.log(error);

        res.json({

            success:false,

            message:"Transaction Failed"

        });

    }

});

/* Get Transactions */

app.get("/transactions/:accountNumber",
async (req,res)=>{

    const transactions =
    await Transaction.find({

        accountNumber:req.params.accountNumber

    }).sort({_id:-1});

    res.json(transactions);

});

/* Change PIN */

app.post("/change-pin", async(req,res)=>{

    try{

        const {

            accountNumber,
            oldPin,
            newPin

        } = req.body;

        const user =
        await User.findOne({ accountNumber });

        const isMatch =
        await bcrypt.compare(oldPin,user.pin);

        if(!isMatch){

            return res.json({

                success:false,

                message:"Old PIN Incorrect"

            });

        }

        const hashedPin =
        await bcrypt.hash(newPin,10);

        user.pin = hashedPin;

        await user.save();

        res.json({

            success:true,

            message:"PIN Changed Successfully"

        });

    }

    catch(error){

        console.log(error);

        res.json({

            success:false,

            message:"PIN Change Failed"

        });

    }

});

/* Server */

app.listen(5000, () => {

    console.log("Server Running on Port 5000");

});