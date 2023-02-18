from flask import Flask,request,jsonify,session,abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from validate_email import validate_email
from flask_login import LoginManager,login_user,logout_user,UserMixin,current_user
from flask_jwt_extended import create_access_token,create_refresh_token,JWTManager,get_jwt_identity,jwt_required
import bcrypt
from flask_swagger_ui import get_swaggerui_blueprint
import os 
from faker import Faker
from itsdangerous import URLSafeTimedSerializer as Serializer
import secrets
from datetime import datetime



app=Flask(__name__)


SWAGGER_URL='/swagger'
API_URL='/static/swagger/swagger.json'
SWAGGER_BLUEPRINT=get_swaggerui_blueprint(
    SWAGGER_URL,API_URL,
    config={
        "app_name":"Ecommerce"
    }
)

app.register_blueprint(SWAGGER_BLUEPRINT)

app.config['SECRET_KEY']='uhdbxdsjwxwsdeewdxel'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///ecommerce.db'
app.config['JWT_SECRET_KEY']='jndwdcnjwejkweidjjkdb'
app.config['JWT_ACCESS_TOKEN_EXPIRES']=3600
db=SQLAlchemy(app)
migrate=Migrate(app,db)
login=LoginManager(app)
jwt=JWTManager(app)

@login.user_loader
def load_user(id):
    return User.query.get(id) 

class User(db.Model,UserMixin):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(20),unique=True,nullable=False)
    email=db.Column(db.String(20),unique=True,nullable=False)
    image=db.Column(db.String(20),nullable=True,default="default.jpg")
    password=db.Column(db.String(20),nullable=False)
    order_in_cart=db.relationship('Cart',backref='user',lazy=True)
    order_by_user=db.relationship('Order',backref="user_purchase",lazy=True)
    
    def __repr__(self):
        return f"user('{self.username},{self.email},{self.image}')"
    
    
    def reset_password(self):
        s=Serializer(app.config['SECRET_KEY'])
        user_id={"user_id":self.id}
        token=s.dumps(user_id)
        return token 
    
    @staticmethod
    def check_token(token):
        s=Serializer(app.config['SECRET_KEY'])
        try:
            user_id=s.loads(token)["user_id"]
        except:
            return None
        return User.query.get(user_id)
        
    
class Products(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    product_name=db.Column(db.String(20),nullable=False)
    product_image=db.Column(db.String(20),nullable=True,default="product.jpg")
    product_des=db.Column(db.Text,nullable=True)
    product_price=db.Column(db.Integer,nullable=False)
    quantity = db.Column(db.Integer, nullable=False,default=1)
    product_in_cart=db.relationship('Cart',backref='product',lazy=True)
    product_ordered=db.relationship('Order',backref='product_orders',lazy=True)
   
    @property
    def display_quantity(self):
       if self.quantity >0:
           return self.quantity
       else:
           return "Out of stock"
    
    
    def __repr__(self):
        return f"products('{self.id},{self.product_name},{self.product_price},{self.quantity}')"
    
class Cart(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id',ondelete='CASCADE'),nullable=False)
    product_id=db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'),nullable=False)
    quantity=db.Column(db.Integer,nullable=False,default=1)
    
    @property
    def display_cart_quantity(self):
        if self.product.quantity > 0:
            if self.product.quantity < self.quantity:
                 return f'only {self.product.quantity} is available'
            else:
                return self.quantity
        else:
            return "Out of stock"
    
    def __repr__(self):
        return f"Cart_items('{self.id},{self.user_id},{self.product_id}')"
    

class Order(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    payer_id=db.Column(db.String(25),nullable=False)
    payment_id=db.Column(db.String(20),nullable=False)
    quantity=db.Column(db.Integer,nullable=False,default=1)
    total_price=db.Column(db.Integer,nullable=False)
    ordered_date=db.Column(db.DateTime,nullable=False,default=datetime.utcnow())
    product_id=db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'),nullable=False)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),nullable=False)
   
    def __repr__(self):
        return f"Order_items('{self.id},{self.user_id},{self.product_id}')"
    

@app.route('/register',methods=['POST'])
def register():
    data=request.get_json()
    if 'username' not in data or 'email' not in data or 'password' not in data or 'confirm_password' not in data:
        return jsonify({"Error":"Username,email,password,confirm_password is required "}),400
    username=data.get('username')
    email=validate_email(data['email'])
    password=data['password']
    confirm_password=data['confirm_password']
    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"Error":"Username already exist"}),400
    if not email :
        return jsonify({"Error":"Enter valid email address"}),400
    if User.query.filter_by(email=data['email']).first() is not None:
        return jsonify({"Error":"Email already exist"}),400
    if password!=confirm_password:
        return jsonify({"Error":"Password doesnt match"}),400
    password_encrypted=bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())
    user=User(username=username,email=data['email'],password=password_encrypted.decode('utf-8'))
    db.session.add(user)
    db.session.commit()
    return jsonify({"success":"User registered successfully"}),201


@app.route('/login',methods=['POST'])
def login():
    print(current_user)
    data=request.get_json()
    if 'email' not in data or 'password' not in data:
        return jsonify({"Error":"Email and password is required"}),400
    email=validate_email(data['email'])
    password=data['password']
    if not email:
        return jsonify({"Error":"Enter valid email address"}),400
    user=User.query.filter_by(email=data['email']).first() 
    if user is None:
        return jsonify({"Error":"Email not yet registered "}),400
    if user and bcrypt.checkpw(password.encode('utf-8'),user.password.encode('utf-8')):
        login_user(user)
        access_token=create_access_token(identity=user.id)
        refresh_token=create_refresh_token(identity=user.id)
        print(current_user)
        return jsonify({"success":"login successful","access":access_token,"refresh":refresh_token}),200
    else:
        return jsonify({"Error":"Invalid credentials"}),400
    
    
@app.route('/profile',methods=['GET','POST'])
@jwt_required()
def profile():
    user_id=get_jwt_identity()
    user=User.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        username=request.form.get('username')
        email=request.form.get('email')
        image=request.files.get('image')
        if image:
            _,file_ext=os.path.splitext(image.filename)
            random_hex=secrets.token_hex(8)
            new_name=random_hex+file_ext
            path=os.path.join(app.root_path,'static/profile_images',new_name)
            image.save(path)
            user.image=new_name
        if username:
            if User.query.filter(username==username, username!=user.username).first() is not None:
                return jsonify('Username already exists')
            user.username=username
        if email:
            if not validate_email(email):
                return jsonify('Enter a valid email address')
            if User.query.filter(email==email, email!=user.email).first() is not None:
                return jsonify('Email already exists')
            user.email=email
        db.session.commit()
        return jsonify("Profile Updated successfully")
    else:
        order=Order.query.filter_by(user_id=user_id).all()
        orders=[]
        if order:         
            for i in order:
                orders.append({"Product Name":i.product_orders.product_name,"Product quantity":i.quantity,"Total Price":i.total_price,"Purchased Date":i.ordered_date.date()})
        return jsonify({"Username":user.username,"Email":user.email,"Image":user.image,"orders":orders})

@app.route('/products',methods=['GET','POST'])
def products():
    if request.method == 'POST':
        #data=request.get_json()
        product_name=request.form.get('product_name')
        product_image=request.files.get('product_image')
        product_des=request.form.get('product_des')
        product_price=request.form.get('product_price')
        product_quantity=request.form.get('product_quantity')
        try:
            if product_image:
                _, file_ext = os.path.splitext(product_image.filename)
                random_hex = secrets.token_hex(8)
                new_name = random_hex + file_ext
                path = os.path.join(app.root_path, 'static/product_images', new_name)
                product_image.save(path)
                product = Products(product_name=product_name, product_des=product_des, product_price=product_price, quantity=product_quantity, product_image=new_name)
            else:
                product = Products(product_name=product_name, product_des=product_des, product_price=product_price, quantity=product_quantity)
            db.session.add(product)
            db.session.commit()
            return jsonify('Product uploaded successfully!'), 200
        except:
               return jsonify('Error in uploading product.'), 500
    data=[]
    for i in Products.query.all():
        data.append({"product_id":i.id,"product name":i.product_name,"product_image":i.product_image,"product_des":i.product_des,"Product_price":i.product_price,"quantity":i.display_quantity})
    return jsonify({"Products":data})

@app.route('/addtocart/<int:id>',methods=['GET','POST'])
@jwt_required()
def addtocart(id):
    user_id=get_jwt_identity()
    product=Products.query.filter_by(id=id).first()
    if request.method=="POST":    
        if product:
            if product.quantity==0:
                return jsonify("Item out of stock."), 400
            if Cart.query.filter_by(user_id=user_id,product_id=product.id).first() is not None:
                return jsonify(f'Item {product.product_name} already exist in cart')
            else:
                data=request.get_json()  
                if 'quantity' not in data:
                    return jsonify('Please enter the quantity')
                if product.quantity< data['quantity']:
                    return jsonify(f'Sorry only {product.quantity} items left ')
                cart=Cart(user_id=user_id,product_id=product.id,quantity=data['quantity'])
                db.session.add(cart)
                db.session.commit()
                return jsonify(f'Item {product.product_name} successfully added to the cart'),201
        else:
            return jsonify('Item not found'),404
    else:
        if product:
            return jsonify({"Item":product.product_name,"Price":product.product_price,"quantity":product.display_quantity}),200
        else:
             return jsonify('Item not found'),404
         
@app.route('/viewcart',methods=['GET'])
@jwt_required()
def view():
    user_id=get_jwt_identity()
    cart=Cart.query.filter_by(user_id=user_id).all()
    data=[]
    total_items=0
    summation=0
    for i in cart:
        if i.quantity <= i.product.quantity:
            summation+=i.product.product_price * i.quantity
            total_items+=1
        data.append({"Product name":i.product.product_name,"product price":i.product.product_price,"quantity":i.display_cart_quantity})
    return jsonify({"Total items":total_items,"Total cost":summation,"Cart items":data}),200           
            
@app.route('/updatecart/<int:id>',methods=['GET','PUT','DELETE'])
@jwt_required()
def update(id):
    user_id=get_jwt_identity()
    cart=Cart.query.filter_by(id=id,user_id=user_id).first()
    if cart:
        if request.method=='GET':
                return jsonify({"Product name":cart.product.product_name,"Product price":cart.product.product_price,
                            "quantity":cart.display_cart_quantity}),200
        if request.method=='PUT':
            data=request.get_json()
            quantity=data['quantity']
            if quantity:
                if data['quantity']>cart.product.quantity:
                    if cart.product.quantity ==0:
                        return jsonify("Product out of stock")
                    return jsonify(f'only {cart.product.quantity} are available')
                cart.quantity=data['quantity']
                db.session.commit()
                return jsonify('Cart updated'),200
            else:
                return jsonify('enter the quantity')
        if request.method=='DELETE':
            db.session.delete(cart)
            db.session.commit()
            return jsonify("Item deleted from the cart "),200
    else:
        return jsonify('No item found'),404
    
    
    
    
#    checkout

import paypalrestsdk


paypalrestsdk.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": "AWgvI312oWhdxSzsiX2R4hWGxKCul1j-p8wFVr_TfdPWIXXUIYUUmFbM77HbqMSfdwQlP_tApK49MJJW",
  "client_secret": "EJlKLTDGswik54e_N6B4aQmunDgJOoYuwEGxW8A6KbIkhiyZiPc2Wvg937vAOtSHSQekrcR1eZlcGqel" })

@app.route("/cartpayment", methods=["GET"])
@jwt_required()
def create_payment():
    user_id=get_jwt_identity()
    cart_items=Cart.query.filter_by(user_id=user_id).all()
    if cart_items:
        items=[]
        total=0
        for i in cart_items:
            if i.quantity >i.product.quantity:
                if i.product.quantity==0:
                    return jsonify(f"Item {i.product.product_name} is out of stock ! Please remove the item from the cart and continue...")
                else:
                    return jsonify(f"Item {i.product.product_name} has {i.display_cart_quantity} ....")
            total+=i.product.product_price*i.quantity
            items.append({"name":i.product.product_name, "price":i.product.product_price, "quantity":i.quantity,"sku":str(i.product.id),"currency":"USD"})
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [
                {
                    "amount": {
                        "total": total,
                        "currency": "USD"
                    },
                    "custom": user_id,
                    "description": "Payment for Flask API",
                    "item_list": {
                    "items": items
                }
                }
            ],
            "redirect_urls": {
                "return_url": "http://127.0.0.1:5000/cartexecute",
                "cancel_url": "http://127.0.0.1:5000/payment/execute"
            }
        })

        if payment.create():
            for link in payment.links:
                if link.method == "REDIRECT":
                    return jsonify(link.href)
        else:
            return jsonify({"error": payment.error}), 400
    else:
        return jsonify({"error":"No items are available in cart"}), 400

@app.route("/cartexecute", methods=["GET"])
def execute_payment():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        for transaction in payment.transactions:
            for i in transaction['item_list']['items']:
              order=Order(payer_id=payer_id, payment_id=payment_id,user_id=payment.transactions[0].custom,product_id=i['sku'],quantity=i['quantity'],total_price=float(i['price'])*int(i['quantity']))
              db.session.add(order)
              db.session.commit()
        cart=Cart.query.filter_by(user_id=payment.transactions[0].custom).all()
        db.session.query(Cart).filter_by(user_id=payment.transactions[0].custom).delete()
        db.session.commit()
        return jsonify({"success": "payment success"}), 200
    else:
        return jsonify({"error": "payment failed"}), 400
    
    
@app.route("/productpayment/<int:id>", methods=["POST"])
@jwt_required()
def create_payment_product(id):
    data=request.get_json() 
    quantity=data.get('quantity', 1)
    user_id=get_jwt_identity()
    product=Products.query.filter_by(id=id).first()
    if product.quantity==0:
        return jsonify("Item out of Stock"), 400
    if product.quantity<quantity:
        return jsonify(f'Only {product.quantity} items are left.'), 400
    if product:
        total=product.product_price*quantity
        items = [
        {
            "name": product.product_name,
            "price": str(product.product_price),
            "currency": "USD",
            "sku": product.id,
            "quantity": quantity
        }
    ]
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [
                {
                    "amount": {
                        "total":total,
                        "currency": "USD"
                    },
                    "item_list": {
                    "items": items
                },
                    "custom": user_id,
                    "description": "Payment for Flask API",
                }
            ],
            "redirect_urls": {
                "return_url": "http://127.0.0.1:5000/productexecute",
                "cancel_url": "http://127.0.0.1:5000/payment/execute"
            }
        })

        if payment.create():
            for link in payment.links:
                if link.method == "REDIRECT":
                    return jsonify(link.href)
        else:
            return jsonify({"error": payment.error}), 400
    else:
        return jsonify({"error":"No products available"}), 400
    
    
@app.route("/productexecute", methods=["GET"])
def productexecute():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        for transaction in payment.transactions:
            for i in transaction['item_list']['items']:
              order=Order(payer_id=payer_id, payment_id=payment_id,user_id=payment.transactions[0].custom,product_id=i['sku'],quantity=i['quantity'],total_price=float(i['price'])*int(i['quantity']))
              db.session.add(order)
              db.session.commit()
        product=Products.query.filter_by(id=int(payment.transactions[0].item_list.items[0].sku)).first()
        value=product.quantity-int(payment.transactions[0].item_list.items[0].quantity)
        product.quantity=value
        db.session.commit()
        return jsonify({"success": "payment success"}), 200
    else:
        return jsonify({"error": "payment failed"}), 400
    
@app.route('/forgotpassword', methods=['POST'])
def resetpassword():
    data=request.get_json()
    email=data['email']
    if not validate_email(email):
        return jsonify("Enter a valid email address")
    user=User.query.filter_by(email=email).first()
    if user is None:
        return jsonify("Email not yet registered")
    link="http://127.0.0.1:5000/resetpassword/"+user.reset_password()
    print(link)
    return jsonify("A link has been sent to your registered email address to reset your password")

@app.route('/resetpassword/<token>', methods=['POST'])
def reset(token):
    data=request.get_json()
    pass1=data['password']
    pass2=data['confirm_password']
    if pass1==pass2:
        user=User.check_token(token)
        if user is None:
            return jsonify("Token maybe expired, please try again")
        else:
            password=bcrypt.hashpw(pass1.encode('utf-8'), bcrypt.gensalt())
            user.password = password.decode('utf-8')
            db.session.commit()
            return jsonify("Your password has been changed successfully")     
    else:
        return jsonify("Passwords do not match")
    
    
    

       
if __name__ == '__main__':
    app.run(debug=True)