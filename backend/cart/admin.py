from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'price_override', 'added_at')
    fields = ('product', 'price_override', 'added_at')
    # autocomplete_fields = ['product'] # If Product search_fields are defined in ProductAdmin

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at', 'item_count', 'display_total_price')
    readonly_fields = ('user', 'created_at', 'updated_at')
    inlines = [CartItemInline]
    search_fields = ['user__username']

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Number of Items'

    def display_total_price(self, obj):
        return f"{obj.get_total_price()} {obj.get_currency()}"
    display_total_price.short_description = 'Total Price'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product_link', 'price_override', 'added_at', 'display_effective_price')
    search_fields = ('cart__user__username', 'product__name')
    list_filter = ('added_at',)
    # autocomplete_fields = ['cart', 'product']

    def product_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.product:
            link = reverse("admin:shop_product_change", args=[obj.product.id])
            return format_html('<a href="{}">{}</a>', link, obj.product.name)
        return "-"
    product_link.short_description = 'Product'

    def display_effective_price(self,obj):
        return f"{obj.get_effective_price()} {obj.cart.get_currency()}"
    display_effective_price.short_description = 'Effective Price'