from flask import Flask, jsonify, request
from flaskext.mysql import MySQL
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import traceback

app = Flask(__name__)
CORS(app)

# ---------- MYSQL CONFIG ----------
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'food_delivery'

mysql = MySQL()
mysql.init_app(app)

# ---------- ENSURE DEFAULT ADMIN ----------
def ensure_admin_account():
    try:
        conn = mysql.connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM admins WHERE email=%s", ("admin@foodiego.com",))
        if not cur.fetchone():
            hashed = generate_password_hash("Admin@123")
            cur.execute(
                "INSERT INTO admins (name,email,password) VALUES (%s,%s,%s)",
                ("FoodieGo Admin", "admin@foodiego.com", hashed)
            )
            conn.commit()
            print("✅ Admin created → admin@foodiego.com / Admin@123")
        cur.close()
        conn.close()
    except:
        traceback.print_exc()

ensure_admin_account()

# ---------- ADMIN LOGIN ----------
@app.route('/login/admin', methods=['POST'])
def admin_login():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"message": "Email and password required"}), 400

    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute("SELECT id,name,password FROM admins WHERE email=%s", (data['email'],))
    admin = cur.fetchone()
    cur.close()
    conn.close()

    if admin and check_password_hash(admin[2], data['password']):
        return jsonify({"id": admin[0], "name": admin[1], "role": "admin"})
    return jsonify({"message": "Invalid admin credentials"}), 401

# ---------- CUSTOMER AUTH ----------
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data:
        return jsonify({"message": "JSON body required"}), 400

    required_fields = ['name','email','password']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM customers WHERE email=%s", (data['email'],))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"message": "Email exists"}), 409

    hashed = generate_password_hash(data['password'])
    cur.execute(
        "INSERT INTO customers (name,email,password) VALUES (%s,%s,%s)",
        (data['name'], data['email'], hashed)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Registered"}), 201

@app.route('/login/customer', methods=['POST'])
def customer_login():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"message": "Email and password required"}), 400

    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute("SELECT id,name,password FROM customers WHERE email=%s", (data['email'],))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and check_password_hash(user[2], data['password']):
        return jsonify({"id": user[0], "name": user[1], "role": "customer"})
    return jsonify({"message": "Invalid credentials"}), 401

# ---------- FOODS ----------
@app.route('/foods', methods=['GET', 'POST'])
def foods():
    conn = mysql.connect()
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute("SELECT id,name,price,image FROM foods")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{"id":r[0],"name":r[1],"price":r[2],"image":r[3]} for r in rows])

    data = request.json
    required_fields = ['name','price']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    cur.execute(
        "INSERT INTO foods (name,price,image) VALUES (%s,%s,%s)",
        (data['name'], data['price'], data.get('image',''))
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Food added"}), 201

# ---------- USERS (ADMIN) ----------
@app.route('/users', methods=['GET'])
def get_users():
    conn = mysql.connect()
    cur = conn.cursor()
    cur.execute("SELECT id,name,email FROM customers")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"id":r[0],"name":r[1],"email":r[2],"role":"customer"} for r in rows])

@app.route('/users/<int:user_id>', methods=['PUT', 'DELETE'])
def manage_user(user_id):
    conn = mysql.connect()
    cur = conn.cursor()
    data = request.json if request.method == 'PUT' else {}

    if request.method == 'PUT':
        if not data or 'name' not in data:
            return jsonify({"message": "Name is required"}), 400
        cur.execute("UPDATE customers SET name=%s WHERE id=%s", (data['name'], user_id))
        conn.commit()

    if request.method == 'DELETE':
        cur.execute("DELETE FROM customers WHERE id=%s", (user_id,))
        conn.commit()

    cur.close()
    conn.close()
    return jsonify({"message": "Success"})

# ---------- ADDRESSES ----------
@app.route('/addresses', methods=['GET', 'POST'])
def addresses():
    conn = mysql.connect()
    cur = conn.cursor()
    
    try:
        if request.method == 'GET':
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"message": "user_id is required"}), 400
            
            cur.execute("""
                SELECT id,address_line,city,postal_code,phone,is_default
                FROM addresses WHERE user_id=%s
            """, (int(user_id),))
            rows = cur.fetchall()
            return jsonify([{
                "id": r[0],
                "address_line": r[1],
                "city": r[2],
                "postal_code": r[3],
                "phone": r[4],
                "is_default": r[5]
            } for r in rows])
        
        # POST logic remains same
        if request.method == 'POST':
            data = request.get_json()
            cur.execute("""
                INSERT INTO addresses (user_id,address_line,city,postal_code,phone,is_default)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                int(data['user_id']), data['address_line'], data['city'],
                data['postal_code'], data['phone'], data.get('is_default', 0)
            ))
            conn.commit()
            return jsonify({"message": "Address added"}), 201
    except Exception as e:
        print("Error:", e)
        return jsonify({"message": str(e)}), 500
    finally:
        cur.close()
        conn.close()




# ---------- ORDERS ----------
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    conn = mysql.connect()
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute("""
            SELECT o.id,c.name,f.name,oi.quantity,o.status
            FROM orders o
            JOIN customers c ON o.user_id=c.id
            JOIN order_items oi ON o.id=oi.order_id
            JOIN foods f ON oi.food_id=f.id
            ORDER BY o.id DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{
            "order_id": r[0],
            "customer": r[1],
            "food": r[2],
            "quantity": r[3],
            "status": r[4]
        } for r in rows])

    # POST request
    data = request.json
    required_fields = ['user_id','address_id','items']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    cur.execute(
        "INSERT INTO orders (user_id,address_id,status) VALUES (%s,%s,'pending')",
        (data['user_id'], data['address_id'])
    )
    order_id = cur.lastrowid

    for i in data['items']:
        if 'id' not in i or 'quantity' not in i:
            continue
        cur.execute(
            "INSERT INTO order_items (order_id,food_id,quantity) VALUES (%s,%s,%s)",
            (order_id, i['id'], i['quantity'])
        )

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Order created"}), 201

@app.route('/orders/<int:order_id>', methods=['PUT', 'DELETE'])
def update_order(order_id):
    conn = mysql.connect()
    cur = conn.cursor()
    data = request.json if request.method == 'PUT' else {}

    if request.method == 'PUT':
        if 'status' in data:
            cur.execute("UPDATE orders SET status=%s WHERE id=%s", (data['status'], order_id))
        if 'food_id' in data and 'quantity' in data:
            cur.execute("""
                UPDATE order_items SET food_id=%s,quantity=%s WHERE order_id=%s
            """, (data['food_id'], data['quantity'], order_id))
        conn.commit()

    if request.method == 'DELETE':
        cur.execute("DELETE FROM order_items WHERE order_id=%s", (order_id,))
        cur.execute("DELETE FROM orders WHERE id=%s", (order_id,))
        conn.commit()

    cur.close()
    conn.close()
    return jsonify({"message": "Order updated"})

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
