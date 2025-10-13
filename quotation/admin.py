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

    # Show per-item total price (correct discount logic)
    def total_price(self, obj):
        if obj and obj.qty and obj.rate:
            # Apply percentage discount
            discounted_rate = float(obj.rate) * (1 - float(obj.discount) / 100)

            # Subtotal after discount
            subtotal = obj.qty * discounted_rate

            # VAT on discounted subtotal
            vat_amount = subtotal * (float(obj.vat) / 100)

            # Total including VAT
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
        'vat_display',
        'grand_total_display',
        'created_at',
        'updated_at',
    )
    inlines = [QuotationItemInline]
    readonly_fields = (
        'created_at',
        'updated_at',
        'subtotal_display',
        'discount_display',
        'vat_display',
        'grand_total_display'
    )

    # --- Calculated display fields ---
    def subtotal_display(self, obj):
        value = float(obj.total_before_discount())
        return "{:.2f}".format(value)
    subtotal_display.short_description = "Subtotal"

    def discount_display(self, obj):
        value = float(obj.total_discount())
        return "{:.2f}".format(value)
    discount_display.short_description = "Item Discounts"

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
