from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Quotation
from .serializers import QuotationSerializer

class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.prefetch_related('items').all().order_by('-created_at')
    serializer_class = QuotationSerializer

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
