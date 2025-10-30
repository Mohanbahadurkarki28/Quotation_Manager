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
            'id',
            'name',
            'qty',
            'rate',
            'discount_type',
            'discount_value',
            'unit',
            'custom_unit',
            'total_price',
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
        fields = [
            'quotation_to',
            'address',
            'phone',
        ]


# -----------------------------
# Quotation Serializer (Main)
# -----------------------------
class QuotationSerializer(serializers.ModelSerializer):
    # Nested serializers
    items = QuotationItemSerializer(many=True, required=False)
    info = QuotationInfoSerializer(required=False)

    # Computed fields
    subtotal = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    total_vat = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id',
            'lead_id',
            'validation_date',
            'version',
            'status',
            'subtotal_discount',
            'vat',
            'terms_and_conditions',
            'additional_notes',
            'created_at',
            'updated_at',
            'items',
            'info',
            'subtotal',
            'total_discount',
            'total_vat',
            'grand_total',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    # -----------------------------
    # Nested Create
    # -----------------------------
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        info_data = validated_data.pop('info', None)

        quotation = Quotation.objects.create(**validated_data)

        # Create related QuotationItems
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)

        # Create related QuotationInfo if provided
        if info_data:
            QuotationInfo.objects.create(quotation=quotation, **info_data)

        return quotation

    # -----------------------------
    # Nested Update (optional but useful)
    # -----------------------------
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        info_data = validated_data.pop('info', None)

        # Update base fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle items update
        if items_data is not None:
            existing_items = {item.id: item for item in instance.items.all()}
            for item_data in items_data:
                item_id = item_data.get('id', None)
                if item_id and item_id in existing_items:
                    # Update existing item
                    item = existing_items[item_id]
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                else:
                    # Create new item
                    QuotationItem.objects.create(quotation=instance, **item_data)

        # Handle info update
        if info_data is not None:
            if hasattr(instance, 'info') and instance.info:
                for attr, value in info_data.items():
                    setattr(instance.info, attr, value)
                instance.info.save()
            else:
                QuotationInfo.objects.create(quotation=instance, **info_data)

        return instance

    # -----------------------------
    # Calculation Methods
    # -----------------------------
    def get_subtotal(self, obj):
        subtotal = sum((item.rate * item.qty for item in obj.items.all()), Decimal('0.00'))
        return subtotal

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
        vat_amount = subtotal_after_discount * obj.vat / Decimal('100.00')
        return vat_amount

    def get_grand_total(self, obj):
        subtotal_after_discount = self.get_subtotal(obj) - self.get_total_discount(obj)
        grand_total = subtotal_after_discount + self.get_total_vat(obj)
        return grand_total
