from flask import Flask, render_template, request, redirect, session, url_for, flash, g
from models import db, User, Cart, Purchase
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_PERMANENT'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Djaak159%40%40@localhost/flask_shop'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)

with app.app_context():
    db.create_all()

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/main')
def main():
    if g.user is None:
        return redirect(url_for('login'))

    query = request.args.get('q', '').strip()
    products = [
        {'name': '태깅이', 'image_url': '/static/images/tshirt.jpg', 'price': 10000},
        {'name': '김라니', 'image_url': '/static/images/jeans.jpg', 'price': 20000},
        {'name': '황보재윤', 'image_url': '/static/images/sneakers.jpg', 'price': 30000},
    ]
    if query:
        products = [p for p in products if query.lower() in p['name'].lower()]
    return render_template('main.html', products=products, query=query)

@app.route('/add_to_cart/<product_name>', methods=['POST'])
def add_to_cart(product_name):
    if g.user is None:
        return redirect(url_for('login'))

    price_map = {
        '태깅이': 10000,
        '김라니': 20000,
        '황보재윤': 30000
    }
    price = price_map.get(product_name, 0)

    existing_item = Cart.query.filter_by(user_id=g.user.id, product_name=product_name).first()
    if existing_item:
        if existing_item.quantity < 99:
            existing_item.quantity += 1
    else:
        new_item = Cart(user_id=g.user.id, product_name=product_name, quantity=1, price=price)
        db.session.add(new_item)

    db.session.commit()
    flash(f'"{product_name}" 장바구니에 담겼습니다!')
    return redirect(url_for('main'))

@app.route('/checkout', methods=['GET', 'POST'])
@app.route('/checkout/<product_name>', methods=['GET', 'POST'])
def checkout(product_name=None):
    if g.user is None:
        return redirect(url_for('login'))

    price_map = {
        '태깅이': 10000,
        '김라니': 20000,
        '황보재윤': 30000
    }

    if product_name:  # ✅ 단일 상품 구매
        price = price_map.get(product_name)
        if price is None:
            flash("존재하지 않는 상품입니다.")
            return redirect(url_for('main'))

        if request.method == 'POST':
            address = request.form.get('address')
            card_number = request.form.get('card_number')

            # ✅ 구매 정보 저장
            purchase = Purchase(
                user_id=g.user.id,
                product_name=product_name,
                quantity=1,
                total_price=price,
                address=address,
                card_number=card_number
            )
            db.session.add(purchase)
            db.session.commit()

            flash('결제가 완료되었습니다.')
            return render_template('purchase_complete.html', product_name=product_name, total=price)

        return render_template('checkout.html', product_name=product_name, total=price)

    else:  # ✅ 장바구니 전체 결제
        items = Cart.query.filter_by(user_id=g.user.id).all()
        total = sum(item.price * item.quantity for item in items)

        if request.method == 'POST':
            address = request.form.get('address')
            card_number = request.form.get('card_number')

            # ✅ 모든 장바구니 항목을 purchase 테이블로 저장
            for item in items:
                purchase = Purchase(
                    user_id=g.user.id,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    total_price=item.price * item.quantity,
                    address=address,
                    card_number=card_number
                )
                db.session.add(purchase)
                db.session.delete(item)  # ✅ 장바구니 비우기
            db.session.commit()

            flash('결제가 완료되었습니다.')
            return render_template('purchase_complete.html', total=total)

        return render_template('checkout.html', product_name=None, items=items, total=total)

@app.route('/cart')
def cart():
    if g.user is None:
        return redirect(url_for('login'))

    items = Cart.query.filter_by(user_id=g.user.id).all()
    total = sum(item.price * item.quantity for item in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/update_quantity/<int:cart_id>', methods=['POST'])
def update_quantity(cart_id):
    item = Cart.query.get_or_404(cart_id)
    if item.user_id != g.user.id:
        flash('권한이 없습니다.')
        return redirect(url_for('cart'))

    action = request.form.get('action')
    if action == 'increase' and item.quantity < 99:
        item.quantity += 1
    elif action == 'decrease' and item.quantity > 1:
        item.quantity -= 1

    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    item = Cart.query.get_or_404(cart_id)
    if item.user_id == g.user.id:
        db.session.delete(item)
        db.session.commit()
        flash('상품이 장바구니에서 삭제되었습니다.')
    else:
        flash('권한이 없습니다.')
    return redirect(url_for('cart'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        if User.query.filter_by(username=username).first():
            flash('이미 존재하는 사용자입니다.')
            return redirect(url_for('signup'))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('회원가입 완료! 로그인 해주세요.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('로그인 성공!')
            return redirect(url_for('main'))
        else:
            flash('로그인 실패: 아이디 또는 비밀번호를 확인하세요.')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)