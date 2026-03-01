from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import RegisterForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from decimal import Decimal
from collections import defaultdict
from products.models import Purchase, Order  # Import from products app
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


def register_view(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password1']
        )
        return redirect('login')
    return render(request, 'auths/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')  
        else:
            error = "Invalid username or password"
            return render(request, 'auths/login.html', {'error': error})
    return render(request, 'auths/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def dashboards(request):
    return render(request, 'auths/dashboard.html')


@login_required
def dashboard(request):
    today = timezone.now().date()
    first_day_month = today.replace(day=1)

    # All purchases
    purchases = Purchase.objects.prefetch_related('items__product')

    total_purchase = Decimal(sum([p.total for p in purchases]))
    total_sales = Decimal(Order.objects.filter(status='completed').aggregate(total=Sum('grand_total'))['total'] or 0)
    profit = total_sales - total_purchase

    # Today purchase & sales
    today_purchase = Decimal(sum([p.total for p in purchases if p.purchase_date.date() == today]))
    today_sales = Decimal(Order.objects.filter(status='completed', created_at__date=today).aggregate(total=Sum('grand_total'))['total'] or 0)

    # This month purchase & sales
    month_purchase = Decimal(sum([p.total for p in purchases if p.purchase_date.date() >= first_day_month]))
    month_sales = Decimal(Order.objects.filter(status='completed', created_at__date__gte=first_day_month).aggregate(total=Sum('grand_total'))['total'] or 0)

    # Chart data (monthly)
    from django.db.models.functions import TruncMonth
    purchase_chart = (
        Purchase.objects
        .annotate(month=TruncMonth('purchase_date'))
        .values('month')
        .annotate(total=Sum('total_amount'))
        .order_by('month')
    )

    sales_chart = (
        Order.objects.filter(status='completed')
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('grand_total'))
        .order_by('month')
    )

    return render(request, 'auths/admin_dashboard.html', {
        'total_purchase': total_purchase,
        'total_sales': total_sales,
        'profit': profit,
        'today_purchase': today_purchase,
        'today_sales': today_sales,
        'month_purchase': month_purchase,
        'month_sales': month_sales,
        'purchase_chart': purchase_chart,
        'sales_chart': sales_chart,
    })