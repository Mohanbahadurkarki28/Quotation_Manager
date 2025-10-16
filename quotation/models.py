from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Sum, F, FloatField, ExpressionWrapper


class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('closed', 'Closed'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    subtotal_discount = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional text fields
    terms_and_conditions = models.TextField(blank=True, null=True)
    additional_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Quotation #{self.id} ({self.status})"

    # -------------------------------
    #  Totals and Calculations
    # -------------------------------
    def total_before_discount(self):
        return self.items.aggregate(
            total=Sum(F('qty') * F('rate'), output_field=FloatField())
        )['total'] or 0

    def total_discount(self):
        return self.items.aggregate(
            total=Sum(
                ExpressionWrapper(F('qty') * F('rate') * F('discount') / 100, output_field=FloatField())
            )
        )['total'] or 0

    def total_vat(self):
        return self.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('qty') * (F('rate') - (F('rate') * F('discount') / 100)) * F('vat') / 100,
                    output_field=FloatField()
                )
            )
        )['total'] or 0

    def grand_total(self):
        subtotal = self.total_before_discount()
        discount = self.total_discount()
        subtotal_after_discount = subtotal - discount - self.subtotal_discount
        vat = self.total_vat()
        return round(subtotal_after_discount + vat, 2)

    def save(self, *args, **kwargs):
        if self.status == 'closed' and self.pk:
            raise ValueError("Closed quotations cannot be modified.")
        super().save(*args, **kwargs)


class QuotationItem(models.Model):
    quotation = models.ForeignKey('Quotation', related_name='items', on_delete=models.CASCADE)

    name = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\s\-,.()]+$',
                message="Name can only contain letters, numbers, spaces, hyphens, commas, periods, and parentheses.",
                code='invalid_name'
            )
        ]
    )

    qty = models.FloatField(default=0, validators=[MinValueValidator(0)])
    rate = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    discount = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    vat = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    version = models.IntegerField(default=1)

    UNIT_CHOICES = [
        ('pcs', 'Piece'),
        ('m', 'Meter'),
    ]
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, blank=True)

    @property
    def total_price(self):
        subtotal = Decimal(self.qty) * self.rate
        discount_amount = subtotal * Decimal(self.discount) / 100
        subtotal_after_discount = subtotal - discount_amount
        vat_amount = subtotal_after_discount * Decimal(self.vat) / 100
        return round(subtotal_after_discount + vat_amount, 2)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Quotation #{self.quotation.id})"


class QuotationInfo(models.Model):
    quotation = models.OneToOneField(
        Quotation,
        related_name='info',
        on_delete=models.CASCADE
    )
    quotation_to = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    phone = models.CharField(
        max_length=25,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^(\+977[- ]?\d{7,10}|0\d{1,2}[- ]?\d{6,8})$',
                message="Phone number must be in one of these formats: '+9779814714838', '+977-9819191818', '+977 9819191818', '01-40000000', or '01xxxxxxx'."
            )
        ]
    )

    def __str__(self):
        return f"Info for Quotation #{self.quotation.id}"
