from django.contrib import admin
from django.utils.html import format_html
from .models import Quotation, QuotationItem


class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    min_num = 1
    max_num = 100
    can_delete = True
    readonly_fields = ('total_price',)

    def total_price(self, obj):
        if obj and obj.qty and obj.rate:
            discounted_rate = float(obj.rate) * (1 - float(obj.discount) / 100)
            subtotal = obj.qty * discounted_rate
            vat_amount = subtotal * (float(obj.vat) / 100)
            total = subtotal + vat_amount
            return "{:.2f}".format(total)
        return "-"
    total_price.short_description = "Item Total"


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'status',
        'subtotal_display',
        'discount_display',
        'subtotal_discount',   
        'vat_display',
        'grand_total_display',
        'created_at',
        'updated_at',
    )
    inlines = [QuotationItemInline]

    # Not read-only so user can input it
    readonly_fields = (
        'created_at',
        'updated_at',
        'subtotal_display',
        'discount_display',
        'vat_display',
        'grand_total_display',
    )

    # Define field order (so subtotal_discount appears nicely)
    fieldsets = (
        (None, {
            'fields': (
                'status',
                'subtotal_discount', 
            )
        }),
        ('Calculated Summary', {
            'fields': (
                'subtotal_display',
                'discount_display',
                'vat_display',
                'grand_total_display',
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # --- Calculated display fields ---
    def subtotal_display(self, obj):
        value = float(obj.total_before_discount())
        return "{:.2f}".format(value)
    subtotal_display.short_description = "Subtotal (Before Discounts)"

    def discount_display(self, obj):
        value = float(obj.total_discount())
        return "{:.2f}".format(value)
    discount_display.short_description = "Per-Item Discounts"

    def vat_display(self, obj):
        value = float(obj.total_vat())
        return "{:.2f}".format(value)
    vat_display.short_description = "Total VAT"

    def grand_total_display(self, obj):
        value = float(obj.grand_total())
        color = "#008000" if value > 0 else "#999999"
        formatted_value = "{:.2f}".format(value)
        return format_html('<b style="color:{};">{}</b>', color, formatted_value)
    grand_total_display.short_description = "Grand Total"
