import streamlit as st
import sqlite3
from datetime import datetime
import hashlib
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Define categories with ISO numbers
categories = {
    'foods': 1, 'groceries': 2, 'electronics': 3, 'clothes': 4,
    'accessories': 5, 'pets': 6, 'drinks': 7, 'shoes': 8,
    'other': 9, 'stuff': 10
}

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.role = None

# Function to send email notifications
def send_email(recipient, subject, body):
    sender_email = "your_email@gmail.com"  # Replace with your Gmail address
    sender_password = "your_email_password"  # Replace with your App Password for Gmail
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    try:
        # Create the email content
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to the Gmail SMTP server
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()  # Upgrade the connection to secure
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

        print(f"Email sent successfully to {recipient}!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Utility function for password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Database setup and product population
def init_db():
    conn = sqlite3.connect("supermarket.db")
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        category TEXT,
                        iso_number INTEGER,
                        price REAL,
                        stock INTEGER)''')
    
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 501):
            category = random.choice(list(categories.keys()))
            iso_number = categories[category]
            price = random.randint(500, 100000)
            stock = random.randint(5, 10)
            cursor.execute('''
                INSERT INTO products (name, category, iso_number, price, stock)
                VALUES (?, ?, ?, ?, ?)
            ''', (f"Product {i}", category, iso_number, price, stock))
        conn.commit()

    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(product_id) REFERENCES products(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                        user_id INTEGER,
                        product_id INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(product_id) REFERENCES products(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        order_date TEXT,
                        status TEXT,
                        total_amount REAL,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
                        order_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER,
                        price REAL,
                        FOREIGN KEY(order_id) REFERENCES orders(id),
                        FOREIGN KEY(product_id) REFERENCES products(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS product_ratings (
                        user_id INTEGER,
                        product_id INTEGER,
                        rating INTEGER,
                        review TEXT,
                        date TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(product_id) REFERENCES products(id))''')
    
    conn.commit()
    return conn

# User registration function
def register_user(username, password, role):
    conn = init_db()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
        conn.commit()
        st.success("User registered successfully.")
    except sqlite3.IntegrityError:
        st.error("Username already exists.")
    conn.close()

# User login function
def login_user(username, password):
    conn = init_db()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT id, role FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cursor.fetchone()
    conn.close()
    if user:
        st.session_state.logged_in = True
        st.session_state.user_id = user[0]
        st.session_state.role = user[1]
        st.success("Logged in successfully.")
    else:
        st.error("Incorrect username or password.")

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.role = None
    st.success("Logged out successfully.")

# Product management functions
def add_product(name, category, price, stock):
    conn = init_db()
    cursor = conn.cursor()
    iso_number = categories.get(category, None)
    if iso_number:
        cursor.execute("INSERT INTO products (name, category, iso_number, price, stock) VALUES (?, ?, ?, ?, ?)", (name, category, iso_number, price, stock))
        conn.commit()
        st.success("Product added successfully.")
    else:
        st.error("Invalid category")
    conn.close()

def update_product(product_id, name, category, price, stock):
    conn = init_db()
    cursor = conn.cursor()
    iso_number = categories.get(category, None)
    if iso_number:
        cursor.execute("UPDATE products SET name = ?, category = ?, iso_number = ?, price = ?, stock = ? WHERE id = ?", (name, category, iso_number, price, stock, product_id))
        conn.commit()
        st.success("Product updated successfully.")
    else:
        st.error("Invalid category")
    conn.close()

def remove_product(product_id):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    st.success("Product removed successfully.")

# Cart Management
def add_to_cart(user_id, product_id, quantity):
    conn = init_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
    stock = cursor.fetchone()
    if not stock or stock[0] < quantity:
        st.error("Requested quantity is not available in stock.")
        conn.close()
        return
    
    cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    existing = cursor.fetchone()
    if existing:
        new_quantity = existing[0] + quantity
        cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (new_quantity, user_id, product_id))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))
    
    conn.commit()
    conn.close()
    st.success("Item added to cart.")

def view_cart(user_id):
    conn = init_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT p.id, p.name, p.price, c.quantity 
    FROM cart c
    JOIN products p ON c.product_id = p.id
    WHERE c.user_id = ?
    """, (user_id,))
    
    items = cursor.fetchall()
    conn.close()
    if not items:
        st.write("Your cart is empty.")
    else:
        st.write("### Your Cart")
        total = 0
        for item in items:
            st.write(f"**Product ID:** {item[0]} | **Name:** {item[1]} | **Price:** ₦{item[2]:,.2f} | **Quantity:** {item[3]}")
            total += item[2] * item[3]
        st.write(f"**Total Amount:** ₦{total:,.2f}")

def remove_from_cart(user_id, product_id):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    conn.commit()
    conn.close()
    st.success("Item removed from cart.")

# Wishlist Management
def add_to_wishlist(user_id, product_id):
    conn = init_db()
    cursor = conn.cursor()
    # Check if already in wishlist
    cursor.execute("SELECT * FROM wishlist WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    if cursor.fetchone():
        st.warning("Product already in wishlist.")
    else:
        cursor.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
        conn.commit()
        st.success("Product added to wishlist.")
    conn.close()

def view_wishlist(user_id):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.id, p.name, p.price 
    FROM wishlist w
    JOIN products p ON w.product_id = p.id
    WHERE w.user_id = ?
    """, (user_id,))
    
    items = cursor.fetchall()
    conn.close()
    if not items:
        st.write("Your wishlist is empty.")
    else:
        st.write("### Your Wishlist")
        for item in items:
            st.write(f"**Product ID:** {item[0]} | **Name:** {item[1]} | **Price:** ₦{item[2]:,.2f}")

def remove_from_wishlist(user_id, product_id):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wishlist WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    conn.commit()
    conn.close()
    st.success("Item removed from wishlist.")

# Order Management
def place_order(user_id):
    conn = init_db()
    cursor = conn.cursor()
    
    # Retrieve cart items
    cursor.execute("""
    SELECT p.id, p.name, p.price, c.quantity, p.stock 
    FROM cart c
    JOIN products p ON c.product_id = p.id
    WHERE c.user_id = ?
    """, (user_id,))
    
    items = cursor.fetchall()
    if not items:
        st.error("Your cart is empty.")
        conn.close()
        return

    # Calculate total and check stock
    total_amount = 0
    for item in items:
        if item[4] < item[3]:
            st.error(f"Insufficient stock for {item[1]}. Available: {item[4]}, Requested: {item[3]}.")
            conn.close()
            return
        total_amount += item[2] * item[3]
    
    # Insert order
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO orders (user_id, order_date, status, total_amount)
        VALUES (?, ?, ?, ?)
    """, (user_id, order_date, "Processing", total_amount))
    order_id = cursor.lastrowid
    
    # Insert order items and update stock
    for item in items:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, item[0], item[3], item[2]))
        cursor.execute("""
            UPDATE products SET stock = stock - ? WHERE id = ?
        """, (item[3], item[0]))
    
    # Clear cart
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    st.success("Order placed successfully.")

def view_order_history(user_id):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, order_date, status, total_amount 
    FROM orders 
    WHERE user_id = ?
    ORDER BY order_date DESC
    """, (user_id,))
    
    orders = cursor.fetchall()
    conn.close()
    if not orders:
        st.write("No orders found.")
    else:
        st.write("### Order History")
        for order in orders:
            st.write(f"**Order ID:** {order[0]} | **Date:** {order[1]} | **Status:** {order[2]} | **Total:** ₦{order[3]:,.2f}")
            # Optionally, show order items
            conn = init_db()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT p.name, oi.quantity, oi.price 
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
            """, (order[0],))
            items = cursor.fetchall()
            conn.close()
            for item in items:
                st.write(f" - **Product:** {item[0]} | **Quantity:** {item[1]} | **Price:** ₦{item[2]:,.2f}")
            st.write("---")

# Ratings and Reviews
def rate_product(user_id, product_id, rating, review):
    conn = init_db()
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO product_ratings (user_id, product_id, rating, review, date)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, product_id, rating, review, date))
    conn.commit()
    conn.close()
    st.success("Product rated successfully.")

def view_product_reviews(product_id):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT r.rating, r.review, r.date, u.username 
    FROM product_ratings r
    JOIN users u ON r.user_id = u.id
    WHERE r.product_id = ?
    ORDER BY r.date DESC
    """, (product_id,))
    
    reviews = cursor.fetchall()
    conn.close()
    if not reviews:
        st.write("No reviews yet for this product.")
    else:
        st.write("### Product Reviews")
        for review in reviews:
            st.write(f"**Username:** {review[3]} | **Rating:** {review[0]}/5 | **Date:** {review[2]}")
            st.write(f"**Review:** {review[1]}")
            st.write("---")

# Search and Filter Functionality
def search_products(query, category=None, min_price=None, max_price=None):
    conn = init_db()
    cursor = conn.cursor()
    
    sql_query = "SELECT id, name, category, price, stock FROM products WHERE name LIKE ?"
    params = (f"%{query}%",)
    
    if category and category != "All":
        sql_query += " AND category = ?"
        params += (category,)
    
    if min_price:
        sql_query += " AND price >= ?"
        params += (min_price,)
    
    if max_price:
        sql_query += " AND price <= ?"
        params += (max_price,)
    
    cursor.execute(sql_query, params)
    results = cursor.fetchall()
    conn.close()
    return results

# Display products with search and filter
def display_products(user_id):
    st.write("### Available Products")
    
    query = st.text_input("Search Products")
    category = st.selectbox("Category", ["All"] + list(categories.keys()))
    min_price, max_price = st.slider("Price Range (₦)", 0, 100000, (0, 100000))
    
    products = search_products(query, category if category != "All" else None, min_price, max_price)
    
    if not products:
        st.write("No products found.")
    else:
        for product in products:
            st.write(f"**Product ID:** {product[0]} | **Name:** {product[1]} | **Category:** {product[2]} | **Price:** ₦{product[3]:,.2f} | **Stock:** {product[4]}")
            col1, col2, col3 = st.columns(3)
            with col1:
                quantity = st.number_input(f"Quantity for Product {product[0]}", min_value=1, max_value=product[4], value=1, key=f"qty_{product[0]}")
            with col2:
                if st.button(f"Add to Cart {product[0]}", key=f"cart_{product[0]}"):
                    add_to_cart(user_id, product[0], quantity)
            with col3:
                if st.button(f"Add to Wishlist {product[0]}", key=f"wishlist_{product[0]}"):
                    add_to_wishlist(user_id, product[0])
            st.write("---")

# Customer Dashboard
def customer_dashboard(user_id):
    st.write("### Customer Dashboard")
    
    # Search and Display Products
    display_products(user_id)
    
    # View Cart
    if st.checkbox("View Cart"):
        view_cart(user_id)
        st.write("---")
    
    # Remove items from cart
    if st.checkbox("Remove Items from Cart"):
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.id, p.name, c.quantity 
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
        """, (user_id,))
        cart_items = cursor.fetchall()
        conn.close()
        if not cart_items:
            st.write("Your cart is empty.")
        else:
            product_ids = [str(item[0]) for item in cart_items]
            product_id_to_remove = st.selectbox("Select Product ID to Remove", product_ids)
            if st.button("Remove from Cart"):
                remove_from_cart(user_id, int(product_id_to_remove))
        st.write("---")

         # Wishlist
    if st.checkbox("View Wishlist"):
        view_wishlist(user_id)
        st.write("---")
    
    # Remove items from wishlist
    if st.checkbox("Remove Items from Wishlist"):
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.id, p.name 
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        WHERE w.user_id = ?
        """, (user_id,))
        wishlist_items = cursor.fetchall()
        conn.close()
        if not wishlist_items:
            st.write("Your wishlist is empty.")
        else:
            product_ids = [str(item[0]) for item in wishlist_items]
            product_id_to_remove = st.selectbox("Select Product ID to Remove from Wishlist", product_ids)
            if st.button("Remove from Wishlist"):
                remove_from_wishlist(user_id, int(product_id_to_remove))
        st.write("---")
    
    # Place Order
    if st.button("Place Order"):
        place_order(user_id)
        st.write("---")
    
    # View Order History
    if st.checkbox("View Order History"):
        view_order_history(user_id)
        st.write("---")
    
    # Rate a Product
    st.write("### Rate a Product")
    product_id = st.number_input("Enter Product ID to Rate", min_value=1, step=1)
    rating = st.slider("Rating (1-5)", 1, 5, 3)
    review = st.text_area("Write a Review")
    if st.button("Submit Review"):
        rate_product(user_id, product_id, rating, review)
    st.write("---")
    
    # Display Product Reviews
    st.write("### View Product Reviews")
    product_id_view = st.number_input("Enter Product ID to View Reviews", min_value=1, step=1)
    if st.button("View Reviews"):
        view_product_reviews(product_id_view)
    st.write("---")

# Supermarket Dashboard (Admin or Store Management)
def supermarket_dashboard(user_id):
    if st.session_state.role != 'admin':
        st.error("You do not have permission to access this dashboard.")
        return
    
    st.write("### Supermarket Dashboard (Admin)")

    # Add new product
    st.subheader("Add New Product")
    product_name = st.text_input("Product Name")
    category = st.selectbox("Category", list(categories.keys()))
    price = st.number_input("Price", min_value=1, value=1000)
    stock = st.number_input("Stock", min_value=1, value=10)
    
    if st.button("Add Product"):
        add_product(product_name, category, price, stock)

    # Update Product
    st.subheader("Update Product")
    product_id = st.number_input("Product ID to Update", min_value=1, step=1)
    if product_id:
        cursor = init_db().cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        conn = sqlite3.connect("supermarket.db")
        if product:
            updated_name = st.text_input("New Name", value=product[1])
            updated_category = st.selectbox("New Category", list(categories.keys()), index=list(categories.keys()).index(product[2]))
            updated_price = st.number_input("New Price", min_value=1, value=product[4])
            updated_stock = st.number_input("New Stock", min_value=1, value=product[5])

            if st.button("Update Product"):
                update_product(product_id, updated_name, updated_category, updated_price, updated_stock)
        conn.close()

    # Remove Product
    st.subheader("Remove Product")
    product_id_remove = st.number_input("Product ID to Remove", min_value=1, step=1)
    if st.button("Remove Product"):
        remove_product(product_id_remove)

# Main Streamlit UI 
def main():
    if st.session_state.logged_in:
        if st.session_state.role == "admin":
            supermarket_dashboard(st.session_state.user_id)
        else:
            customer_dashboard(st.session_state.user_id)
    else:
        st.write("### Welcome to the Supermarket Management System")
        st.write("Please log in or register to continue.")
        choice = st.radio("Login or Register", ["Login", "Register"])
        if choice == "Register":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["customer", "admin"])
            if st.button("Register"):
                register_user(username, password, role)
        else:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                login_user(username, password)

    if st.session_state.logged_in:
        if st.button("Logout"):
            logout()

if __name__ == "__main__":
    main()

