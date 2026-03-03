from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import db
from models import Product, Order, Cart, Review

buyer = Blueprint('buyer', __name__)

def buyer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'buyer':
            flash('Please login as buyer.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@buyer.route('/buyer/dashboard')
@buyer_required
def dashboard():
    buyer_id = session['user_id']
    orders = Order.query.filter_by(buyer_id=buyer_id).order_by(Order.created_at.desc()).all()
    total_spent = sum(o.total_price for o in orders) or 0
    return render_template('buyer/dashboard.html', orders=orders, total_spent=total_spent)

@buyer.route('/marketplace')
def marketplace():
    search = request.args.get('search', '')
    category = request.args.get('category', '')

    query = Product.query.filter_by(status='available')
    if search:
        query = query.filter(Product.crop_name.ilike(f'%{search}%'))
    if category:
        query = query.filter_by(category=category)

    products = query.order_by(Product.created_at.desc()).all()
    return render_template('buyer/marketplace.html',
                         products=products,
                         search=search)

@buyer.route('/add-to-cart/<int:product_id>', methods=['POST'])
@buyer_required
def add_to_cart(product_id):
    quantity = float(request.form.get('quantity', 1))
    buyer_id = session['user_id']
    existing = Cart.query.filter_by(buyer_id=buyer_id, product_id=product_id).first()
    if existing:
        existing.quantity += quantity
    else:
        cart_item = Cart(buyer_id=buyer_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash('Added to cart!', 'success')
    return redirect(url_for('buyer.marketplace'))


@buyer.route('/cart')
@buyer_required
def cart():
    buyer_id = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('orders/cart.html', cart_items=cart_items, total=total)


@buyer.route('/place-order', methods=['POST'])
@buyer_required
def place_order():
    buyer_id = session['user_id']
    delivery_address = request.form['delivery_address']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    for item in cart_items:
        order = Order(
            buyer_id=buyer_id,
            farmer_id=item.product.farmer_id,
            product_id=item.product_id,
            quantity=item.quantity,
            total_price=item.product.price * item.quantity,
            delivery_address=delivery_address
        )
        db.session.add(order)
        db.session.delete(item)
    db.session.commit()
    flash('Order placed successfully!', 'success')
    return redirect(url_for('buyer.dashboard'))


@buyer.route('/review/<int:order_id>', methods=['GET', 'POST'])
@buyer_required
def review(order_id):
    order = Order.query.get(order_id)
    if request.method == 'POST':
        rev = Review(
            buyer_id=session['user_id'],
            farmer_id=order.farmer_id,
            order_id=order_id,
            rating=int(request.form['rating']),
            comment=request.form['comment']
        )
        db.session.add(rev)
        db.session.commit()
        flash('Review submitted!', 'success')
        return redirect(url_for('buyer.dashboard'))
    return render_template('orders/review.html', order=order)