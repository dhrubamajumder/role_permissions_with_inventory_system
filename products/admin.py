from django.contrib import admin
from .models import Product, Supplier, Purchase, OrderItem, Order

admin.site.register(Product)
admin.site.register(Supplier)
admin.site.register(Purchase)
admin.site.register(OrderItem)
admin.site.register(Order)
