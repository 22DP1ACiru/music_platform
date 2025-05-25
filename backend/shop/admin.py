from django.contrib import admin
from .models import Product, Order, OrderItem # Use .models because it's in the same app

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0 # Don't show extra empty forms by default
    readonly_fields = ('product', 'quantity', 'price_at_purchase', 'item_total') 
    can_delete = False # Usually order items are not deleted from a processed order
    fields = ('product', 'quantity', 'price_at_purchase', 'item_total')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'price', 'currency', 'is_active', 'release', 'track')
    list_filter = ('product_type', 'is_active', 'currency')
    search_fields = ('name', 'description', 'release__title', 'track__title')
    list_editable = ('is_active',) # price is often better edited on detail view unless bulk changing
    fields = ('name', 'description', 'product_type', 'release', 'track', 'price', 'currency', 'is_active')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'total_amount_display', 'status', 'created_at', 'payment_gateway_id')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('id', 'user__username', 'user__email', 'email', 'payment_gateway_id')
    readonly_fields = ('created_at', 'updated_at', 'total_amount', 'currency') # Total amount often calculated
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'email', 'status')
        }),
        ('Financials', {
            'fields': ('total_amount', 'currency'),
        }),
        ('Payment Information', {
            'fields': ('payment_gateway_id', 'payment_method_details'),
            'classes': ('collapse',), # Collapsible section
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return obj.email or "Guest"
    user_display.short_description = "User/Email"

    def total_amount_display(self, obj):
        return f"{obj.total_amount} {obj.currency}"
    total_amount_display.short_description = "Total"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'product_link', 'quantity', 'price_at_purchase', 'item_total')
    search_fields = ('order__id', 'product__name')
    readonly_fields = ('order', 'product', 'quantity', 'price_at_purchase', 'item_total') # Typically these are not changed after creation
    list_select_related = ('order', 'product', 'order__user') # Optimization for admin list view

    def order_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:shop_order_change", args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)
    order_link.short_description = 'Order'

    def product_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:shop_product_change", args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', link, obj.product.name)
    product_link.short_description = 'Product'