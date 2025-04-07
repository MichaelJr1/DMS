import random
from flask import Flask, render_template, request, redirect
import psycopg2
from datetime import timedelta, date

app = Flask(__name__)
DATABASE_URL = "postgresql://neondb_owner:npg_M5sVheSzQLv4@ep-shrill-tree-a819xf7v-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True  # Enable auto-commit for transactions
    print("Connected to PostgreSQL successfully!")

    # Create a cursor object
    cur = conn.cursor()

    # Ensure the 'water_added' column exists, if not add it
    cur.execute("""
        ALTER TABLE team4_flowers 
        ADD COLUMN IF NOT EXISTS water_added INT DEFAULT 0;
    """)

    # --- CREATE TABLES ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team4_flowers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            last_watered DATE NOT NULL,
            water_level INT NOT NULL,
            min_water_required INT NOT NULL,
            water_added INT NOT NULL DEFAULT 0
        );
    """)

    # Creates the customers table - Project 2
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team4_customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100)
        );
    """)

    # Creates the orders table - Project 2
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team4_orders (
            id SERIAL PRIMARY KEY,
            customer_id INT REFERENCES team4_customers(id),
            flower_id INT REFERENCES team4_flowers(id),
            order_date DATE
        );
    """)

    # Check if the typo 'order_ate' column exists, and rename it if needed
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'team4_orders' AND column_name = 'order_ate';
    """)
    if cur.fetchone():
        print("Fixing column name: renaming 'order_ate' to 'order_date'...")
        cur.execute("ALTER TABLE team4_orders RENAME COLUMN order_ate TO order_date;")
    

    # Insert 100,000 customers if not already inserted - Project 2
    cur.execute("SELECT COUNT(*) FROM team4_customers;")
    customer_count = cur.fetchone()[0]
    if customer_count == 0:
        print("Inserting 100,000 customers...")
        for i in range(100000):
            cur.execute("INSERT INTO team4_customers (name, email) VALUES (%s, %s)",
                        (f'Customer_{i}', f'customer{i}@email.com'))
        print("Customer data inserted.")

    cur.execute("SELECT MIN(id), MAX(id) FROM team4_customers")
    min_cust_id, max_cust_id = cur.fetchone()

    cur.execute("SELECT MIN(id), MAX(id) FROM team4_flowers")
    min_flower_id, max_flower_id = cur.fetchone()

    # Insert 500,000 orders if not already inserted - Project 2
    cur.execute("SELECT COUNT(*) FROM team4_orders;")
    order_count = cur.fetchone()[0]
    if order_count < 500000:
        print("Inserting 500,000 orders...")
        for i in range(order_count, 500000):
            cust_id = random.randint(min_cust_id, max_cust_id)
            flower_id = random.randint(min_flower_id, max_flower_id)
            days_ago = random.randint(0, 365)
            order_date = date.today() - timedelta(days=days_ago)

            cur.execute("""
                INSERT INTO team4_orders (customer_id, flower_id, order_date)
                VALUES (%s, %s, %s)
            """, (cust_id, flower_id, order_date))
            #print(f"cust_id: {cust_id}, flower_id: {flower_id}, order_date: {order_date}")
        print("Order data inserted.")

    # Creates the table with sample data if empty
    cur.execute("SELECT COUNT(*) FROM team4_flowers;")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("""
            INSERT INTO team4_flowers (name, last_watered, water_level, min_water_required)
            VALUES
            ('Rose', '2025-03-05', 20, 5),
            ('Lily', '2025-03-05', 10, 7),
            ('Tulip', '2025-03-05', 3, 5);
        """)
        print("Sample data inserted.")
    else:
        print("Sample data already exists.")

except Exception as e:
    print("Error:", e)

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    # Set Timezone for every new connection as well
    with conn.cursor() as cur:
        cur.execute("SET TIMEZONE = 'America/Los_Angeles';")  # Change timezone to match CURRENT_DATE timezone
    return conn

@app.route('/')
def index():
    return render_template('flowers.html')

# --- Main Structure --- #
@app.route('/flowers')
def flowers():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, last_watered, water_level, min_water_required, water_added FROM team4_flowers by ORDER BY id ASC")
    flowers = cur.fetchall()
    
    today = datetime.date.today()
    formatted_flowers = []

    for flower in flowers:
        
        water_level = flower[3]
        min_water_required = flower[4]
        #water_added = flower[5]
        days_since_watered = (today - flower[2]).days

        if water_level >= min_water_required and days_since_watered <= 2:
            watering_status = 'Well-watered'
        elif water_level > 0 and water_level < min_water_required:
            watering_status = 'Needs Watering'
        elif water_level <= 0:
            watering_status = 'Severely Dehydrated'
        elif 3 <= days_since_watered <= 5:
            watering_status = 'Needs Watering'
        elif 6 <= days_since_watered <= 8:
            watering_status = 'Dry'
        else:
            watering_status = 'Severely Dehydrated'

    # Convert fetched data into dictionaries
        formatted_flowers.append({
            "id": flower[0],
            "name": flower[1] if flower[1] else "Unnamed",
            "last_watered": flower[2].strftime("%Y-%m-%d") if isinstance(flower[2], datetime.date) else "Unknown",
            "water_level": flower[3] if flower[3] is not None else 0,
            "min_water_required": flower[4] if flower[4] is not None else 0,
            "water_added" : flower[5] if flower[5] is not None else 0,
            "watering_status": watering_status
        })
    
    cur.close()
    conn.close()
    
    return render_template('flowers.html', flowers=formatted_flowers)

# Get all Flowers
@app.route('/flowers')
def manage_flowers():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM team4_flowers")
    flowers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('flowers.html', flowers=flowers)

# Add Flower
@app.route('/add_flower', methods=['POST'])
def add_flower():
    name = request.form['name']
    last_watered = request.form['last_watered']
    water_level = request.form['water_level']
    min_water_required = request.form['min_water_required']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO team4_flowers (name, last_watered, water_level, min_water_required) VALUES (%s, %s, %s, %s)", (name, last_watered, water_level, min_water_required))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/flowers')

# Update Flower
@app.route('/update_flower/<int:flower_id>', methods=['POST'])
def update_flower(flower_id):
    name = request.form['name']
    last_watered = request.form['last_watered']
    water_level = request.form['water_level']
    min_water_required = request.form['min_water_required']

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE team4_flowers 
        SET name = %s, last_watered = %s, water_level = %s, min_water_required = %s 
        WHERE id = %s
    """, (name, last_watered, water_level, min_water_required, flower_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/flowers')

# Delete Flower
@app.route('/delete_team4_flower/<int:flower_id>', methods=['POST'])
def delete_flower(flower_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM team4_flowers WHERE id = %s", (flower_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/flowers')

# Water Loss Algorithm
@app.route('/simulate_water_loss')
def simulate_water_loss():
    print("Simulating water loss...")  # Debugging
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Debugging the number of days
        cur.execute("SELECT id, last_watered FROM team4_flowers")
        flowers = cur.fetchall()
        for flower in flowers:
            flower_id, last_watered = flower
            # Calculate the difference between the current date and last watered date
            date_diff = (datetime.date.today() - last_watered).days
            print(f"Flower ID: {flower_id}, Last Watered: {last_watered}, Days Diff: {date_diff}")

        cur.execute("""
                UPDATE team4_flowers
                SET water_level = water_level - (5 * (CURRENT_DATE - last_watered)),
                last_watered = CURRENT_DATE
        """)
        conn.commit()
    except Exception as e:
        print("Error updating water levels:", e)
    finally:
        cur.close()
        conn.close()
    return redirect('/flowers')

# Water Flower
@app.route('/water_flower/<int:flower_id>', methods=['POST'])
def water_flower(flower_id):
    water_added = int(request.form['water_added'])

    # Get the current water level for the flower 
    # Only the water level column
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT water_level FROM team4_flowers WHERE id = %s", (flower_id,))
    flower = cur.fetchone()
    current_water_level = flower[0]

    # Update the water level
    new_water_level = current_water_level + water_added

    # Update the water_added column to track the water added
    cur.execute("""
        UPDATE team4_flowers 
        SET water_level = %s, water_added = water_added + %s, last_watered = CURRENT_DATE
        WHERE id = %s
    """, (new_water_level, water_added, flower_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/flowers')

# Slow Query
@app.route('/slow_query')
def slow_query():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.name, o.order_date, f.name AS flower_name
        FROM team4_orders o
        JOIN team4_customers c ON o.customer_id = c.id
        JOIN team4_flowers f ON o.flower_id = f.id
        ORDER BY o.order_date DESC
    """)

    results = cur.fetchall()
    cur.close()
    conn.close()

    return f"Query returned {len(results)} rows."

# -- Reset the Database ID to 1 (Testing purpose ONLY)
@app.route('/reset_flower_ids')
def reset_flower_ids():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM team4_flowers")  # Deletes all records
    cur.execute("ALTER SEQUENCE team4_flowers_id_seq RESTART WITH 1")  # Resets ID
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/flowers')

if __name__ == '__main__':
    app.run(debug=True)
