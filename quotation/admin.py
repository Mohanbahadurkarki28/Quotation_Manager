from decimal import Decimal
from django.contrib import admin
from django.utils.html import format_html
from .models import Quotation, QuotationItem, QuotationInfo

# --------------------------------------------
# Inline for Quotation Items
# --------------------------------------------
class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    min_num = 1
    max_num = 100
    can_delete = True

    readonly_fields = ('item_total',)
    fields = ('name', 'qty', 'rate', 'discount_type', 'discount_value', 'unit', 'custom_unit', 'item_total')

    def item_total(self, obj):
        """Display per-item total"""
        if obj and obj.pk:
            base = obj.rate * obj.qty
            if obj.discount_type == 'percent':
                total = base * (Decimal('1.00') - obj.discount_value / Decimal('100.00'))
            else:
                total = max(base - obj.discount_value, Decimal('0.00'))
            return f"{total:.2f}"
        return "-"
    item_total.short_description = "Item Total"

# --------------------------------------------
# Inline for Quotation Info
# --------------------------------------------
class QuotationInfoInline(admin.StackedInline):
    model = QuotationInfo
    extra = 0
    max_num = 1
    can_delete = False
    fields = ('quotation_to', 'address', 'phone')

# --------------------------------------------
# Main Quotation Admin
# --------------------------------------------
@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'quotation_number', 
        'lead_id',
        'validity_date',
        'status',
        'version',
        'subtotal_display',
        'discount_display',
        'vat_display',
        'grand_total_display',
        'created_at',
        'updated_at',
    )

    inlines = [QuotationInfoInline, QuotationItemInline]

    readonly_fields = (
        'quotation_number',
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
                'quotation_number', 
                'lead_id',
                'validity_date',
                'status',
                'version',
                'subtotal_discount',
                'vat',
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
    # Calculations
    # ----------------------------------------
    def get_items_queryset(self, obj):
        """Helper to get all items for a quotation"""
        return obj.items.all()

    @admin.display(description="Subtotal (Before Discounts)")
    def subtotal_display(self, obj):
        subtotal = sum((item.rate * item.qty for item in self.get_items_queryset(obj)), Decimal('0.00'))
        return f"{subtotal:.2f}"

    @admin.display(description="Total Discounts")
    def discount_display(self, obj):
        total_discount = Decimal('0.00')
        for item in self.get_items_queryset(obj):
            base = item.rate * item.qty
            if item.discount_type == 'percent':
                discount = base * item.discount_value / Decimal('100.00')
            else:
                discount = item.discount_value
            total_discount += min(discount, base) 
        # Include quotation-level discount if any
        if obj.subtotal_discount:
            total_discount += Decimal(obj.subtotal_discount)
        return f"{total_discount:.2f}"

    @admin.display(description="Total VAT")
    def vat_display(self, obj):
        subtotal_after_discount = sum(
            float(item.rate * item.qty) - (float(item.rate * item.qty) * float(item.discount_value)/100 if item.discount_type=='percent' else float(item.discount_value))
            for item in self.get_items_queryset(obj)
        )
        vat_amount = Decimal(subtotal_after_discount) * Decimal(obj.vat) / Decimal('100.00')
        return f"{vat_amount:.2f}"

    @admin.display(description="Grand Total")
    def grand_total_display(self, obj):
        subtotal = sum((item.rate * item.qty for item in self.get_items_queryset(obj)), Decimal('0.00'))
        total_discount = Decimal('0.00')
        for item in self.get_items_queryset(obj):
            base = item.rate * item.qty
            if item.discount_type == 'percent':
                discount = base * item.discount_value / Decimal('100.00')
            else:
                discount = item.discount_value
            total_discount += min(discount, base)
        if obj.subtotal_discount:
            total_discount += Decimal(obj.subtotal_discount)
        subtotal_after_discount = subtotal - total_discount
        vat_amount = subtotal_after_discount * Decimal(obj.vat) / Decimal('100.00')
        grand_total = subtotal_after_discount + vat_amount
        color = "#008000" if grand_total > 0 else "#999999"
        formatted_value = f"{grand_total:.2f}"
        return format_html('<b style="color:{};">{}</b>', color, formatted_value)
