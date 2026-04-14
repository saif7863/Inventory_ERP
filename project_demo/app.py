import pandas as pd
from datetime import datetime
from flask import Flask,render_template,request,redirect,send_file,session
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


'''FOR DATA_BASE'''
import sqlite3
app=Flask(__name__)
app.secret_key = "erp_secret_123"
def init_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            supplier TEXT NOT NULL,
            created_date TEXT NOT NULL
        )
    """)

    # Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            sale_date TEXT NOT NULL
        )
    """)

        
    conn.commit()
    conn.close()
init_db()
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "1234":
            session["user"] = username
            session["role"] = "admin"
            return redirect("/")

        elif username == "staff" and password == "1111":
            session["user"] = username
            session["role"] = "staff"
            return redirect("/")

        return "Invalid username or password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

@app.route("/", methods=["GET", "POST"])
def home():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    if "user" not in session:
        return redirect("/login")

    # add product
    if request.method == "POST":
        product_name = request.form["product_name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        buy_price = request.form["buy_price"]
        sell_price = request.form["sell_price"]
        supplier = request.form["supplier"]
        created_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO products
            (product_name, category, quantity, buy_price, sell_price, supplier,created_date)
            VALUES (?, ?, ?, ?, ?, ?,?)
        """, (
            product_name,
            category,
            quantity,
            buy_price,
            sell_price,
            supplier,
            created_date
        ))

        conn.commit()
        conn.close()
        return redirect("/")


    # 🔥 search logic
    search = request.args.get("search")

    if search and search.strip() != "":
        cursor.execute("""
            SELECT * FROM products
            WHERE LOWER(product_name) LIKE LOWER(?)
            OR LOWER(category) LIKE LOWER(?)
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    # total products count
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    # total stock quantity
    cursor.execute("SELECT SUM(quantity) FROM products")
    total_stock = cursor.fetchone()[0]

    # low stock count
    cursor.execute("SELECT COUNT(*) FROM products WHERE quantity <= 5")
    low_stock_count = cursor.fetchone()[0]
    cursor.execute("""
        SELECT SUM((sell_price - buy_price) * quantity)
        FROM products
    """)
    profit = cursor.fetchone()[0]

    if profit is None:
        profit = 0
    current_date = datetime.now().strftime("%d-%m-%Y")

    conn.close()

    return render_template(
        "index.html",
        products=products,
        total_products=total_products,
        total_stock=total_stock,
        low_stock_count=low_stock_count,
        current_date = current_date,
        profit = profit
    )


@app.route("/delete/<int:id>")
def delete_product(id):
    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM products WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    if request.method == "POST":
        quantity = request.form["quantity"]
        buy_price = request.form["buy_price"]
        sell_price = request.form["sell_price"]
        supplier = request.form["supplier"]

        cursor.execute(
            "UPDATE products SET quantity = ? WHERE id = ?",
            (quantity, id)
        )
        cursor.execute("UPDATE products SET buy_price = ? WHERE id = ?",
                       (buy_price, id))
        cursor.execute("UPDATE products SET sell_price = ? WHERE id = ?",(sell_price, id))
        cursor.execute("UPDATE products SET supplier = ? WHERE id = ?",(supplier,id))

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute("SELECT * FROM products WHERE id = ?", (id,))
    product = cursor.fetchone()

    conn.close()

    return render_template("edit.html", product=product)


@app.route("/stock_in/<int:id>")
def stock_in(id):

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE products
        SET quantity = quantity + 1
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/stock_out/<int:id>")
def stock_out(id):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # get current quantity
    cursor.execute(
        "SELECT quantity FROM products WHERE id = ?",
        (id,)
    )
    current_qty = cursor.fetchone()[0]

    # only reduce if greater than 0
    if current_qty > 0:
        cursor.execute("""
            UPDATE products
            SET quantity = quantity - 1
            WHERE id = ?
        """, (id,))
        conn.commit()

    conn.close()

    return redirect("/")
@app.route("/export")
def export_excel():
    conn = sqlite3.connect("inventory.db")

    query = "SELECT * FROM products"
    df = pd.read_sql_query(query, conn)

    file_name = "inventory_report.xlsx"
    df.to_excel(file_name, index=False)

    conn.close()

    return send_file(
        file_name,
        as_attachment=True
    )
@app.route("/products", methods=["GET", "POST"])
def products_page():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    if request.method == "POST":
        product_name = request.form["product_name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        buy_price = request.form["buy_price"]
        sell_price = request.form["sell_price"]
        supplier = request.form["supplier"]
        created_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO products
            (product_name, category, quantity, buy_price, sell_price, supplier, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_name,
            category,
            quantity,
            buy_price,
            sell_price,
            supplier,
            created_date
        ))

        conn.commit()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    conn.close()

    return render_template("products.html", products=products)

@app.route("/invoice", methods=["GET", "POST"])
def invoice():
    if "user" not in session:
        return redirect("/login")

    invoice_data = None

    if request.method == "POST":
        customer_name = request.form["customer_name"]
        product_name = request.form["product_name"]
        quantity = int(request.form["quantity"])
        rate = float(request.form["rate"])
        invoice_date = datetime.now().strftime("%d-%m-%Y")

        total = quantity * rate

        invoice_data = {
            "customer_name": customer_name,
            "product_name": product_name,
            "quantity": quantity,
            "rate": rate,
            "invoice_date": invoice_date,
            "total": total
        }

    return render_template("invoice.html", invoice=invoice_data)
@app.route("/download_invoice", methods=["POST"])
def download_invoice():
    customer_name = request.form["customer_name"]
    product_name = request.form["product_name"]
    quantity = int(request.form["quantity"])
    rate = float(request.form["rate"])
    invoice_date = datetime.now().strftime("%d-%m-%Y")
    total = quantity * rate

    file_name = "invoice.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(200, 800, "Beverage ERP Invoice")

    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Date: {invoice_date}")
    c.drawString(100, 720, f"Customer: {customer_name}")
    c.drawString(100, 690, f"Product: {product_name}")
    c.drawString(100, 660, f"Quantity: {quantity}")
    c.drawString(100, 630, f"Rate: ₹ {rate}")
    c.drawString(100, 600, f"Total: ₹ {total}")

    c.save()

    return send_file(file_name, as_attachment=True)

@app.route("/forgot_password")
def forgot_password():
    return "Please contact admin to reset your password"

@app.route("/sales", methods=["GET", "POST"])
def sales():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    if request.method == "POST":
        customer_name = request.form["customer_name"]
        product_name = request.form["product_name"]
        quantity = int(request.form["quantity"])

        cursor.execute(
            "SELECT quantity, sell_price FROM products WHERE LOWER(product_name) LIKE LOWER(?)",
            (f"%{product_name}%",)
        )
        product = cursor.fetchone()
        print("Fetched product:", product)

        if product:
            current_stock = product[0]
            sell_price = product[1]

            if current_stock >= quantity:
                total = quantity * sell_price
                invoice_no = "INV" + datetime.now().strftime("%H%M%S")
                sale_date = datetime.now().strftime("%Y-%m-%d")

                cursor.execute("""
                    INSERT INTO sales
                    (invoice_no, customer_name, product_name, quantity, price, total, sale_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_no,
                    customer_name,
                    product_name,
                    quantity,
                    sell_price,
                    total,
                    sale_date
                ))

                cursor.execute("""
                    UPDATE products
                    SET quantity = quantity - ?
                    WHERE LOWER(product_name) LIKE LOWER(?)
                """, (quantity, f"%{product_name}%"))

                conn.commit()

    cursor.execute("SELECT * FROM sales ORDER BY id DESC")
    sales_data = cursor.fetchall()

    conn.close()

    return render_template("sales.html", sales=sales_data)
@app.route("/export_sales")
def export_sales():
    conn = sqlite3.connect("inventory.db")

    query = """
        SELECT invoice_no,
               customer_name,
               product_name,
               quantity,
               price,
               total,
               sale_date
        FROM sales
        ORDER BY id DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    file_name = "sales_history.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)
if __name__=='__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)



