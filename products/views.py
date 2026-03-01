from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import  Product, Purchase, Stock, Order, OrderItem, PurchaseItem
from .forms import ProductForm, PurchaseForm
from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
import json
from django.db.models.functions import TruncMonth
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, F
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from datetime import date




# ---------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------     Product     ---------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------

# @login_required(login_url='/login/')
def product_list(request):
    products = Product.objects.all().order_by('id')
    return render(request, 'product/product_list.html', {'products': products,})

# ---------------------- Product  Create   ------------------------------


def create_product(request):
    products = Product.objects.all().order_by('id')
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product created successfully!")
            return redirect('product_list')
    else:
        form = ProductForm()
    context = {
        'form': form,
        'products': products,
    }
    return render(request, 'product/product_form.html', context)



# ----------------------  Product Update   ------------------------------

# @login_required(login_url='/login/')
# @role_permission_required('product_update')
def product_update(request, pk):
    products = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=products)
    if form.is_valid():
        form.save()
        return redirect('product_list')
    return render(request, 'product/product_form.html', {'form':form, 'is_update':True})


# ---------------------- Product Delete  ------------------------------

# @login_required(login_url='/login/')
# @role_permission_required('product_delete')
def product_delete(request, pk):
    prodcuts = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        prodcuts.delete()
        return redirect('product_list')
    
    

# ---------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------       ---------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------

# 

# ---------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------     Purchase     ---------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------




# ----------------------------------------  Purchase  List  -------------------------------------------


def purchase_list(request):
    purchases = Purchase.objects.prefetch_related('items__product').order_by('-id')
    grand_total = 0
    for p in purchases:
        try:
            grand_total += p.total  
        except Exception as e:
            print(f"Error calculating total for Purchase {p.id}: {e}")
            continue
    return render(request, 'purchase/purchase_list.html', {
        'purchases': purchases,
        'grand_total': grand_total, 
    })


# ---------------------- Purchase  Create   ------------------------------


@transaction.atomic
def create_purchase(request, pk=None):
    purchase = None
    items = None
    is_update = False

    if pk:
        purchase = get_object_or_404(Purchase, pk=pk)
        items = purchase.items.all()
        is_update = True

    if request.method == 'POST':
        # DEBUG: Print all raw POST data
        print("=== RAW POST DATA ===")
        print(dict(request.POST))
    
        form = PurchaseForm(request.POST, instance=purchase)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.save()

            products_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            purchase_prices = request.POST.getlist('purchase_price[]')  # user edited price

            # Delete old items if updating
            if is_update:
                purchase.items.all().delete()

            grand_total = Decimal('0.00')

            for prod_id, qty, price in zip(products_ids, quantities, purchase_prices):
                if not prod_id or not price or not qty:
                    continue
                
                quantity = int(qty)
                price = Decimal(price)

                product = get_object_or_404(Product, pk=int(prod_id))
                
                 # Update product
                product.purchase_price = price
                product.save(update_fields=['purchase_price'])

                # Save PurchaseItem
                item = PurchaseItem.objects.create(
                    purchase=purchase,
                    product=product,
                    quantity=quantity,
                    unit_cost=price,
                    remaining_quantity=quantity
                )
                grand_total += price * quantity

                # Stock update
                stock_obj, _ = Stock.objects.get_or_create(product=product)
                stock_qty = stock_obj.quantity or 0
                stock_unit_cost = Decimal(stock_obj.unit_cost or 0)

                # Weighted average unit cost
                total_cost = (stock_unit_cost * stock_qty) + (price * quantity)
                total_qty = stock_qty + quantity
                
                current_unit_cost = total_cost / total_qty if total_qty > 0 else Decimal('0.00')
                current_unit_cost = current_unit_cost.quantize(Decimal('0.01'))

                # Update stock
                stock_obj.quantity = total_qty
                stock_obj.unit_cost = current_unit_cost
                stock_obj.save(update_fields=['quantity', 'unit_cost'])

               

            # Update purchase total
            purchase.total_amount = grand_total.quantize(Decimal('0.01'))
            purchase.save(update_fields=['total_amount'])

            return redirect('purchase_detail', pk=purchase.pk)
    else:
        form = PurchaseForm(instance=purchase)

    all_products = Product.objects.all()
    for p in all_products:
        p.default_price = p.purchase_price  # original price

    return render(request, 'purchase/purchase_form.html', {
        'form': form,
        'products': all_products,
        'items': items,
        'is_update': is_update,
        # 'today': timezone.now().date(),
        'today': date.today().strftime('%Y-%m-%d'),
    })
    
    
# ----------------------------------------  Purchase Update  -------------------------------------------


def purchase_update(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    old_status = purchase.status

    products = Product.objects.all().order_by('id')
    items = [
        {
            'product_id': item.product.id,
            'quantity': item.quantity,
            'purchase_price': item.purchase_price,
        }
        for item in purchase.items.all()
    ]

    if request.method == 'POST':
        form = PurchaseForm(request.POST, instance=purchase)
        if form.is_valid():
            updated_purchase = form.save(commit=False)
            updated_purchase.created_by = request.user
            updated_purchase.save()

            new_status = updated_purchase.status

            if old_status == 'Received':
                for item in purchase.items.all():
                    stock = Stock.objects.filter(product=item.product).first()
                    if stock:
                        stock.quantity = max(0, stock.quantity - item.quantity)
                        stock.save()

            purchase.items.all().delete()

            product_ids = request.POST.getlist('product')
            quantities = request.POST.getlist('quantity')
            prices = request.POST.getlist('purchase_price')

            for prod_id, qty, price in zip(product_ids, quantities, prices):
                if prod_id and int(qty) > 0:
                    item = PurchaseItem.objects.create(
                        purchase=purchase,
                        product_id=int(prod_id),
                        quantity=int(qty),
                        purchase_price=float(price)
                    )

                    if new_status == 'Received':
                        stock, _ = Stock.objects.get_or_create(
                            product=item.product,
                            defaults={'quantity': 0}
                        )
                        stock.quantity += item.quantity
                        stock.save()

            return redirect('purchase_list')

    else:
        form = PurchaseForm(instance=purchase)

    return render(request, 'purchase/purchase_form.html', {
        'form': form,
        'products': products,
        'purchase': purchase,
        'items': items,
        'is_update': True
    })


# ----------------------------------------  Purchase  Details  -------------------------------------------


def purchase_detail(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    return render(request, 'purchase/purchase_details.html', {'purchase': purchase})


# ----------------------------------------  Purchase    ------------------------------------------- 


def purchase_delete(request, pk):
    purchases = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        for item in purchases.items.all():
            stock, created= Stock.objects.get_or_create(product=item.product)
            stock.quantity -= item.quantity
            if stock.quantity < 0:
                stock.quantity = 0
            stock.save()
        purchases.delete()
        return redirect('purchase_list')



# ===============================================================================================
# ------------------------------------       Collecting Orders      -----------------------------
# ===============================================================================================

def order_list(request):
    stocks = Stock.objects.filter(quantity__gt=0).select_related('product')
    return render(request, 'collect_order/order_list.html', {'stocks':stocks})

# -------------------------------------------------------------------------------------------------------

def collect_order_list(request, category_id=None):
    if category_id:
        selected_category = get_object_or_404(pk=category_id)
        products = Product.objects.filter(category=selected_category)
    else:
        products = Product.objects.all()
        selected_category = None
    context = {'products':products, 'selected_category':selected_category}
    return render(request, 'collect_order/collect_order_list.html',context)



# --------------------------  JsonResponse  --------------------------------
def ajax_products_by_category(request, category_id):
    if category_id == 'all':
        products = Product.objects.filter(stock__isnull=False, stock__quantity__gt=0)
    else:
        products = Product.objects.filter(category_id=category_id, stock__isnull=False, stock__quantity__gt=0)
    data = []
    for p in products:
        data.append({
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'stock': p.stock.quantity
        })
    return JsonResponse(data, safe=False)

# ===============================================================================================
# ------------------------------------       pending order view      -----------------------------
# ===============================================================================================

    
@transaction.atomic
def create_order(request):
    if request.method == 'POST':
        table = request.POST.get('table')
        order_type = request.POST.get('order_type')
        discount = Decimal(request.POST.get('discount') or 0)
        paid_amount = Decimal(request.POST.get('paid_amount') or 0)
        fund = request.POST.get('fund')

        # # Check pending order for this table
        # if Order.objects.filter(table=table, status='pending').exists():
        #     messages.error(request, f"Table {table} already has a pending order!")
        #     return redirect('create_order')

        # Create order
        order = Order.objects.create(
            table=table,
            order_type=order_type,
            discount=discount,
            paid_amount=paid_amount,
            fund=fund,
            status='pending'
        )

        # Load order items from JSON
        items = json.loads(request.POST.get('order_items', '[]'))

        total_amount = Decimal('0.00')

        for item in items:
            product = get_object_or_404(Product, pk=item['product_id'])
            quantity = int(item['quantity'])
            price = Decimal(item['price'])
             
            # Amount = quantity * purchase_price
            amount = price * quantity

            # Check stock availability
            stock_obj = get_object_or_404(Stock, product=product)
            if stock_obj.quantity < quantity:
                messages.error(request, f"{product.name} not available in stock!")
                order.delete()
                return redirect('create_order')

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                purchase_price=price,  
                # amount=price * quantity,
                unit_cost=stock_obj.unit_cost,
                # profit = (Decimal(price) - Decimal(stock_obj.unit_cost)) * quantity
            ) 
            
            # Update stock quantity
            stock_obj.quantity -= quantity
            stock_obj.save(update_fields=['quantity'])

            total_amount += amount

        # Update order grand total with discount applied
        order.grand_total = total_amount - discount
        
        order.save(update_fields=['grand_total'])

        messages.success(request, "Order created successfully!")
        return redirect('pending_orders')

    # GET request: show available products from stock
    stocks = Stock.objects.filter(quantity__gt=0).select_related('product')
    return render(request, 'collect_order/order_list.html', {
        'stocks': stocks
    })
    
    

def save_order(request):
    if request.method == 'POST':
        table = request.POST.get('table')
        order_type = request.POST.get('order_type')
        discount = float(request.POST.get('discount', 0))
        grand_total = float(request.POST.get('grand_total', 0))
        fund = request.POST.get('fund')
        paid_amount = float(request.POST.get('paid_amount', 0))
        order_items_json = request.POST.get('order_items')
        order_items = json.loads(order_items_json)
        # Create Order
        order = Order.objects.create(
            table=table,
            order_type=order_type,
            discount=discount,
            grand_total=grand_total,
            fund=fund,
            paid_amount=paid_amount,
            status='pending'
        )
        # Create OrderItems
        for item in order_items:
            OrderItem.objects.create(order=order, product_id=item['product_id'], quantity=item['quantity'], price=item['price'], amount=item['quantity']*item['price'])

        return redirect('pending_orders')

# ===========================================  Pending Order List   ===================================================

def pending_order_list(request):
    orders = Order.objects.filter(status='pending') \
        .prefetch_related('items') \
        .order_by('-id')
    return render(request, 'collect_order/pending_order.html', {
        'orders': orders,
    })


def accept_order(request, order_id):
    order = Order.objects.get(id=order_id, status='pending')
    order.status = 'completed'
    order.save()
    messages.success(request, f"Order accepted successfully!")
    return redirect('pending_orders')  # redirect to sales report


# =========================================  Sales Report ======================================

def sales_report_list(request):
    orders = Order.objects.filter(status='completed').order_by('-created_at')
    total_grand = orders.aggregate(total=Sum('grand_total'))['total'] or 0
    return render(request, 'report/sales_list.html', {
        'orders': orders,
        'total_grand': total_grand
    })
    
    
# # =========================================  Admin Dashboard ======================================


@receiver(post_save, sender=PurchaseItem)
def update_purchase_total(sender, instance, **kwargs):
    instance.purchase.update_total_amount()
    
    
def home_view(request):
<<<<<<< HEAD
    return render(request, 'homes.html')
=======
    return render(request, 'homes.html')

# # =========================================  Sales Report ======================================


def sales_report(request):
    # Optional: date filter
    orders = Order.objects.prefetch_related('items__product').all()

    # Calculate total profit per order
    report_data = []
    for order in orders:
        total_profit = order.items.aggregate(total=Sum('profit'))['total'] or 0
        total_amount = order.items.aggregate(total=Sum('amount'))['total'] or 0
        report_data.append({
            'order': order,
            'total_amount': total_amount,
            'total_profit': total_profit,
            'items': order.items.all()
        })

    return render(request, 'reports/sales_report.html', {'report_data': report_data})



def stock_list(request):
    stocks = Stock.objects.select_related('product').filter(quantity__gt=0)
    return render(request, 'report/sales_list.html', {
        'stocks': stocks
    })
    
>>>>>>> fb036dbbc8cd92a3d72e642d0fcd026bd5dba2bb
