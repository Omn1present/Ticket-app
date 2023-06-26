from flask import Flask, render_template, url_for, flash, redirect, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, login_user, logout_user, login_required



from app import app, login_manager, bcrypt, db
from models import User, Event, Ticket, Cart, Favorites, PurchaseHistory, CartTicket
from forms import RegistrationForm, LoginForm, ChangePasswordForm, AddToCartForm, RemoveFromCartForm, CheckoutForm, AddToFavoritesForm, RemoveFromFavoritesForm
import os
import stripe
stripe.api_key=os.environ.get('STRIPE_SECRET') 
from collections import defaultdict
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@app.route('/home')
def home():
    search = request.args.get('search')
    price_min = request.args.get('price_min')
    price_max = request.args.get('price_max')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')

    events = Event.query.filter((Event.name.ilike(f'%{search}%') | (search==None)))
    
    if price_min:
        events = events.filter(Event.tickets.any(Ticket.price >= price_min))
    if price_max:
        events = events.filter(Event.tickets.any(Ticket.price <= price_max))
    if date_start:
        events = events.filter(Event.date >= datetime.strptime(date_start, '%Y-%m-%d'))
    if date_end:
        events = events.filter(Event.date <= datetime.strptime(date_end, '%Y-%m-%d'))

    events = events.order_by(Event.date.asc())

    
    return render_template('home.html', events=events)

@app.route('/event/<int:event_id>')
def event(event_id):
    form_addc=AddToCartForm()
    form_addf=AddToFavoritesForm()
    event = Event.query.get_or_404(event_id)
    return render_template('event.html', event=event,form_addc=form_addc, form_addf=form_addf)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, phone=form.phone.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You can now login', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        flash('Your cart is empty', 'info')
        return redirect(url_for('home'))
    query=db.session.query(Ticket).join(CartTicket, Ticket.id==CartTicket.ticket_id).with_entities(Ticket,CartTicket.id).filter(CartTicket.cart_id==cart.id)
    tickets = query.all()
    total_cost = 0
    for item in tickets:
        total_cost+=item[0].price
    remove_form=RemoveFromCartForm()
    checkout_form=CheckoutForm()
    return render_template('cart.html', tickets=tickets, total_cost=total_cost, remove_form=remove_form, checkout_form=checkout_form)

@app.route('/add_to_cart/<int:ticket_id>', methods=['POST'])
@login_required
def add_to_cart(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    cart_ticket=CartTicket(cart_id=cart.id, ticket_id=ticket_id)
    if ticket.quantity>0:
        db.session.add(cart_ticket)
        db.session.commit()
        flash('Ticket added to cart!', 'success')
    else:
        flash('No more tickets left, sorry.','danger')
    return redirect(url_for('event', event_id=ticket.event_id))

@app.route('/remove_from_cart/<int:ticket_id>',methods=['POST'])
@login_required
def remove_from_cart(ticket_id):
    ticket = CartTicket.query.get_or_404(ticket_id)
    db.session.delete(ticket)
    db.session.commit()
    flash('Ticket removed from cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/favorites')
@login_required
def favorites():
    form=RemoveFromFavoritesForm
    favorite_events=db.session.query(Event).join(Favorites, Event.id==Favorites.event_id).filter(Favorites.user_id==current_user.id).all()
    return render_template('favorites.html', favorite_events=favorite_events, form=form)

@app.route('/add_to_favorites/<int:event_id>', methods=['POST'])
@login_required
def add_to_favorites(event_id):
    favorites = Favorites.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if not favorites:
        favorites = Favorites(user_id=current_user.id, event_id=event_id)
        db.session.add(favorites)
        db.session.commit()
        flash('Event added to favorites!', 'success')
    else:
        flash('Event is already in favorites!', 'info')
    return redirect(url_for('event', event_id=event_id))

@app.route('/remove_from_favorites/<int:event_id>', methods=['POST'])
@login_required
def remove_from_favorites(event_id):
    favorites = Favorites.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    db.session.delete(favorites)
    db.session.commit()
    flash('Event removed from favorites!', 'success')
    return redirect(url_for('event', event_id=event_id))

@app.route('/purchase_history')
@login_required
def purchase_history():
    query=db.session.query(Ticket).join(PurchaseHistory, Ticket.id==PurchaseHistory.ticket_id).with_entities(Ticket,PurchaseHistory.date_purchased).filter(PurchaseHistory.user_id==current_user.id)
    purchases=query.all()
    return render_template('purchase_history.html', purchases=purchases)
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    query=db.session.query(Ticket).join(CartTicket, Ticket.id==CartTicket.ticket_id).with_entities(Ticket,CartTicket.id).filter(CartTicket.cart_id==cart.id)
    tickets = query.all()
    ticketquants=defaultdict(lambda: 0)
    tprice=0
    for t, ctid in tickets:
        ticketquants[t.id]+=1
        tprice+=t.price
    flag=False
    for t,ctid in tickets:
        if ticketquants[t.id]>t.quantity:
            ct=CartTicket.query.get_or_404(ctid)
            db.session.delete(ct)
            flag=True 
            ticketquants[t.id]-=1
    if flag:
        flash("Between the time you've added the tickets to the cart and the time that you've pressed 'checkout' some of the tickets were sold out. We deleted them from your cart. You may press 'checkout' again or modify your order first.",'danger')
        db.session.commit()
        return redirect(url_for('cart'))
    
    intent = stripe.PaymentIntent.create(
        amount=int(tprice * 100),  
        currency="usd",
        metadata={"integration_check": "accept_a_payment"},
    )
    return render_template("payment_form.html", client_secret=intent.client_secret, tprice=tprice, intent=intent)
    

@app.route('/pay', methods=['POST'])
@login_required
def pay():
    intent_id = request.form['payment_intent_id']
    intent = stripe.PaymentIntent.retrieve(intent_id)

    if intent.status == 'succeeded':
        cart = Cart.query.filter_by(user_id=current_user.id).first()
        query=db.session.query(Ticket).join(CartTicket, Ticket.id==CartTicket.ticket_id).with_entities(Ticket,CartTicket.id).filter(CartTicket.cart_id==cart.id)
        tickets = query.all()
        for t, ctid in tickets:
            t.quantity-=1
            ct=CartTicket.query.get_or_404(ctid)
            history=PurchaseHistory(user_id=current_user.id, ticket_id=t.id)
            db.session.add(history)
            db.session.delete(ct)
        db.session.commit()
        flash("Payment successful","success")
        return redirect(url_for('cart'))

    flash("Payment unsuccessful","danger")
    
    return redirect(url_for('cart'))


@app.route('/delete_account', methods=['POST', 'GET'])
@login_required
def delete_account():
    db.session.delete(current_user)
    db.session.commit()
    flash('Your account has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        print(bcrypt.check_password_hash(current_user.password, form.old_password.data))
        if bcrypt.check_password_hash(current_user.password, form.old_password.data):
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            current_user.password = hashed_password
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('settings'))
        else:
            flash('Old password is incorrect. Please try again.', 'danger')
    return render_template('settings.html', form=form)

@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.before_request
def before_request():
    if 'theme' not in session:
        session['theme'] = 'light'








@app.route('/toggle_theme/<theme>', methods=['POST','GET'])
def toggle_theme(theme):
    if theme == 'dark':
        session['theme'] = 'dark'
    elif theme == 'light':
        session['theme'] = 'light'
    return redirect(request.referrer)