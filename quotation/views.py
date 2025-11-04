import re
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Quotation
from .serializers import QuotationSerializer


VALID_NAME_REGEX = re.compile(r'^[A-Za-z0-9\s\-,.()]+$')


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all().order_by('-created_at')
    serializer_class = QuotationSerializer

    # ----------------------------------------
    # Approve Quotation
    # ----------------------------------------
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status in ['approved', 'closed']:
            return Response(
                {'error': 'Cannot approve a quotation in this status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        quotation.status = 'approved'
        quotation.save()
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ----------------------------------------
    # Close Quotation
    # ----------------------------------------
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status == 'draft':
            return Response(
                {'error': 'Cannot close a draft quotation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        quotation.status = 'closed'
        quotation.save()
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ----------------------------------------
    # Add Item to Quotation (JSON-based)
    # ----------------------------------------
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        quotation = self.get_object()
        data = request.data

        name = data.get('name', '').strip()
        qty = float(data.get('qty', 0))
        rate = float(data.get('rate', 0))
        discount_type = data.get('discount_type', 'percent')
        discount_value = float(data.get('discount_value', 0))
        unit = data.get('unit', '')
        custom_unit = data.get('custom_unit', '')

        # Validate name
        if not VALID_NAME_REGEX.match(name):
            return Response(
                {"error": "Invalid name. Only letters, numbers, spaces, hyphens, commas, periods, and parentheses are allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        item = {
            "id": len(quotation.items) + 1 if quotation.items else 1,
            "name": name,
            "qty": qty,
            "rate": rate,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "unit": unit,
            "custom_unit": custom_unit,
        }

        quotation.items = quotation.items or []
        quotation.items.append(item)
        quotation.save()

        return Response(
            {"message": "Item added successfully", "item": item},
            status=status.HTTP_201_CREATED
        )

    # ----------------------------------------
    # Remove Item from Quotation (by item_id)
    # ----------------------------------------
    @action(detail=True, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, pk=None, item_id=None):
        quotation = self.get_object()
        items = quotation.items or []

        new_items = [i for i in items if str(i.get("id")) != str(item_id)]

        if len(items) == len(new_items):
            return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)

        quotation.items = new_items
        quotation.save()

        return Response({"message": "Item removed successfully."}, status=status.HTTP_200_OK)

    # ----------------------------------------
    # Update Item (within JSON)
    # ----------------------------------------
    @action(detail=True, methods=['patch'], url_path='update-item/(?P<item_id>[^/.]+)')
    def update_item(self, request, pk=None, item_id=None):
        quotation = self.get_object()
        data = request.data
        items = quotation.items or []

        for item in items:
            if str(item.get("id")) == str(item_id):
                name = data.get('name', item['name']).strip()
                if not VALID_NAME_REGEX.match(name):
                    return Response(
                        {"error": "Invalid name. Only letters, numbers, spaces, hyphens, commas, periods, and parentheses are allowed."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                item['name'] = name
                item['qty'] = float(data.get('qty', item['qty']))
                item['rate'] = float(data.get('rate', item['rate']))
                item['discount_type'] = data.get('discount_type', item.get('discount_type', 'percent'))
                item['discount_value'] = float(data.get('discount_value', item.get('discount_value', 0)))
                item['unit'] = data.get('unit', item.get('unit', ''))
                item['custom_unit'] = data.get('custom_unit', item.get('custom_unit', ''))
                quotation.items = items
                quotation.save()
                return Response({"message": "Item updated successfully."}, status=status.HTTP_200_OK)

        return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
