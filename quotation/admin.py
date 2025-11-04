from django.contrib import admin
from django import forms
from .models import Quotation
from django_json_widget.widgets import JSONEditorWidget 
from decimal import Decimal


# ==============================
# Custom Form for Quotation
# ==============================
class QuotationAdminForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = '__all__'
        widgets = {
            # Use pretty JSON editor for the items field
            'items': JSONEditorWidget(options={'mode': 'tree', 'search': True}),
        }

    def clean_items(self):
        """Validate and normalize JSON structure for items."""
        items = self.cleaned_data.get('items', [])
        if not isinstance(items, list):
            raise forms.ValidationError("Items must be a list of dictionaries.")
        for i, item in enumerate(items):
            required_keys = ["name", "qty", "rate", "discount_type", "discount_value", "unit", "custom_unit"]
            for key in required_keys:
                if key not in item:
                    raise forms.ValidationError(f"Item {i+1}: Missing key '{key}'.")
        return items


# ==============================
# Admin for Quotation
# ==============================
@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    form = QuotationAdminForm
    list_display = (
        'quotation_number', 'lead_id', 'quotation_to',
        'status', 'subtotal_discount', 'vat', 'validity_date'
    )
    readonly_fields = ('quotation_number', 'created_at', 'updated_at')

    # Optional extras
    search_fields = ('quotation_number', 'lead_id', 'quotation_to')
    list_filter = ('status', 'validity_date')
    ordering = ('-created_at',)

    fieldsets = (
        ('Quotation Details', {
            'fields': ('quotation_number', 'lead_id', 'status', 'version', 'validity_date')
        }),
        ('Customer Info', {
            'fields': ('quotation_to', 'address', 'phone')
        }),
        ('Financial Details', {
            'fields': ('subtotal_discount', 'vat', 'terms_and_conditions', 'additional_notes')
        }),
        ('Items', {
            'fields': ('items',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
