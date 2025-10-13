from rest_framework import serializers
from decimal import Decimal
from .models import Quotation, QuotationItem
import re


class QuotationItemSerializer(serializers.ModelSerializer):
    rate = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = QuotationItem
        fields = '__all__'
        read_only_fields = ['id', 'quotation']

    # Validation for name (no special characters)
    def validate_name(self, value):
        if not re.match(r'^[A-Za-z0-9\s\-,.()]+$', value):
            raise serializers.ValidationError(
                "Name can only contain letters, numbers, spaces, hyphens, commas, periods, and parentheses."
            )
        return value



class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)
    
    # Computed read-only fields
    total_before_discount = serializers.SerializerMethodField()
    total_discount = serializers.SerializerMethodField()
    total_vat = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'status', 'subtotal_discount', 'items',
            'created_at', 'updated_at',
            'total_before_discount', 'total_discount', 'total_vat', 'grand_total'
        ]


    def get_total_before_discount(self, obj):
        return obj.total_before_discount()

    def get_total_discount(self, obj):
        return obj.total_discount()

    def get_total_vat(self, obj):
        return obj.total_vat()

    def get_grand_total(self, obj):
        return obj.grand_total()


    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        quotation = Quotation.objects.create(**validated_data)
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)
        return quotation


    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # Update quotation fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            existing_ids = [item.id for item in instance.items.all()]
            incoming_ids = [item.get('id') for item in items_data if item.get('id')]

            # Delete items not in incoming data
            for item in instance.items.exclude(id__in=incoming_ids):
                item.delete()

            # Create or update items
            for item_data in items_data:
                item_id = item_data.get('id', None)
                if item_id and item_id in existing_ids:
                    # Update existing item
                    item_instance = QuotationItem.objects.get(id=item_id, quotation=instance)
                    for attr, value in item_data.items():
                        setattr(item_instance, attr, value)
                    item_instance.save()
                else:
                    # Create new item
                    QuotationItem.objects.create(quotation=instance, **item_data)

        return instance
