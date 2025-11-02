from decimal import Decimal
from rest_framework import serializers
from .models import Quotation, QuotationItem, QuotationInfo

# -----------------------------
# Quotation Item Serializer
# -----------------------------
class QuotationItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = QuotationItem
        fields = [
            'id', 'name', 'qty', 'rate', 'discount_type', 'discount_value',
            'unit', 'custom_unit', 'total_price',
        ]
        read_only_fields = ['id', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price


# -----------------------------
# Quotation Info Serializer
# -----------------------------
class QuotationInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationInfo
        fields = ['quotation_to', 'address', 'phone']


# -----------------------------
# Quotation Serializer (Main)
# -----------------------------
class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, required=False)
    info = QuotationInfoSerializer(required=False)

    subtotal = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    total_vat = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_number', 'lead_id', 'validity_date', 'version', 'status',
            'subtotal_discount', 'vat', 'terms_and_conditions', 'additional_notes',
            'created_at', 'updated_at', 'items', 'info',
            'subtotal', 'total_discount', 'total_vat', 'grand_total',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'quotation_number']

    # -----------------------------
    # Nested Create
    # -----------------------------
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        info_data = validated_data.pop('info', None)

        # Remove quotation_number if passed
        validated_data.pop('quotation_number', None)

        # Create instance and force-generate quotation_number
        quotation = Quotation(**validated_data)
        quotation.quotation_number = quotation.generate_quotation_number()
        quotation.save()

        # Create related items
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)

        # Create related info
        if info_data:
            QuotationInfo.objects.create(quotation=quotation, **info_data)

        return quotation

    # -----------------------------
    # Nested Update
    # -----------------------------
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        info_data = validated_data.pop('info', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update items
        if items_data is not None:
            existing_items = {item.id: item for item in instance.items.all()}
            for item_data in items_data:
                item_id = item_data.get('id')
                if item_id and item_id in existing_items:
                    item = existing_items[item_id]
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                else:
                    QuotationItem.objects.create(quotation=instance, **item_data)

        # Update info
        if info_data is not None:
            if hasattr(instance, 'info') and instance.info:
                for attr, value in info_data.items():
                    setattr(instance.info, attr, value)
                instance.info.save()
            else:
                QuotationInfo.objects.create(quotation=instance, **info_data)

        return instance

    # -----------------------------
    # Computed Fields
    # -----------------------------
    def get_subtotal(self, obj):
        return sum((item.rate * item.qty for item in obj.items.all()), Decimal('0.00'))

    def get_total_discount(self, obj):
        total_discount = Decimal('0.00')
        for item in obj.items.all():
            base = item.rate * item.qty
            if item.discount_type == 'percent':
                discount = base * item.discount_value / Decimal('100.00')
            else:
                discount = item.discount_value
            total_discount += min(discount, base)
        if obj.subtotal_discount:
            total_discount += Decimal(obj.subtotal_discount)
        return total_discount

    def get_total_vat(self, obj):
        subtotal_after_discount = self.get_subtotal(obj) - self.get_total_discount(obj)
        return subtotal_after_discount * obj.vat / Decimal('100.00')

    def get_grand_total(self, obj):
        subtotal_after_discount = self.get_subtotal(obj) - self.get_total_discount(obj)
        return subtotal_after_discount + self.get_total_vat(obj)
