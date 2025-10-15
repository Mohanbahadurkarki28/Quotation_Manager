from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from .models import Quotation, QuotationItem
import re


# -----------------------------
# Quotation Item Serializer
# -----------------------------
class QuotationItemSerializer(serializers.ModelSerializer):
    rate = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QuotationItem
        fields = [
            'id', 'quotation', 'name', 'qty', 'rate',
            'discount', 'vat', 'unit', 'version', 'total_price'
        ]
        read_only_fields = ['id', 'quotation', 'total_price']

    # --- Validation ---
    def validate_name(self, value):
        """Only allow alphanumeric + limited punctuation."""
        if not re.match(r'^[A-Za-z0-9\s\-,.()]+$', value):
            raise serializers.ValidationError(
                "Name can only contain letters, numbers, spaces, hyphens, commas, periods, and parentheses."
            )
        return value.strip()

    # --- Computed total ---
    def get_total_price(self, obj):
        """Return total = (rate - discount%) * qty + VAT."""
        rate = Decimal(obj.rate)
        qty = Decimal(obj.qty)
        discount = Decimal(obj.discount or 0)
        vat = Decimal(obj.vat or 0)

        discounted_rate = rate * (Decimal('1.0') - discount / Decimal('100'))
        subtotal = qty * discounted_rate
        vat_amount = subtotal * (vat / Decimal('100'))
        total = subtotal + vat_amount

        # Round to 2 decimal places
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# -----------------------------
# Quotation Serializer
# -----------------------------
class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)

    # Computed read-only totals
    total_before_discount = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    total_vat = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'status', 'subtotal_discount', 'items',
            'created_at', 'updated_at',
            'total_before_discount', 'total_discount', 'total_vat', 'grand_total',
        ]

    # --- Computed total fields ---
    def get_total_before_discount(self, obj):
        return obj.total_before_discount()

    def get_total_discount(self, obj):
        return obj.total_discount()

    def get_total_vat(self, obj):
        return obj.total_vat()

    def get_grand_total(self, obj):
        return obj.grand_total()

    # --- Create ---
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        quotation = Quotation.objects.create(**validated_data)
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)
        return quotation

    # --- Update (safe for partial updates) ---
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # Update quotation fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle nested items
        if items_data is not None:
            existing_items = {item.id: item for item in instance.items.all()}

            for item_data in items_data:
                item_id = item_data.get('id')
                if item_id and item_id in existing_items:
                    # Update existing item
                    item_instance = existing_items[item_id]
                    for attr, value in item_data.items():
                        setattr(item_instance, attr, value)
                    item_instance.save()
                else:
                    # Create new item
                    QuotationItem.objects.create(quotation=instance, **item_data)

            # Delete items not present in the update
            current_ids = [i.get('id') for i in items_data if i.get('id')]
            for old_item in instance.items.exclude(id__in=current_ids):
                old_item.delete()

        return instance
