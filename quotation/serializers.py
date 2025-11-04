from decimal import Decimal
from rest_framework import serializers
from .models import Quotation


class QuotationSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    total_vat = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_number', 'lead_id', 'validity_date', 'version', 'status',
            'subtotal_discount', 'vat', 'terms_and_conditions', 'additional_notes',
            'quotation_to', 'address', 'phone',  # <-- added directly
            'created_at', 'updated_at', 'items',
            'subtotal', 'total_discount', 'total_vat', 'grand_total',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'quotation_number']

    # -----------------------------
    # CREATE
    # -----------------------------
    def create(self, validated_data):
        # Remove quotation_number if passed manually
        validated_data.pop('quotation_number', None)

        quotation = Quotation(**validated_data)
        quotation.quotation_number = quotation.generate_quotation_number()
        quotation.save()
        return quotation

    # -----------------------------
    # UPDATE
    # -----------------------------
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    # -----------------------------
    # COMPUTED FIELDS
    # -----------------------------
    def get_subtotal(self, obj):
        """Sum of all (rate * qty) from items JSON."""
        if not obj.items:
            return Decimal('0.00')
        return sum(
            (Decimal(str(item.get('rate', 0))) * Decimal(str(item.get('qty', 0))))
            for item in obj.items
        )

    def get_total_discount(self, obj):
        """Sum of all item-level and subtotal discounts."""
        total_discount = Decimal('0.00')
        if obj.items:
            for item in obj.items:
                rate = Decimal(str(item.get('rate', 0)))
                qty = Decimal(str(item.get('qty', 0)))
                base = rate * qty
                discount_type = item.get('discount_type', 'percent')
                discount_value = Decimal(str(item.get('discount_value', 0)))

                if discount_type == 'percent':
                    discount = base * discount_value / Decimal('100.00')
                else:
                    discount = discount_value

                total_discount += min(discount, base)

        if obj.subtotal_discount:
            total_discount += Decimal(obj.subtotal_discount)
        return total_discount

    def get_total_vat(self, obj):
        """VAT applied after discounts."""
        subtotal_after_discount = self.get_subtotal(obj) - self.get_total_discount(obj)
        vat_percent = Decimal(str(obj.vat)) if obj.vat else Decimal('0.00')
        return subtotal_after_discount * vat_percent / Decimal('100.00')

    def get_grand_total(self, obj):
        """Final grand total."""
        subtotal_after_discount = self.get_subtotal(obj) - self.get_total_discount(obj)
        return subtotal_after_discount + self.get_total_vat(obj)
