

from unicodedata import name
from django.urls import path
from . import views


urlpatterns = [
    path('create/', views.create_product, name='product_create'),
    path('list/', views.product_list, name='product_list'),
    path('<int:pk>/edit/', views.product_update, name='product_update'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    path('purchase/create/', views.create_purchase, name='purchase_create'),
    path('purchase/list/', views.purchase_list, name='purchase_list'),
    path('purchase/detail/<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('purchase/<int:pk>/update/', views.purchase_update, name='purchase_update'),
    path('purchase/<int:pk>/delete', views.purchase_delete, name='purchase_delete'),
    
    path('showsales/', views.collect_order_list, name='collect_order_list'),
    path('showsales/category/<int:category_id>/', views.collect_order_list, name='collect_order_list_by_category'),
    
    path('orders/', views.order_list, name='order_list'),
    path('orders/category/<int:category_id>/', views.order_list, name='order_list_by_category'),
    
    path('product/orders/ajax/products/<str:category_id>/', views.ajax_products_by_category, name='ajax_products'),
    
    path('orders/save/', views.save_order, name='save_order'),
    
    path('orders/create/', views.create_order, name='create_order'),
    path('order/pending/', views.pending_order_list, name='pending_orders'),
    path('order/accept/<int:order_id>/', views.accept_order, name='accept_order'),

    path('sales/report/', views.sales_report_list, name='sales_report'),
    
<<<<<<< HEAD
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),


    path('homes/', views.home_view, name='home_view'),
=======
    path('homes/', views.home_view, name='home_view'),
    
    path('sales/report/', views.sales_report_list, name='sales_report'),
    
    path('stock/list/', views.stock_list, name='stock_list'),
>>>>>>> fb036dbbc8cd92a3d72e642d0fcd026bd5dba2bb
]
