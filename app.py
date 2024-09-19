import sqlite3 as sql
from flask import Flask, session, render_template, request, g, redirect, flash, jsonify, url_for
from flask_restful import Api, Resource
from flask_cors import CORS
import requests
import json
import os
from base64 import b64encode
from datetime import datetime
import random

app = Flask(__name__)
api = Api(app)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = os.urandom(24)



@app.before_request
def before_request():
    g.user = None
    g.cartdict = {}
    g.cats = getcategories()

    if "user_id" in session:

        g.user = {}
        con = sql.connect("store.db")
        con.row_factory = sql.Row
        cursor = con.cursor()
        cursor.execute("SELECT * FROM user WHERE user_id=?", (session["user_id"],))
        i = cursor.fetchone()
        g.user["user_id"] = i["user_id"]
        g.user["email"] = i["email"]
        g.user["mobile"] = i["mobile"]
        g.user["firstname"] = i["firstname"]
        g.user["lastname"] = i["lastname"]
        g.user["isadmin"] = i["isadmin"]
        
        cursor.execute("SELECT * FROM cart WHERE user_id=?", (session["user_id"],))
        result=cursor.fetchall()
        if len(result) == 0:
            pass
        else:
            for j in result:
                if j["product_id"] in g.cartdict:
                    old_qty=g.cartdict[j["product_id"]]
                    new_qty=j["qty"]+old_qty
                    g.cartdict[j["product_id"]]=new_qty
                else:
                    g.cartdict[j["product_id"]]=j["qty"]


# Page Routes

@app.route("/")
def home():
    p = requests.get("http://127.0.0.1:5000/product")
    products = p.content
    products = json.loads(products)
    random.shuffle(products)
    return render_template('index.html', products=products)

@app.route("/about.html")
def about():
    return render_template('about.html')

@app.route("/thankyou")
def thankyou():
    return render_template('thankyou.html')

@app.route("/login")
def login():
    if "user_id" in session:
        session.pop('user_id', None)
    return render_template('login.html')

@app.route("/register")
def register():
    return render_template('register.html')

@app.route("/profile")
def profile():
    if "user_id" in session:
        a = requests.get("http://127.0.0.1:5000/address", data=str(g.user['user_id']))
        addresses = a.content
        addresses = json.loads(addresses)
        return render_template('profile.html', addresses=addresses)
    else:
        return render_template('profile.html')

@app.route("/orders")
def orders():
    if "user_id" in session:
        a = requests.get("http://127.0.0.1:5000/order", data=str(g.user['user_id']))
        orders = a.content
        orders = json.loads(orders)
        return render_template('orders.html', orders=orders)
    else:
        return render_template('orders.html')

@app.route("/admin")
def admin():
    units=["Rs/unit", "Rs/Kg", "Rs/Litre", "Rs/dozen", "Rs/box"]
    cats = getcategories()
    p = requests.get("http://127.0.0.1:5000/product")
    products = p.content
    products = json.loads(products)
    shoptitle = "All Products"
    return render_template('admin.html', cats=cats, products=products,units=units, shoptitle=shoptitle)

@app.route("/adminbycategory", methods=['POST', 'GET'])
def adminbycategory():
    units=["Rs/unit", "Rs/Kg", "Rs/Litre", "Rs/dozen", "Rs/box"]
    cid = request.args["category_id"]
    p = requests.get(f"http://127.0.0.1:5000/product/category/{cid}")
    products = p.content
    products = json.loads(products)
    cats = getcategories()
    for i in cats:
        if i['category_id'] == int(cid):
            shoptitle = i['name']
    return render_template('admin.html', products=products, cats=cats, shoptitle=shoptitle, units=units)

@app.route("/shop", methods=['POST', 'GET'])
def shop():
    if request.method == 'POST':
        cats = getcategories()
        keyword = request.form['keyword']
        shoptitle = f"Search Result for {keyword}"
        keyword = "%" + keyword + "%"
        print(keyword)
        p = requests.get(f"http://127.0.0.1:5000/product/search/{keyword}")
        products = p.content
        products = json.loads(products)
        return render_template('shop.html', products=products, cats=cats, shoptitle=shoptitle)
    p = requests.get("http://127.0.0.1:5000/product")
    products = p.content
    products = json.loads(products)
    cats = getcategories()
    shoptitle = "Shop All"
    return render_template('shop.html', products=products, cats=cats, shoptitle=shoptitle)

@app.route("/shopbycategory", methods=['POST', 'GET'])
def shopbycategory():
    cid = request.args["category_id"]
    p = requests.get(f"http://127.0.0.1:5000/product/category/{cid}")
    products = p.content
    products = json.loads(products)
    cats = getcategories()
    for i in cats:
        if i['category_id'] == int(cid):
            shoptitle = i['name']
    return render_template('shop.html', products=products, cats=cats, shoptitle=shoptitle)

@app.route("/shop_single")
def shop_single():
    pid = request.args["product_id"]
    print(pid)
    p = requests.get( f"http://127.0.0.1:5000/product/{pid}")
    product = p.content
    product = json.loads(product)
    return render_template('shop-single.html', product=product)

@app.route("/cart", methods=['POST', 'GET'])
def cart():
    cart_products=[]
    subtotal=0
    gst = 0
    discount=0
    newtotal=0
    if "user_id" in session:
        a = requests.get("http://127.0.0.1:5000/address", data=str(g.user['user_id']))
        addresses = a.content
        addresses = json.loads(addresses)
        for product in g.cartdict:
            p = requests.get( f"http://127.0.0.1:5000/product/{product}")
            cart_products.append(json.loads(p.content))
        for product in cart_products:
            total = product['price']*g.cartdict[product['product_id']]
            subtotal = subtotal+total
        gst=round(0.18*subtotal,2)
        grandtotal=subtotal+gst
        grandtotal=round(grandtotal,2)
        if request.method == 'POST':
            code = request.form['code']
            if code == "NEW10":
                discount=round(0.1*grandtotal,2)
                newtotal=grandtotal-discount
                newtotal=round(newtotal,2)
                flash("Coupon Applied Sucessfully!")
            else:
                flash("Invalid Coupon Code! :(")
    else:
        flash("Please login to start shopping or view your existing cart!")
        return(redirect("/login"))
    return render_template('cart.html',cart_products=cart_products, subtotal=subtotal, gst=gst, grandtotal=grandtotal, addresses=addresses, discount=discount, newtotal=newtotal)

@app.route("/checkout",methods=['POST', 'GET'])
def checkout():
    cart_products=[]
    subtotal=0
    gst = 0
    discount=0
    newtotal=0
    if "user_id" in session:
        for product in g.cartdict:
            p = requests.get( f"http://127.0.0.1:5000/product/{product}")
            cart_products.append(json.loads(p.content))
        for product in cart_products:
            total = product['price']*g.cartdict[product['product_id']]
            subtotal = subtotal+total
        gst=round(0.18*subtotal,2)
        grandtotal=subtotal+gst
        grandtotal=round(grandtotal,2)
        if request.method == 'POST':
            aid = request.form['address']
            a = requests.get( f"http://127.0.0.1:5000/address/{aid}")
            address = json.loads(a.content)
            code = request.form['code1']
            if code == "NEW10":
                discount=round(0.1*grandtotal,2)
                newtotal=grandtotal-discount
                newtotal=round(newtotal,2)
                flash("Coupon Applied Sucessfully!")
            else:
                flash("Invalid Coupon Code! :(")
    else:
        flash("Please login to start shopping or view your existing cart!")
        return(redirect("/login"))
    return render_template('checkout.html',cart_products=cart_products, subtotal=subtotal, gst=gst, grandtotal=grandtotal, address=address, discount=discount, newtotal=newtotal)


# Functional Routes
@app.route("/placeorder", methods=['POST', 'GET'])
def placeorder():
    if request.method == 'POST':
        try:
            con = sql.connect("store.db")
            cursor = con.cursor()
            order = request.form.to_dict(flat=True)
            x=requests.post("http://127.0.0.1:5000/order", json=order)
            cursor.execute("SELECT order_id FROM orders where user_id=? ORDER BY order_id DESC LIMIT 1",(order['user_id'],))
            maxorder = cursor.fetchone()
            order_id = maxorder[0]
            print(order_id)
            for product in g.cartdict:
                qty= int(g.cartdict.get(product))
                cursor.execute("INSERT INTO order_item (order_id,product_id,quantity) VALUES (?,?,?)",(int(order_id),int(product),int(g.cartdict.get(product))))
                cursor.execute("SELECT stock from Products WHERE product_id=?",(int(product),))
                temp = cursor.fetchone()
                currentstock = temp[0]
                newstock = currentstock-qty
                cursor.execute("UPDATE Products SET stock=? WHERE product_id=?",(newstock,product))
                
            con.execute("DELETE from cart WHERE user_id = ?",(order['user_id'],))
            con.commit()
            msg = "Order Sucessfully Placed"

            print(msg)
        except:
            msg="Error, couldn't place order"
            print(msg)
        finally:
            return render_template("thankyou.html", order_id=order_id)
        
@app.route("/signuserup", methods=['POST', 'GET'])
def signuserup():
    if request.method == 'POST':
        try:
            user = request.form.to_dict(flat=True)
            requests.post("http://127.0.0.1:5000/newuser", json=user)
            msg = "User Sucessfully added"
            print(msg)
            flash("Sign Up sucessfull, Please login!")
        except:
            msg="Error, couldn't add new user"
            print(msg)
        finally:
            return redirect("/login")


@app.route("/loguserin", methods=['POST', 'GET'])
def loguserin():
    if "user_id" in session:
        session.pop('user_id', None)
        
    if request.method == 'POST':
        user={}
        # session.pop('user_id')
        username = request.form['username']
        password = request.form['pw']
        con = sql.connect("store.db")
        con.row_factory = sql.Row
        cursor = con.cursor()
        cursor.execute("SELECT * FROM user WHERE email=? and password=?", (username,password))
        results = cursor.fetchall()
        msg = "success"

        if len(results) == 0:
            flash("Sorry, Username or Password is incorrect. Try again!")
            return redirect("/login")
        else:
            for i in results:
                user["user_id"] = i["user_id"]
                user["email"] = i["email"]
                user["mobile"] = i["mobile"]
                user["firstname"] = i["firstname"]
                user["lastname"] = i["lastname"]
                user["isadmin"] = i["isadmin"]

            session["user_id"] = user["user_id"]
            print(user, session["user_id"])
            if user["isadmin"] == 1:
                return redirect("/admin")
            else:
                return redirect("/")

@app.route("/updatestock", methods=['POST', 'GET'])
def updatestock():
    if request.method == 'POST':
        try:
            product_id = request.form['product_id']
            stock = request.form['stock']
            print(product_id,stock)
            con =  sql.connect("store.db")
            cursor = con.cursor()
            cursor.execute("UPDATE Products SET stock=? WHERE product_id=?",(stock,product_id))
            con.commit()
            
            msg = "Product Stock updated Sucessfully"
            print(msg)

        except:
            msg="Error, couldn't update stock"
            flash(msg)
        finally:
            con.close()
            return redirect("/admin")
        
@app.route("/updatecat", methods=['POST', 'GET'])
def updatecat():
    if request.method == 'POST':
        try:
            category_id = request.form['category_id']
            name = request.form['name']
            con =  sql.connect("store.db")
            cursor = con.cursor()
            cursor.execute("UPDATE Category SET name=? WHERE category_id=?",(name,category_id))
            con.commit()
            
            msg = "Category updated Sucessfully"
            print(msg)

        except:
            msg="Error, couldn't update Category"
            print(msg)
            flash(msg)
        finally:
            con.close()
            return redirect("/admin")
        
@app.route("/updateproduct", methods=['POST', 'GET'])
def updateproduct():
    if request.method == 'POST':
        try:
            product = request.form.to_dict(flat=True)
            print(product)
            con =  sql.connect("store.db")
            cursor = con.cursor()
            cursor.execute("UPDATE Products SET name=?,price=?,mfg=?,exp=?,description=?,category_id=?,unit=? WHERE product_id=?",(product['name'],int(product['price']),product['mfg'],product['exp'],product['description'],int(product["category_id"]),product['unit'],int(product['product_id'])))
            con.commit()
            
            msg = "Product updated Sucessfully"
            print(msg)

        except:
            msg="Error, couldn't update product"
            con.rollback()
            print(msg)
            flash(msg)
        finally:
            con.close()
            return redirect("/admin")
        
@app.route("/updateuser", methods=['POST', 'GET'])
def updateuser():
    if request.method == 'POST':
        con =  sql.connect("store.db")
        try:
            user_id = g.user['user_id']
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            password = request.form['pw']
            mobile = request.form['mobile']
            print(user_id,firstname,lastname,password,mobile)
            cursor = con.cursor()
            cursor.execute("UPDATE user SET firstname=?,lastname=?,password=?,mobile=? WHERE user_id=?",(firstname,lastname,password,mobile,user_id,))
            con.commit()
            msg = "Profile updated Sucessfully, please login!"
            print(msg)

        except:
            msg="Error, couldn't update profile"
            print(msg)
        finally:
            con.close()
            return redirect("/profile")

cartid = None
@app.route("/addtocart", methods=['POST', 'GET'])
def addtocart():
    msg=""
    con =  sql.connect("store.db")
    cursor = con.cursor()
    date = datetime.now()
    date = date.strftime("%d/%m/%Y %H:%M:%S")
    if "user_id" not in session:
        flash("Please login to start shopping!")
        return(redirect("/login"))
    if request.method == 'POST':
        pid = request.form['product_id']
        pid = int(pid)
        cid = request.form['category_id']
        cid = int(cid)
        qty = request.form['qty']
        stock = request.form['stock']
        name = request.form['name']
        stock=int(stock)
        qty= int(qty)
        if pid in g.cartdict:
            temp = g.cartdict[pid]
            temp=int(temp)
            temp2 = temp+qty

            if temp2>3:
                msg="You cannot add more than 3 quantity for this product."
            elif temp2 <= 3 and temp2 <= stock:
                qty=temp2
                msg=f"Added {name} to cart"
                cursor.execute("UPDATE cart SET qty=? WHERE user_id=? AND product_id=?",(qty,g.user["user_id"],pid))
                con.commit()

            elif stock <= 3:
                qty=stock
                msg=f"Only {stock} {name} in stock"
                g.cartdict[pid] = qty
                cursor.execute("UPDATE cart SET qty=? WHERE user_id=? AND product_id=?",(qty,g.user["user_id"],pid))
                con.commit()

        else:
            if qty <= stock:
                msg=f"added {name} to cart"
                g.cartdict[pid] = qty
                cursor.execute("INSERT INTO cart (user_id,product_id,qty,category_id) VALUES (?,?,?,?)",(g.user["user_id"],pid,qty,cid))
                con.commit()
            elif qty >= stock:
                qty=stock
                msg=f"Only {stock} {name} in stock"
                g.cartdict[pid] = qty
                cursor.execute("INSERT INTO cart (user_id,product_id,qty,category_id) VALUES (?,?,?,?)",(g.user["user_id"],pid,qty,cid))
                con.commit()
        
        print(g.cartdict)
        flash(msg)
    return(redirect("/shop"))

@app.route("/deletecartproduct", methods=['POST', 'GET'])
def deletecartproduct():
    product_id = request.args['product_id']
    message={}
    try: 
        product_id=int(product_id)
        con = sql.connect("store.db")
        cursor = con.cursor()
        con.execute("DELETE from cart WHERE user_id=? AND product_id = ?",(g.user["user_id"],product_id,))
        con.commit()
        message["status"] = "Product deleted successfully"
    except:
        con.rollback()
        message["status"] = "Cannot delete Product"
    finally:
        con.close()

    return redirect("/cart")


@app.route("/addproduct", methods=['POST', 'GET'])
def addproduct():
    if request.method == 'POST':
        try:
            # Product Data add
            product = request.form.to_dict(flat=True)
            image_data = request.files['image'].read()
            # base64_string = base64.b64encode(image_data)
            # print(base64_string)
            # result["image"]= base64_string
            # print(result)
            #requests.post("http://127.0.0.1:5000/product", json=result)
            msg = "Product Successfully Added"
            print(msg)
            con = sql.connect("store.db")
            cursor = con.cursor()
            cursor.execute("INSERT INTO Products (name,price,mfg,exp,description,category_id,image,Unit,stock) VALUES (?,?,?,?,?,?,?,?,?)", (product['name'],product['price'],product['mfg'],product['exp'],product['description'],product["category_id"],image_data, product['unit'],product['stock']))
            con.commit() 

        except:
            msg="Error, couldn't add product"
            flash(msg)
        finally:
            con.close()
            return redirect("/admin")
        
@app.route("/delproduct", methods=['POST', 'GET'])
def delproduct():
    if request.method == 'POST':
        try:
            product_id = request.form['product_id']
            print(product_id)
            requests.delete("http://127.0.0.1:5000/product", data=product_id)
            msg = "Product Deleted Sucessfully"
            print(msg)

        except:
            msg="Error, couldn't delete product"
            flash(msg)
        finally:
            return redirect("/admin")
        
@app.route("/delcategory", methods=['POST', 'GET'])
def delcategory():
    if request.method == 'POST':
        try:
            category_id = request.form['category_id']
            print(category_id)
            requests.delete("http://127.0.0.1:5000/category", data=category_id)
            msg = "category Deleted Sucessfully"
            print(msg)

        except:
            msg="Error, couldn't delete product"
            flash(msg)
        finally:
            return redirect("/admin")

@app.route("/addcategory", methods=['POST', 'GET'])
def addcategory():
    if request.method == 'POST':
        try:
            category = request.form.to_dict(flat=True)
            requests.post("http://127.0.0.1:5000/category", json=category)
            msg = "Category Successfully Added"
            print(msg)

        except:
            msg="Error, couldn't add catrgory"
            flash(msg)

        finally:
            return redirect("/admin")

@app.route("/addaddress", methods=['POST', 'GET'])
def addaddress():
    if request.method == 'POST':
        try:
            user_id = request.form['user_id']
            mobile = request.form['mobile']
            address1 = request.form['address1']
            address2 = request.form['address2']
            state = request.form['state']
            city = request.form['city']
            pincode = request.form['pincode']
            addressfull = address1 + '\n' + address2 + '\n' + city + ', ' + state + ', ' + pincode
            print(addressfull)
            address = {}
            address['mobile'] = mobile
            address['address'] = addressfull
            address['user_id'] = int(user_id)
            address=json.dumps(address)
            requests.post("http://127.0.0.1:5000/address", json=address)
            msg = "Address Successfully Added"
            print(msg)

        except:
            msg="Error, couldn't add catrgory"
            flash(msg)

        finally:
            return redirect("/profile")
        
def getcategories():
    con = sql.connect("store.db")  
    con.row_factory = sql.Row

    cursor=con.cursor()

    cursor.execute("select * from category")

    cats=cursor.fetchall()

    return cats


# DB Functions for API
def place_order(order):
    date = datetime.now()
    date = date.strftime("%d/%m/%Y %H:%M:%S")
    message={}
    try:
        print(type(order['user_id']))
        con = sql.connect("store.db")
        con.execute("PRAGMA foreign_keys = ON")
        cursor = con.cursor()
        cursor.execute("INSERT INTO orders (user_id,created_at,subtotal,gst,grandtotal,discount,address,mobile,payable) VALUES (?,?,?,?,?,?,?,?,?)",(order['user_id'],str(date),order['subtotal'],order['gst'],order['grandtotal'],order['discount'],order['address'],order['mobile'],order['payable'],))
        

        con.commit()
        message["status"] = "successfully placed order"
    except:
        con.rollback()
        message["status"] = "Failed to place order"
    finally:
        print(message)
    return message

def get_orders(user_id):
    orders = []
    try:
        con = sql.connect("store.db")  
        con.row_factory = sql.Row
        cursor=con.cursor()

        cursor.execute("select * from orders where user_id=? ORDER BY order_id DESC",(user_id,))

        rows=cursor.fetchall()
        
        for i in rows:
            order = {}
            order["order_id"] = i["order_id"]
            order["status"] = i["status"]
            order["subtotal"] = i["subtotal"]
            order["gst"] = i["gst"]
            order["grandtotal"] = i["grandtotal"]
            order["discount"] = i["discount"]
            order["address"] = i["address"]
            order["mobile"] = i["mobile"]
            order["created_at"] = i["created_at"]
            order["payable"] = i["payable"]
            orders.append(order)
            
    except:
        orders = []

    return orders

def get_products():
    products=[]
    try:
        con = sql.connect("store.db")  
        con.row_factory = sql.Row

        cursor=con.cursor()

        cursor.execute("select * from products")

        rows=cursor.fetchall()
        for i in rows:
            product = {}
            product["product_id"] = i["product_id"]
            product["name"] = i["name"]
            product["price"] = i["price"]
            product["unit"] = i["Unit"]
            product["mfg"] = i["mfg"]
            product["exp"] = i["exp"]
            product["description"] = i["description"]
            product["discount"] = i["discount"]
            product["stock"] = i["stock"]
            product["category_id"] = i["category_id"]
            product["image"] = i["image"]
            product["image"] = b64encode(product['image']).decode("utf-8")
            products.append(product)
            
    except:
        products = []

    return products

def search_products(keyword):
    products=[]
    try:
        con = sql.connect("store.db")  
        con.row_factory = sql.Row

        cursor=con.cursor()

        cursor.execute("select * from products WHERE name LIKE ?", (keyword,))

        rows=cursor.fetchall()
        for i in rows:
            product = {}
            product["product_id"] = i["product_id"]
            product["name"] = i["name"]
            product["price"] = i["price"]
            product["unit"] = i["Unit"]
            product["mfg"] = i["mfg"]
            product["exp"] = i["exp"]
            product["description"] = i["description"]
            product["discount"] = i["discount"]
            product["stock"] = i["stock"]
            product["category_id"] = i["category_id"]
            product["image"] = i["image"]
            product["image"] = b64encode(product['image']).decode("utf-8")
            products.append(product)
            
    except:
        products = []

    return products

def get_product_by_category(category_id):
    products=[]
    try:
        con = sql.connect("store.db")  
        con.row_factory = sql.Row

        cursor=con.cursor()

        cursor.execute("select * from products WHERE category_id=?", (category_id,))

        rows=cursor.fetchall()
        for i in rows:
            product = {}
            product["product_id"] = i["product_id"]
            product["name"] = i["name"]
            product["price"] = i["price"]
            product["unit"] = i["Unit"]
            product["mfg"] = i["mfg"]
            product["exp"] = i["exp"]
            product["description"] = i["description"]
            product["discount"] = i["discount"]
            product["stock"] = i["stock"]
            product["category_id"] = i["category_id"]
            product["image"] = i["image"]
            product["image"] = b64encode(product['image']).decode("utf-8")
            products.append(product)
            
    except:
        products = []

    return products

def get_address(user_id):
    address_list=[]
    try:
        con = sql.connect("store.db")  
        con.row_factory = sql.Row

        cursor=con.cursor()

        cursor.execute("select * from address where user_id=?",(user_id,))

        rows=cursor.fetchall()
        for i in rows:
            address = {}
            address['address_id'] = i['address_id']
            address['Address'] = i['Address']
            address['mobile'] = i['mobile']
            address_list.append(address)
            
    except:
        address_list = []

    return address_list

def get_address_by_id(address_id):
    address={}
    try:
        con = sql.connect("store.db")  
        con.row_factory = sql.Row

        cursor=con.cursor()

        cursor.execute("select * from address where address_id=?",(address_id,))

        i=cursor.fetchone()
        address['address_id'] = i['address_id']
        address['Address'] = i['Address']
        address['mobile'] = i['mobile']
        
            
    except:
        address = {}

    return address

def add_user(user):
    message={}
    try:
        with sql.connect('store.db') as con:
            con.execute("PRAGMA foreign_keys = ON")
            cursor = con.cursor()

            cursor.execute("SELECT user_id FROM user ORDER BY user_id DESC LIMIT 1")

            maxuser = cursor.fetchone()
            user_id = maxuser[0]
            user_id = user_id+1


            cursor.execute("INSERT INTO user (user_id,firstname,lastname,email,password,mobile) VALUES (?,?,?,?,?,?)", (user_id,user["firstname"],user["lastname"],user["username"],user["pw"],user["mobile"]))

            con.commit()

            message["status"] = "User Added successfully"

            print(message["status"])
    except:
        con.rollback()
        message["status"] = "Failed to add User"
        
    finally:
        con.close()
        return message


def add_product(product):
    try:
        with sql.connect('store.db') as con:
            con.execute("PRAGMA foreign_keys = ON")

            cursor = con.cursor()

            cursor.execute("INSERT INTO Products (name,price,mfg,exp,description,category_id,Unit) VALUES (?,?,?,?,?,?,?)", (product['name'],product['price'],product['mfg'],product['exp'],product['description'],product["category_id"],product["unit"]))

            con.commit()

            msg = "Product Successfully Added"

            print(msg)

    except:
        con.rollback()
        msg="Error, couldn't add product"
        flash(msg)
    finally:
        con.close()
        return product
    
def add_address(address):
    print(address)
    try:
        with sql.connect('store.db') as con:
            con.execute("PRAGMA foreign_keys = ON")

            cursor = con.cursor()

            cursor.execute("INSERT INTO address (user_id, Address, mobile) VALUES (?,?,?)", (address['user_id'],address['address'],address['mobile'],))

            con.commit()

            msg = "Address Successfully Added"

            print(msg)

    except:
        con.rollback()
        msg="Error, couldn't add address"
        flash(msg)
    finally:
        con.close()
        print(msg)
        return msg

def add_category(category):
    try:
        with sql.connect('store.db') as con:

            cursor = con.cursor()

            cursor.execute("SELECT category_id FROM Category ORDER BY category_id DESC LIMIT 1")

            maxcat = cursor.fetchone()
            cat_id = maxcat[0]
            cat_id = cat_id+1
            cursor.execute("INSERT INTO Category (category_id, name) VALUES (?,?)", (cat_id, category['name'],))

            con.commit()

            msg = "Category Successfully Added"

            print(msg)

    except:
        con.rollback()
        msg="Error, couldn't add catrgory"
        flash(msg)
    finally:
        con.close()

def delete_product(product_id):
    message={}
    try: 
        product_id=int(product_id)
        con = sql.connect("store.db")
        cursor = con.cursor()
        con.execute("DELETE from products WHERE product_id = ?",(product_id,))
        con.execute("DELETE from cart WHERE product_id = ?",(product_id,))
        con.commit()
        message["status"] = "Product deleted successfully"
    except:
        con.rollback()
        message["status"] = "Cannot delete Product"
    finally:
        con.close()

    return message

def delete_category(category_id):
    message={}
    try: 
        con = sql.connect("store.db")
        cursor = con.cursor()
        con.execute("DELETE from category WHERE category_id = ?",(category_id,))
        con.execute("DELETE from products WHERE category_id = ?",(category_id,))
        con.execute("DELETE from cart WHERE category_id = ?",(category_id,))
        con.commit()
        message["status"] = "Category deleted successfully"
    except:
        con.rollback()
        message["status"] = "Cannot delete category"
    finally:
        con.close()

    return message

def get_product_by_id(product_id):
    product = {}
    try:
        con = sql.connect("store.db")
        con.row_factory = sql.Row
        cursor = con.cursor()
        cursor.execute("SELECT * FROM products WHERE product_id = ?", 
                       (product_id,))
        i = cursor.fetchone()
        product["product_id"] = i["product_id"]
        product["name"] = i["name"]
        product["price"] = i["price"]
        product["unit"] = i["Unit"]
        product["mfg"] = i["mfg"]
        product["exp"] = i["exp"]
        product["description"] = i["description"]
        product["discount"] = i["discount"]
        product["stock"] = i["stock"]
        product["category_id"] = i["category_id"]
        product["image"] = i["image"]
        product["image"] = b64encode(product['image']).decode("utf-8")
    except:
        product={}
    
    return product

# API's
class Product(Resource):
    def get(self):
        return jsonify(get_products())
    
    def post(self):
        product = request.get_json()
        return add_product(product)
    
    def delete(self):
        product_id = request.get_data(as_text=True)
        product_id = int(product_id)
        return jsonify(delete_product(product_id))

class Category(Resource):
    def post(self):
        Category = request.get_json()
        return add_category(Category)
    
    def delete(self):
        category_id = request.get_data(as_text=True)
        category_id = int(category_id)
        return jsonify(delete_category(category_id))

class Address(Resource):
    def post(self):
        address = request.get_json()
        address=json.loads(address)
        print(address['user_id'])
        return add_address(address)
    
    def get(self):
        user_id = request.get_data(as_text=True)
        user_id = int(user_id)
        return jsonify(get_address(user_id))

class Order(Resource):
    def post(self):
        order = request.get_json()
        return place_order(order)
    
    def get(self):
        user_id = request.get_data(as_text=True)
        user_id = int(user_id)
        return jsonify(get_orders(user_id))
        

    
@app.route('/product/<product_id>', methods=['GET'])
def api_get_product(product_id):
    return jsonify(get_product_by_id(product_id))

@app.route('/product/search/<keyword>', methods=['GET'])
def api_search_product(keyword):
    return jsonify(search_products(keyword))

@app.route('/product/category/<category_id>', methods=['GET'])
def api_product_category(category_id):
    category_id=int(category_id)
    return jsonify(get_product_by_category(category_id))

@app.route('/address/<address_id>', methods=['GET'])
def api_get_address(address_id):
    return jsonify(get_address_by_id(address_id))

@app.route('/newuser', methods=['POST'])
def api_add_user():
    user = request.get_json()
    return add_user(user)

api.add_resource(Product, '/product')
api.add_resource(Category, '/category')
api.add_resource(Address, '/address')
api.add_resource(Order, '/order')

if __name__ == "__main__":
    app.run() #run app