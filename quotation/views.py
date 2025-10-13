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

    # --- Existing actions ---
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status in ['approved', 'closed']:
            return Response({'error': 'Cannot approve a quotation in this status.'}, status=status.HTTP_400_BAD_REQUEST)

        quotation.status = 'approved'
        quotation.save()
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status == 'draft':
            return Response({'error': 'Cannot close a draft quotation.'}, status=status.HTTP_400_BAD_REQUEST)

        quotation.status = 'closed'
        quotation.save()
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ---  New secure method to add an item ---
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """
        Blocks names with special characters to prevent SQL injection and XSS.
        """
        quotation = self.get_object()
        data = request.data

        name = data.get('name', '').strip()
        qty = data.get('qty', 0)
        rate = data.get('rate', 0)
        discount = data.get('discount', 0)
        vat = data.get('vat', 0)
        unit = data.get('unit', 'pcs')

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
                vat=vat,
                unit=unit
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Item added successfully", "item_id": item.id},
            status=status.HTTP_201_CREATED
        )
