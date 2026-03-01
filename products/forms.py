from django import forms 
from django.contrib.auth.models import User
from .models import Product, Purchase, PurchaseItem, Supplier
import datetime


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'email']
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data



class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sales_price', 'purchase_price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sales_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['purchase_date']  
        widgets = {
            'purchase_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_date'].initial = datetime.date.today()


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity', 'unit_cost']  
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control price', 'readonly': True}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name' : forms.TextInput(attrs={'class':'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
        }
    

