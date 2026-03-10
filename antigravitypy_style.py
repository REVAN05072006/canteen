# -*- coding: utf-8 -*-
"""
Smart Canteen Web Application
Run with: python smart_canteen.py
"""

import os
import io
import sys
import json
import base64
import uuid
from datetime import datetime

import uvicorn
import pandas as pd
import qrcode
from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional

# Prevent Unicode charmap errors on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Excel file initialization
def init_db():
    """Initialize Excel files if they don't exist"""
    
    # Users database
    if not os.path.exists("users.xlsx"):
        df = pd.DataFrame(columns=["user_id", "name", "email", "password", "phone"])
        # Add a test user
        test_user = pd.DataFrame([{
            "user_id": 1, 
            "name": "Test User", 
            "email": "test@example.com", 
            "password": "password123", 
            "phone": "1234567890"
        }])
        df = pd.concat([df, test_user], ignore_index=True)
        df.to_excel("users.xlsx", index=False)
        print("✅ Created users.xlsx with test user")
        
    if not os.path.exists("orders.xlsx"):
        df = pd.DataFrame(columns=["order_id", "user_id", "item_name", "quantity", "price", "timestamp"])
        df.to_excel("orders.xlsx", index=False)
        
    if not os.path.exists("inventory.xlsx"):
        data = [
            {"item_id": 1, "item_name": "🍔 Burger", "price": 120, "stock": 20},
            {"item_id": 2, "item_name": "🍕 Pizza", "price": 250, "stock": 15},
            {"item_id": 3, "item_name": "☕ Coffee", "price": 50, "stock": 50},
            {"item_id": 4, "item_name": "🥤 Soda", "price": 40, "stock": 50},
            {"item_id": 5, "item_name": "🥪 Sandwich", "price": 80, "stock": 25},
            {"item_id": 6, "item_name": "🍵 Tea", "price": 30, "stock": 40},
            {"item_id": 7, "item_name": "🍟 Fries", "price": 90, "stock": 30},
        ]
        df = pd.DataFrame(data)
        df.to_excel("inventory.xlsx", index=False)

init_db()

# FastAPI setup
app = FastAPI(title="Smart Canteen")

# Mount static files (optional, for future use)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Create template files
def create_template_files():
    """Create HTML template files"""
    
    # Base template
    with open("templates/base.html", "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Canteen</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --orange: #FF7A00;
            --cream: #FFF5EC;
            --white: #FFFFFF;
        }
        body {
            background-color: var(--cream);
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3, h4, h5, h6, .navbar-brand {
            font-family: 'Fredoka', sans-serif;
            font-weight: 600;
        }
        .navbar {
            background-color: var(--white);
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .btn-primary {
            background-color: var(--orange);
            border: none;
            color: var(--white);
        }
        .btn-primary:hover {
            background-color: #e66a00;
            color: #ffffff;
        }
        .text-orange {
            color: var(--orange) !important;
        }
        .btn-outline-primary {
            border-color: var(--orange);
            color: var(--orange);
        }
        .btn-outline-primary:hover {
            background-color: var(--orange);
            color: white;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light sticky-top mb-4">
        <div class="container">
            <a class="navbar-brand text-orange fs-3" href="/">🍽️ Smart Canteen</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto align-items-center">
                    {% if admin %}
                    <li class="nav-item"><a class="nav-link fw-bold" href="/admin/dashboard">Admin Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link text-danger fw-bold ms-lg-2" href="/admin/logout">Logout Admin</a></li>
                    {% elif user %}
                    <li class="nav-item"><a class="nav-link fw-bold" href="/">Menu</a></li>
                    <li class="nav-item"><a class="nav-link fw-bold" href="/qr">QR Scanner</a></li>
                    <li class="nav-item ms-lg-3"><span class="nav-link bg-light border rounded text-dark fw-bold px-3 shadow-sm">Hi, {{ user.name }}</span></li>
                    <li class="nav-item ms-lg-3"><a class="btn btn-sm btn-outline-danger mt-1 mt-lg-0 fw-bold px-3" href="/logout">Logout</a></li>
                    {% else %}
                    <li class="nav-item"><a class="nav-link fw-bold text-dark" href="/qr">QR Scanner</a></li>
                    <li class="nav-item"><a class="nav-link fw-bold text-dark ms-lg-2" href="/admin/login">Admin</a></li>
                    <li class="nav-item ms-lg-2"><a class="nav-link btn btn-outline-primary px-4 py-1 mb-1 mb-lg-0 fw-bold" href="/login">Login</a></li>
                    <li class="nav-item ms-lg-2"><a class="nav-link btn btn-primary px-4 py-1 text-white fw-bold shadow-sm" href="/signup">Sign Up</a></li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>
    <div class="container pb-5">
        {% block content %}{% endblock %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")

    # Index template
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<style>
    .food-card {
        border-radius: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        background: var(--white);
        border: none;
    }
    .food-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.08);
    }
    .sticky-cart {
        position: sticky;
        top: 100px;
        background: var(--white);
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.05);
        padding: 25px;
    }
    .stock-indicator {
        font-size: 0.85rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 10px;
        display: inline-block;
        margin-bottom: 15px;
    }
    .stock-high { background: #d1e7dd; color: #0f5132; }
    .stock-medium { background: #fff3cd; color: #856404; }
    .stock-low { background: #f8d7da; color: #842029; }
</style>

<div class="row">
    <div class="col-lg-8">
        <h2 class="mb-4 text-dark fw-bold">Delicious Menu ✨</h2>
        <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-4">
            {% for item in items %}
            <div class="col">
                <div class="card h-100 food-card p-3 shadow-sm">
                    <div class="card-body text-center d-flex flex-column align-items-center">
                        <h3 class="card-title fw-bold mb-1 text-dark">{{ item.item_name }}</h3>
                        <h4 class="text-orange mb-3 fw-bold">₹{{ item.price }}</h4>
                        
                        <div class="mt-auto w-100">
                        {% if item.stock <= 0 %}
                            <div class="stock-indicator stock-low w-100">OUT OF STOCK</div>
                            <button class="btn btn-secondary w-100 fw-bold rounded-pill" disabled>Sold Out</button>
                        {% else %}
                            {% if item.stock < 3 %}
                                <div class="stock-indicator stock-low w-100">Low Stock: {{ item.stock }} left!</div>
                            {% elif item.stock < 10 %}
                                <div class="stock-indicator stock-medium w-100">Stock: {{ item.stock }}</div>
                            {% else %}
                                <div class="stock-indicator stock-high w-100">Stock: {{ item.stock }}</div>
                            {% endif %}
                            
                            <button class="btn btn-primary w-100 fw-bold rounded-pill shadow-sm mt-2" onclick="addToCart({{ item.item_id }}, '{{ item.item_name|replace("'", "\\\\'") }}', {{ item.price }}, {{ item.stock }})">
                                + Add to Cart
                            </button>
                        {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <div class="col-lg-4 mt-5 mt-lg-0">
        <div class="sticky-cart border border-light">
            <h3 class="mb-3 fw-bold text-dark">Your Cart 🛒</h3>
            <div id="cart-items" class="mb-3">
                <p class="text-muted">Cart is empty. Grab some food!</p>
            </div>
            <hr>
            <div class="d-flex justify-content-between fw-bold fs-4 mb-4">
                <span>Total:</span>
                <span id="cart-total" class="text-orange">₹0</span>
            </div>
            <button class="btn btn-success w-100 fw-bold py-3 rounded-pill fs-5 shadow" onclick="checkout()">Place Order</button>
        </div>
    </div>
</div>

<script>
    let cart = {};

    function updateCartUI() {
        const cartDiv = document.getElementById('cart-items');
        const totalSpan = document.getElementById('cart-total');
        
        if (Object.keys(cart).length === 0) {
            cartDiv.innerHTML = '<p class="text-muted">Cart is empty. Grab some food!</p>';
            totalSpan.innerText = '₹0';
            return;
        }

        let html = '<ul class="list-group list-group-flush mb-3 rounded">';
        let total = 0;
        
        for (let id in cart) {
            let item = cart[id];
            let itemTotal = item.price * item.quantity;
            total += itemTotal;
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center bg-light mb-2 rounded border-0 border-start border-4 border-warning px-3 py-2">
                    <div>
                        <h6 class="my-0 fw-bold text-dark">${item.name}</h6>
                        <small class="text-muted fw-bold">₹${item.price} x ${item.quantity}</small>
                    </div>
                    <div class="text-end">
                        <span class="text-dark fw-bold d-block mb-1">₹${itemTotal}</span>
                        <div class="btn-group shadow-sm" role="group">
                            <button class="btn btn-sm btn-outline-danger fw-bold px-2 py-0" onclick="removeFromCart(${id})">-</button>
                            <span class="btn btn-sm btn-light fw-bold disabled px-2 py-0">${item.quantity}</span>
                            <button class="btn btn-sm btn-outline-success fw-bold px-2 py-0" onclick="addOne(${id})">+</button>
                        </div>
                    </div>
                </li>
            `;
        }
        html += '</ul>';
        cartDiv.innerHTML = html;
        totalSpan.innerText = '₹' + total;
    }

    function addToCart(id, name, price, maxStock) {
        if (!cart[id]) {
            cart[id] = { name: name, price: price, quantity: 1, maxStock: maxStock };
        } else {
            if (cart[id].quantity < maxStock) {
                cart[id].quantity += 1;
            } else {
                alert("Cannot add more than available stock!");
            }
        }
        updateCartUI();
    }
    
    function addOne(id) {
        if (cart[id]) {
            if (cart[id].quantity < cart[id].maxStock) {
                cart[id].quantity += 1;
                updateCartUI();
            } else {
                alert("Cannot add more than available stock!");
            }
        }
    }

    function removeFromCart(id) {
        if (cart[id]) {
            cart[id].quantity -= 1;
            if (cart[id].quantity <= 0) {
                delete cart[id];
            }
            updateCartUI();
        }
    }

    async function checkout() {
        if (Object.keys(cart).length === 0) {
            alert("Cart is empty!");
            return;
        }
        
        {% if not user %}
            alert("Please login to place an order!");
            window.location.href = "/login";
            return;
        {% endif %}

        const response = await fetch('/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cart)
        });
        
        const result = await response.json();
        if (result.success) {
            cart = {};
            updateCartUI();
            window.location.href = "/success";
        } else {
            alert("Order Failed: " + result.message);
            window.location.reload();
        }
    }
</script>
{% endblock %}""")

    # Signup template
    with open("templates/signup.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow p-5 border-0 rounded-4 mt-4 bg-white">
            <h3 class="text-center fw-bold mb-4 text-dark">Create Account</h3>
            {% if error %}
            <div class="alert alert-danger fw-bold">{{ error }}</div>
            {% endif %}
            <form action="/signup" method="post">
                <div class="mb-3">
                    <label class="form-label text-muted fw-bold">Full Name</label>
                    <input type="text" name="name" class="form-control bg-light border-0 py-2 fw-bold" required>
                </div>
                <div class="mb-3">
                    <label class="form-label text-muted fw-bold">Email Address</label>
                    <input type="email" name="email" class="form-control bg-light border-0 py-2 fw-bold" required>
                </div>
                <div class="mb-3">
                    <label class="form-label text-muted fw-bold">Phone Number</label>
                    <input type="text" name="phone" class="form-control bg-light border-0 py-2 fw-bold" required>
                </div>
                <div class="mb-4">
                    <label class="form-label text-muted fw-bold">Secure Password</label>
                    <input type="password" name="password" class="form-control bg-light border-0 py-2 fw-bold" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-3 fw-bold rounded-pill text-white mt-2 shadow-sm fs-5">Sign Up</button>
            </form>
            <p class="text-center mt-4 text-muted fw-bold">Already have an account? <a href="/login" class="text-orange text-decoration-none fw-bold ms-1">Login</a></p>
        </div>
    </div>
</div>
{% endblock %}""")

    # Login template
    with open("templates/login.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow p-5 border-0 rounded-4 mt-4 bg-white">
            <h3 class="text-center fw-bold mb-4 text-dark">Welcome Back 👋</h3>
            {% if error %}
            <div class="alert alert-danger fw-bold">{{ error }}</div>
            {% endif %}
            <form action="/login" method="post">
                <div class="mb-3">
                    <label class="form-label text-muted fw-bold">Email Address</label>
                    <input type="email" name="email" class="form-control bg-light border-0 py-2 fw-bold" required>
                </div>
                <div class="mb-4">
                    <label class="form-label text-muted fw-bold">Password</label>
                    <input type="password" name="password" class="form-control bg-light border-0 py-2 fw-bold" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-3 fw-bold rounded-pill text-white mt-2 shadow-sm fs-5">Login</button>
            </form>
            <p class="text-center mt-4 text-muted fw-bold">Don't have an account? <a href="/signup" class="text-orange text-decoration-none fw-bold ms-1">Sign up</a></p>
        </div>
    </div>
</div>
{% endblock %}""")

    # Admin login template
    with open("templates/admin_login.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow-lg p-5 border-0 rounded-4 mt-4 text-white" style="background-color: #2b2b2b;">
            <h3 class="text-center fw-bold mb-2 text-orange">Admin Portal</h3>
            <p class="text-center text-muted mb-4 small fw-bold">Default - Username: admin | Password: admin123</p>
            {% if error %}
            <div class="alert alert-danger fw-bold">{{ error }}</div>
            {% endif %}
            <form action="/admin/login" method="post">
                <div class="mb-3">
                    <label class="form-label text-light fw-bold">Admin Username</label>
                    <input type="text" name="username" class="form-control bg-secondary border-0 text-white fw-bold py-2" required>
                </div>
                <div class="mb-4">
                    <label class="form-label text-light fw-bold">Admin Password</label>
                    <input type="password" name="password" class="form-control bg-secondary border-0 text-white fw-bold py-2" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 py-3 fw-bold rounded-pill mt-2 shadow fs-5">Secure Login</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}""")

    # Admin dashboard template
    with open("templates/admin_dashboard.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<div class="row mb-4">
    <div class="col-md-4 mb-3 mb-md-0">
        <div class="card shadow border-0 bg-white p-4 rounded-4 text-center">
            <h6 class="text-muted fw-bold">TOTAL ORDERS TODAY</h6>
            <h1 class="text-orange fw-bold display-5 mt-2">{{ today_orders }}</h1>
        </div>
    </div>
    <div class="col-md-4 mb-3 mb-md-0">
        <div class="card shadow border-0 bg-white p-4 rounded-4 text-center">
            <h6 class="text-muted fw-bold">MOST POPULAR ITEM</h6>
            <h1 class="text-orange fw-bold display-5 mt-2" style="font-size: 2.5rem;">{{ popular_item }}</h1>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card shadow border-0 p-4 rounded-4 text-center" style="background-color: #fff3cd;">
            <h6 class="text-danger fw-bold">LOW STOCK ALERTS (&lt; 3)</h6>
            <h1 class="text-danger fw-bold display-5 mt-2">{{ low_stock_count }}</h1>
        </div>
    </div>
</div>

<div class="row">
    <!-- Inventory Panel -->
    <div class="col-lg-6 mb-4">
        <div class="card shadow border-0 bg-white p-4 rounded-4">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h4 class="fw-bold m-0 text-dark">Inventory Management</h4>
                <button class="btn btn-primary btn-sm rounded-pill fw-bold px-3 shadow-sm" data-bs-toggle="modal" data-bs-target="#addItemModal">+ Add Item</button>
            </div>
            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                <table class="table table-hover align-middle border-top">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th class="py-3">Menu Item</th>
                            <th class="py-3">Price (₹)</th>
                            <th class="py-3">Stock Left</th>
                            <th class="py-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in items %}
                        <tr class="{% if item.stock < 3 %}table-warning{% endif %}">
                            <td class="fw-bold">{{ item.item_name }}</td>
                            <td class="text-orange fw-bold">₹{{ item.price }}</td>
                            <td>
                                {% if item.stock < 3 %}
                                    <span class="badge bg-danger rounded-pill px-2 py-1">{{ item.stock }} (Low)</span>
                                {% else %}
                                    <span class="fw-bold">{{ item.stock }}</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="d-flex gap-2">
                                    <form action="/admin/stock/{{ item.item_id }}" method="post" class="d-flex w-100">
                                        <input type="number" name="new_stock" class="form-control form-control-sm border-0 bg-light me-1" style="width: 60px;" value="{{ item.stock }}" min="0" required>
                                        <button type="submit" class="btn btn-sm btn-outline-success fw-bold px-2">Update</button>
                                    </form>
                                    <form action="/admin/price/{{ item.item_id }}" method="post" class="d-flex w-100">
                                        <input type="number" name="new_price" class="form-control form-control-sm border-0 bg-light me-1" style="width: 65px;" value="{{ item.price }}" min="0" required>
                                        <button type="submit" class="btn btn-sm btn-outline-primary fw-bold px-2">Set</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Orders Panel -->
    <div class="col-lg-6 mb-4">
        <div class="card shadow border-0 bg-white p-4 rounded-4">
            <h4 class="fw-bold mb-4 text-dark">Recent Orders</h4>
            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                <table class="table table-hover align-middle border-top">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th class="py-3">ID</th>
                            <th class="py-3">User ID</th>
                            <th class="py-3">Item</th>
                            <th class="py-3">Qty</th>
                            <th class="py-3">Price</th>
                            <th class="py-3">Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for order in orders %}
                        <tr>
                            <td class="text-muted fw-bold">#{{ order.order_id }}</td>
                            <td class="fw-bold">{{ order.user_id }}</td>
                            <td class="fw-bold">{{ order.item_name }}</td>
                            <td class="text-center fw-bold">{{ order.quantity }}</td>
                            <td class="text-orange fw-bold">₹{{ order.price }}</td>
                            <td class="text-muted small fw-bold">{{ order.timestamp }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="text-center py-4 text-muted fw-bold">No orders yet.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Add Item Modal -->
<div class="modal fade" id="addItemModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content rounded-4 border-0 shadow">
            <div class="modal-header border-0 pb-0">
                <h5 class="modal-title fw-bold">Add New Menu Item</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4">
                <form action="/admin/add_item" method="post">
                    <div class="mb-3">
                        <label class="form-label text-muted fw-bold">Item Name (Include Emoji)</label>
                        <input type="text" name="item_name" class="form-control bg-light border-0 py-2 fw-bold" placeholder="e.g. 🥗 Salad" required>
                    </div>
                    <div class="row">
                        <div class="col-6 mb-3">
                            <label class="form-label text-muted fw-bold">Price (₹)</label>
                            <input type="number" name="price" class="form-control bg-light border-0 py-2 fw-bold" min="1" required>
                        </div>
                        <div class="col-6 mb-4">
                            <label class="form-label text-muted fw-bold">Initial Stock</label>
                            <input type="number" name="stock" class="form-control bg-light border-0 py-2 fw-bold" min="0" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary w-100 py-2 fw-bold rounded-pill text-white shadow-sm">Add to Menu</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")

    # QR template
    with open("templates/qr.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 text-center">
        <div class="card shadow p-5 border-0 rounded-4 mt-4 bg-white">
            <h2 class="fw-bold text-dark mb-3">Order via QR Code</h2>
            <p class="text-muted mb-4 fw-bold">Scan this QR code to access the Smart Canteen menu instantly from your phone.</p>
            
            <div class="d-flex justify-content-center mb-4">
                <div class="p-3 border rounded-4 shadow-sm" style="background-color: #f8f9fa;">
                    <img src="data:image/png;base64,{{ qr_code }}" class="img-fluid rounded" alt="QR Code">
                </div>
            </div>
            
            <hr class="my-4">
            
            <h4 class="fw-bold mb-3 text-dark">Camera Scanner (Optional UI)</h4>
            <div id="video-container" class="mb-3" style="display: none;">
                <video id="camera-stream" width="100%" class="rounded-4 bg-dark" autoplay playsinline></video>
                <button id="close-camera" class="btn btn-danger mt-3 fw-bold rounded-pill px-4">Stop Camera</button>
            </div>
            <button id="start-camera" class="btn btn-primary fw-bold py-2 px-4 rounded-pill shadow-sm">📷 Open Camera to Scan</button>
        </div>
    </div>
</div>

<script>
    const startBtn = document.getElementById('start-camera');
    const closeBtn = document.getElementById('close-camera');
    const videoContainer = document.getElementById('video-container');
    const video = document.getElementById('camera-stream');
    let stream;

    startBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
            video.srcObject = stream;
            videoContainer.style.display = 'block';
            startBtn.style.display = 'none';
        } catch (err) {
            alert("Error accessing camera: " + err.message);
        }
    });

    closeBtn.addEventListener('click', () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        videoContainer.style.display = 'none';
        startBtn.style.display = 'inline-block';
    });
</script>
{% endblock %}""")

    # Success template
    with open("templates/success.html", "w", encoding="utf-8") as f:
        f.write("""{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5 text-center">
        <div class="card shadow p-5 border-0 rounded-4 mt-5 bg-white">
            <div class="mb-4">
                <span style="font-size: 5rem;">✅</span>
            </div>
            <h2 class="fw-bold text-success mb-3">Order Confirmed!</h2>
            <p class="text-muted fw-bold mb-4">Your delicious food is being prepared. Please collect it from the counter shortly.</p>
            <a href="/" class="btn btn-primary py-3 px-5 rounded-pill fw-bold shadow-sm fs-5">Back to Menu</a>
        </div>
    </div>
</div>
{% endblock %}""")

# Create template files
create_template_files()

# Authentication logic
sessions = {}  # Maps session_id -> user_dict
admin_sessions = {}  # Maps session_id -> admin_dict

# Helper to get current user from cookie
def get_current_user(session_id: Optional[str] = None):
    if session_id and session_id in sessions:
        return sessions[session_id]
    return None

def get_current_admin(admin_session_id: Optional[str] = None):
    if admin_session_id and admin_session_id in admin_sessions:
        return admin_sessions[admin_session_id]
    return None

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, 
                   session_id: Optional[str] = Cookie(None),
                   admin_session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    admin = get_current_admin(admin_session_id)
    df = pd.read_excel("inventory.xlsx")
    items = df.to_dict(orient="records")
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user": user, 
        "admin": admin,
        "items": items
    })

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request,
                     session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("signup.html", {"request": request, "user": None, "admin": None})

@app.post("/signup", response_class=HTMLResponse)
async def signup(request: Request,
                name: str = Form(...), 
                email: str = Form(...), 
                phone: str = Form(...), 
                password: str = Form(...)):
    
    df = pd.read_excel("users.xlsx")
    
    # Check if email already exists (strip whitespace)
    email = email.strip()
    if email in df["email"].astype(str).str.strip().values:
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "user": None, 
            "admin": None,
            "error": "Email already exists!"
        })
    
    # Generate new user_id
    user_id = int(df["user_id"].max()) + 1 if not df.empty else 1
    
    # Create new user
    new_user = pd.DataFrame([{
        "user_id": user_id, 
        "name": name.strip(), 
        "email": email, 
        "password": password,  # Store as is, no stripping
        "phone": phone.strip()
    }])
    
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_excel("users.xlsx", index=False)
    
    print(f"✅ New user created: {email}")
    
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request,
                    session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "admin": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request,
               email: str = Form(...), 
               password: str = Form(...)):
    
    # Read users from Excel
    df = pd.read_excel("users.xlsx")
    
    # Clean the input
    email = email.strip()
    password = password  # Don't strip password to preserve exact match
    
    # Debug: Print all users in database
    print(f"\n🔍 Login attempt - Email: '{email}', Password: '{password}'")
    print(f"📊 Users in database: {len(df)}")
    
    if not df.empty:
        print("📋 Users in database:")
        for idx, row in df.iterrows():
            db_email = str(row['email']).strip()
            db_password = str(row['password'])
            print(f"   {idx+1}. Email: '{db_email}', Password: '{db_password}'")
            print(f"      Match: Email={db_email == email}, Password={db_password == password}")
    
    # Convert DataFrame to list of dicts for easier handling
    users_list = df.to_dict('records')
    
    # Find user with matching email and password
    user_found = None
    for user in users_list:
        db_email = str(user['email']).strip()
        db_password = str(user['password'])
        
        if db_email == email and db_password == password:
            user_found = user
            break
    
    if user_found:
        # Convert numpy types to Python native types
        user_dict = {
            "user_id": int(user_found["user_id"]),
            "name": str(user_found["name"]),
            "email": str(user_found["email"]),
            "password": str(user_found["password"]),
            "phone": str(user_found["phone"])
        }
        
        # Create session
        session_id = str(uuid.uuid4())
        sessions[session_id] = user_dict
        
        print(f"✅ Login successful for: {email}")
        print(f"🔑 Session created: {session_id}")
        print(f"👤 User data: {user_dict}\n")
        
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="session_id", value=session_id)
        return response
    
    print(f"❌ Login failed for: {email}\n")
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "user": None, 
        "admin": None,
        "error": "Invalid email or password!"
    })

@app.get("/logout")
async def logout(request: Request,
                session_id: Optional[str] = Cookie(None)):
    response = RedirectResponse(url="/", status_code=302)
    if session_id and session_id in sessions:
        del sessions[session_id]
        print(f"✅ Logged out session: {session_id}")
    response.delete_cookie("session_id")
    return response

# Cart checkout system
@app.post("/checkout")
async def checkout(request: Request,
                  session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    
    if not user:
        return JSONResponse({"success": False, "message": "Not logged in. Please login to place an order."})
    
    try:
        cart = await request.json()
        if not cart:
            return JSONResponse({"success": False, "message": "Cart is empty"})
        
        user_id = user["user_id"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        inv_df = pd.read_excel("inventory.xlsx")
        orders_df = pd.read_excel("orders.xlsx")
        
        new_orders = []
        max_order_id = int(orders_df["order_id"].max()) if not orders_df.empty else 0
        
        for item_id_str, details in cart.items():
            item_id = int(item_id_str)
            qty = int(details["quantity"])
            
            # Check stock
            item_idx = inv_df.index[inv_df["item_id"] == item_id].tolist()
            if not item_idx: 
                continue
            idx = item_idx[0]
            
            current_stock = int(inv_df.at[idx, "stock"])
            if current_stock < qty:
                return JSONResponse({"success": False, "message": f"Not enough stock for {details['name']}"})
                
            # Update stock
            inv_df.at[idx, "stock"] = current_stock - qty
            
            # Record order
            max_order_id += 1
            new_orders.append({
                "order_id": max_order_id,
                "user_id": user_id,
                "item_name": details["name"],
                "quantity": qty,
                "price": details["price"],
                "timestamp": timestamp
            })
            
        # Save updates
        inv_df.to_excel("inventory.xlsx", index=False)
        if new_orders:
            orders_df = pd.concat([orders_df, pd.DataFrame(new_orders)], ignore_index=True)
            orders_df.to_excel("orders.xlsx", index=False)
            
        return JSONResponse({"success": True})
        
    except Exception as e:
        print(f"❌ Checkout error: {str(e)}")
        return JSONResponse({"success": False, "message": str(e)})

@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request,
                      session_id: Optional[str] = Cookie(None),
                      admin_session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    admin = get_current_admin(admin_session_id)
    return templates.TemplateResponse("success.html", {
        "request": request, 
        "user": user, 
        "admin": admin
    })

# Admin system
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request,
                          admin_session_id: Optional[str] = Cookie(None)):
    admin = get_current_admin(admin_session_id)
    if admin:
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse("admin_login.html", {
        "request": request, 
        "user": None, 
        "admin": None
    })

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request,
                     username: str = Form(...), 
                     password: str = Form(...)):
    
    if username.strip() == "admin" and password == "admin123":
        session_id = str(uuid.uuid4())
        admin_sessions[session_id] = {"username": username, "role": "admin"}
        print(f"✅ Admin login successful: {username}")
        
        response = RedirectResponse(url="/admin/dashboard", status_code=302)
        response.set_cookie(key="admin_session_id", value=session_id)
        return response
    
    print(f"❌ Admin login failed: {username}")
    return templates.TemplateResponse("admin_login.html", {
        "request": request, 
        "user": None, 
        "admin": None,
        "error": "Invalid admin credentials!"
    })

@app.get("/admin/logout")
async def admin_logout(request: Request,
                      admin_session_id: Optional[str] = Cookie(None)):
    response = RedirectResponse(url="/", status_code=302)
    if admin_session_id and admin_session_id in admin_sessions:
        del admin_sessions[admin_session_id]
        print(f"✅ Admin logged out: {admin_session_id}")
    response.delete_cookie("admin_session_id")
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request,
                         admin_session_id: Optional[str] = Cookie(None),
                         session_id: Optional[str] = Cookie(None)):
    admin = get_current_admin(admin_session_id)
    user = get_current_user(session_id)
    
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    inv_df = pd.read_excel("inventory.xlsx")
    orders_df = pd.read_excel("orders.xlsx")
    
    # Convert to native Python types
    items = []
    for _, row in inv_df.iterrows():
        items.append({
            "item_id": int(row["item_id"]),
            "item_name": str(row["item_name"]),
            "price": int(row["price"]),
            "stock": int(row["stock"])
        })
    
    orders = []
    if not orders_df.empty:
        orders_df_sorted = orders_df.sort_values(by="timestamp", ascending=False)
        for _, row in orders_df_sorted.iterrows():
            orders.append({
                "order_id": int(row["order_id"]),
                "user_id": int(row["user_id"]),
                "item_name": str(row["item_name"]),
                "quantity": int(row["quantity"]),
                "price": int(row["price"]),
                "timestamp": str(row["timestamp"])
            })
    
    # Smart features
    today = datetime.now().strftime("%Y-%m-%d")
    today_orders = sum(1 for o in orders if str(o["timestamp"]).startswith(today))
    
    popular_item = "None"
    if not orders_df.empty:
        item_counts = orders_df.groupby("item_name")["quantity"].sum()
        if not item_counts.empty:
            popular_item = str(item_counts.idxmax())
            
    low_stock_count = len(inv_df[inv_df["stock"] < 3])
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, 
        "user": user, 
        "admin": admin,
        "items": items,
        "orders": orders,
        "today_orders": today_orders,
        "popular_item": popular_item,
        "low_stock_count": low_stock_count
    })

@app.post("/admin/stock/{item_id}")
async def update_stock(request: Request,
                      item_id: int, 
                      new_stock: int = Form(...),
                      admin_session_id: Optional[str] = Cookie(None)):
    
    admin = get_current_admin(admin_session_id)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    df = pd.read_excel("inventory.xlsx")
    df.loc[df["item_id"] == item_id, "stock"] = new_stock
    df.to_excel("inventory.xlsx", index=False)
    print(f"✅ Updated stock for item {item_id} to {new_stock}")
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/price/{item_id}")
async def update_price(request: Request,
                      item_id: int, 
                      new_price: int = Form(...),
                      admin_session_id: Optional[str] = Cookie(None)):
    
    admin = get_current_admin(admin_session_id)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    df = pd.read_excel("inventory.xlsx")
    df.loc[df["item_id"] == item_id, "price"] = new_price
    df.to_excel("inventory.xlsx", index=False)
    print(f"✅ Updated price for item {item_id} to {new_price}")
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/add_item")
async def add_item(request: Request,
                  item_name: str = Form(...), 
                  price: int = Form(...), 
                  stock: int = Form(...),
                  admin_session_id: Optional[str] = Cookie(None)):
    
    admin = get_current_admin(admin_session_id)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    df = pd.read_excel("inventory.xlsx")
    new_id = int(df["item_id"].max()) + 1 if not df.empty else 1
    new_item = pd.DataFrame([{"item_id": new_id, "item_name": item_name, "price": price, "stock": stock}])
    df = pd.concat([df, new_item], ignore_index=True)
    df.to_excel("inventory.xlsx", index=False)
    print(f"✅ Added new item: {item_name}")
    
    return RedirectResponse(url="/admin/dashboard", status_code=302)

# QR generator
@app.get("/qr", response_class=HTMLResponse)
async def qr_page(request: Request,
                 session_id: Optional[str] = Cookie(None),
                 admin_session_id: Optional[str] = Cookie(None)):
    
    user = get_current_user(session_id)
    admin = get_current_admin(admin_session_id)
    
    host_url = str(request.base_url).rstrip('/')
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(host_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return templates.TemplateResponse("qr.html", {
        "request": request, 
        "user": user, 
        "admin": admin,
        "qr_code": img_str
    })

# Debug route to view all users (remove in production)
@app.get("/debug/users")
async def debug_users():
    df = pd.read_excel("users.xlsx")
    users = []
    for _, row in df.iterrows():
        users.append({
            "user_id": int(row["user_id"]),
            "name": str(row["name"]),
            "email": str(row["email"]),
            "password": str(row["password"]),
            "phone": str(row["phone"])
        })
    return JSONResponse({"users": users})

# Server start
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Smart Canteen Application")
    print("=" * 60)
    print("📱 Access the application at: http://localhost:8000")
    print("\n👤 Test User Credentials:")
    print("   Email: test@example.com")
    print("   Password: password123")
    print("\n🔑 Admin Credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n📝 Or sign up with your own email!")
    print("\n🔍 Debug: Visit http://localhost:8000/debug/users to see all users")
    print("=" * 60)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
