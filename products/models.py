from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone

# Create your models here.



class Product(models.Model):
    name = models.CharField(max_length=150)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2)  # Selling price
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)  
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class Purchase(models.Model):
    # supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purchase_date = models.DateField(default=timezone.now)


    @property
    def total(self):
        return sum(item.total for item in self.items.all())

    def update_total_amount(self):
        self.total_amount = self.total
        self.save(update_fields=['total_amount'])
        
        
class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)  # unit price
    remaining_quantity = models.PositiveIntegerField(default=0)

    @property
    def total(self):
        return self.quantity * self.unit_cost
    

class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0) 
    unit_cost = models.PositiveIntegerField(default=0)  

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class Order(models.Model):
    table = models.CharField(max_length=50)
    order_type = models.CharField(max_length=20, choices=[('heaving','Heaving'),('parcel','Parcel')])
    discount = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fund = models.CharField(max_length=20, choices=[('cash','Cash'),('bkash','Bkash')])
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')  # pending / completed

    @property
    def calculated_profit(self):
        return self.items.aggregate(total=Sum('profit'))['total'] or Decimal('0.00')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=6)
    profit = models.DecimalField(max_digits=12, decimal_places=2)
    
    def save(self, *args, **kwargs):
        qty = Decimal(self.quantity)

        # Only set defaults if not already provided
        if not self.purchase_price:
            self.purchase_price = Decimal(self.product.purchase_price)
        if not self.unit_cost:
            self.unit_cost = Decimal(self.product.unit_cost)

        # Recalculate derived fields
        self.amount = self.purchase_price * qty
        self.profit = (self.purchase_price - self.unit_cost) * qty 

        super().save(*args, **kwargs)

        self.order.total_profit = self.order.items.aggregate(total=Sum('profit'))['total'] or Decimal('0.00')
        self.order.save(update_fields=['total_profit'])


# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     purchase_price = models.DecimalField(max_digits=10, decimal_places=2)  # per unit price from Product
#     amount = models.DecimalField(max_digits=12, decimal_places=2)
#     profit = models.DecimalField(max_digits=12, decimal_places=2)
#     unit_cost = models.DecimalField(max_digits=10, decimal_places=6)  # higher precision for average

#     def save(self, *args, **kwargs):
#         qty = Decimal(self.quantity)

#         # Set purchase_price from product
#         self.purchase_price = Decimal(self.product.purchase_price)

#         # Total amount
#         self.amount = self.purchase_price * qty

#         # Only calculate FIFO unit_cost & profit for new items
#         if not self.pk:
#             remaining_qty = qty
#             total_cost = Decimal('0.00')
#             total_profit = Decimal('0.00')

#             with transaction.atomic():
#                 # FIFO stock consumption
#                 purchase_batches = PurchaseItem.objects.filter(
#                     product=self.product,
#                     remaining_quantity__gt=0
#                 ).order_by('purchase__purchase_date', 'id')

#                 total_available = sum(batch.remaining_quantity for batch in purchase_batches)
#                 if total_available < qty:
#                     raise ValueError(
#                         f"Not enough stock for product {self.product.name}. Available: {total_available}, required: {qty}"
#                     )

#                 for batch in purchase_batches:
#                     if remaining_qty <= 0:
#                         break

#                     usable_qty = min(Decimal(batch.remaining_quantity), remaining_qty)
#                     batch.remaining_quantity -= int(usable_qty)
#                     batch.save(update_fields=['remaining_quantity'])

#                     batch_cost = Decimal(batch.unit_cost) * usable_qty
#                     batch_profit = (self.purchase_price - Decimal(batch.unit_cost)) * usable_qty

#                     total_cost += batch_cost
#                     total_profit += batch_profit
#                     remaining_qty -= usable_qty

#             # 🔹 Unit cost = weighted average
#             self.unit_cost = total_cost / qty
#             self.profit = total_profit

#         super().save(*args, **kwargs)

#         # Update order total profit
#         self.order.total_profit = self.order.items.aggregate(total=Sum('profit'))['total'] or Decimal('0.00')
#         self.order.save(update_fields=['total_profit'])
        
        





