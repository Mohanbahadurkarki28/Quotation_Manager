from django.contrib import admin
from django.utils.html import format_html
from .models import Quotation, QuotationItem


# --------------------------------------------
# Inline for Quotation Items
# --------------------------------------------
class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    min_num = 1
    max_num = 100
    can_delete = True

    # Show computed field
    readonly_fields = ('item_total',)
    fields = ('name', 'qty', 'rate', 'discount', 'vat', 'version', 'unit', 'item_total')

    def item_total(self, obj):
        """Display per-item total from model property."""
        return f"{obj.total_price:.2f}" if obj and obj.pk else "-"
    item_total.short_description = "Item Total"


# --------------------------------------------
# Main Quotation Admin
# --------------------------------------------
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

    readonly_fields = (
        'created_at',
        'updated_at',
        'subtotal_display',
        'discount_display',
        'vat_display',
        'grand_total_display',
    )

    fieldsets = (
        (None, {
            'fields': (
                'status',
                'subtotal_discount',
                'terms_and_conditions',
                'additional_notes',
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

    # ----------------------------------------
    # Display helper methods for Quotation totals
    # ----------------------------------------
    def subtotal_display(self, obj):
        value = float(obj.total_before_discount())
        return f"{value:.2f}"
    subtotal_display.short_description = "Subtotal (Before Discounts)"

    def discount_display(self, obj):
        value = float(obj.total_discount())
        return f"{value:.2f}"
    discount_display.short_description = "Total Discounts"

    def vat_display(self, obj):
        value = float(obj.total_vat())
        return f"{value:.2f}"
    vat_display.short_description = "Total VAT"

    def grand_total_display(self, obj):
        value = float(obj.grand_total())
        color = "#008000" if value > 0 else "#999999"
        return format_html('<b style="color:{};">{:.2f}</b>', color, value)
    grand_total_display.short_description = "Grand Total"
