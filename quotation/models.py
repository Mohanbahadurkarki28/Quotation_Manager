from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


# -----------------------------
# Main Quotation Model
# -----------------------------
class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.AutoField(primary_key=True)
    lead_id = models.IntegerField(null=True, blank=True)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    subtotal_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    vat = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('13.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Text fields
    terms_and_conditions = models.TextField(blank=True, null=True)
    additional_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Quotation #{self.id} ({self.status})"


# -----------------------------
# Quotation Item Model
# -----------------------------
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

    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Discount logic
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percent'),
        ('amount', 'Amount'),
    ]
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent'
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Unit: predefined or custom
    UNIT_CHOICES = [
        ('pcs', 'Piece'),
        ('m', 'Meter'),
    ]
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES, blank=True)
    custom_unit = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -----------------------------
    # Save and String Representation
    # -----------------------------
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Quotation #{self.quotation.id})"

    # -----------------------------
    # Helper Properties
    # -----------------------------
    @property
    def effective_unit(self):
        """Return the actual unit, custom if provided."""
        return self.custom_unit if self.custom_unit else self.unit

    @property
    def total_price(self):
        """Calculate total after discount safely using Decimal."""
        base = self.rate * self.qty
        if self.discount_type == 'percent':
            return base * (Decimal('1.00') - self.discount_value / Decimal('100.00'))
        else:  # amount
            return max(base - self.discount_value, Decimal('0.00'))


# -----------------------------
# Quotation Info Model
# -----------------------------
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
                regex=r'^\+(0?[1-9][0-9]{0,2})[- ]?\d{7,10}$',
                message="Phone number must be in one of these formats: '+9779814716361', '+977-9819191818', '+977 9819191818', '01-40000000', or '01xxxxxxx'."
            )
        ]
    )

    def __str__(self):
        return f"Info for Quotation #{self.quotation.id}"
