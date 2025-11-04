import re
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Quotation, QuotationItem
from .serializers import QuotationSerializer

# Allowed characters: letters, numbers, spaces, hyphens, commas, periods, and parentheses
VALID_NAME_REGEX = re.compile(r'^[A-Za-z0-9\s\-,.()]+$')


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.prefetch_related('items').all().order_by('-created_at')
    serializer_class = QuotationSerializer

    # ----------------------------------------
    # Approve Quotation
    # ----------------------------------------
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status in ['approved', 'closed']:
            return Response({'error': 'Cannot approve a quotation in this status.'},
                            status=status.HTTP_400_BAD_REQUEST)

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
            return Response({'error': 'Cannot close a draft quotation.'},
                            status=status.HTTP_400_BAD_REQUEST)

        quotation.status = 'closed'
        quotation.save()
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ----------------------------------------
    # Add Item to Quotation
    # ----------------------------------------
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """
        Add an item to a quotation. Validates name and handles manual/custom units.
        """
        quotation = self.get_object()
        data = request.data

        name = data.get('name', '').strip()
        qty = data.get('qty', 0)
        rate = data.get('rate', 0)
        discount = data.get('discount', 0)
        unit = data.get('unit', '')       
        custom_unit = data.get('custom_unit', '') 

        # --- Validate name ---
        if not VALID_NAME_REGEX.match(name):
            return Response(
                {"error": "Invalid name. Only letters, numbers, spaces, hyphens, commas, periods, and parentheses are allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            item = QuotationItem.objects.create(
                quotation=quotation,
                name=name,
                qty=qty,
                rate=rate,
                discount=discount,
                unit=unit,
                custom_unit=custom_unit
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Item added successfully", "item_id": item.id},
            status=status.HTTP_201_CREATED
        )

    # ----------------------------------------
    # Remove Item from Quotation
    # ----------------------------------------
    @action(detail=True, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, pk=None, item_id=None):
        quotation = self.get_object()
        try:
            item = quotation.items.get(id=item_id)
            item.delete()
            return Response({"message": "Item removed successfully."}, status=status.HTTP_200_OK)
        except QuotationItem.DoesNotExist:
            return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)

    # ----------------------------------------
    # Update Item
    # ----------------------------------------
    @action(detail=True, methods=['patch'], url_path='update-item/(?P<item_id>[^/.]+)')
    def update_item(self, request, pk=None, item_id=None):
        quotation = self.get_object()
        data = request.data

        try:
            item = quotation.items.get(id=item_id)
        except QuotationItem.DoesNotExist:
            return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)

        name = data.get('name', item.name).strip()
        qty = data.get('qty', item.qty)
        rate = data.get('rate', item.rate)
        discount = data.get('discount', item.discount)
        unit = data.get('unit', item.unit)
        custom_unit = data.get('custom_unit', item.custom_unit)

        if not VALID_NAME_REGEX.match(name):
            return Response(
                {"error": "Invalid name. Only letters, numbers, spaces, hyphens, commas, periods, and parentheses are allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.name = name
        item.qty = qty
        item.rate = rate
        item.discount = discount
        item.unit = unit
        item.custom_unit = custom_unit
        item.save()

        return Response({"message": "Item updated successfully."}, status=status.HTTP_200_OK)
