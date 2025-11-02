from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from datetime import date, timedelta
from nepali_datetime import date as nep_date 
from django.db import transaction


class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.AutoField(primary_key=True)
    quotation_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    lead_id = models.IntegerField(null=True, blank=True)
    validity_date = models.DateField(null=True, blank=True)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    subtotal_discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    vat = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('13.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('99.00'))]
    )

    terms_and_conditions = models.TextField(blank=True, null=True)
    additional_notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -----------------------------
    # Nepali Fiscal Year Helper
    # -----------------------------
    @staticmethod
    def get_current_fiscal_year():
        today_np = nep_date.today()
        year = today_np.year
        month = today_np.month

        if month < 4:
            start_year = year - 1
            end_year = year
        else:
            start_year = year
            end_year = year + 1

        start_short = str(start_year)[-3:]
        end_short = str(end_year)[-2:]
        return f"{start_short}/{end_short}"

    # -----------------------------
    # Generate Quotation Number
    # -----------------------------
    def generate_quotation_number(self):
        fiscal_year = self.get_current_fiscal_year()
        prefix = f"Q-{fiscal_year}"

        with transaction.atomic():
            last_q = Quotation.objects.select_for_update().filter(
                quotation_number__startswith=prefix
            ).order_by('-id').first()

            last_num = 0
            if last_q and last_q.quotation_number:
                try:
                    last_num = int(last_q.quotation_number.split('-')[-1])
                except (IndexError, ValueError):
                    last_num = 0

            new_num = last_num + 1

            # Ensure uniqueness
            while Quotation.objects.filter(quotation_number=f"{prefix}-{new_num}").exists():
                new_num += 1

            return f"{prefix}-{new_num}"

    # -----------------------------
    # Auto-generate quotation_number and validity_date
    # -----------------------------
    def save(self, *args, **kwargs):
        if not self.quotation_number:
            self.quotation_number = self.generate_quotation_number()
        if not self.validity_date:
            self.validity_date = date.today() + timedelta(days=14)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quotation_number or 'Quotation'} - Lead #{self.lead_id or 'N/A'} ({self.status})"

    class Meta:
        indexes = [
            models.Index(fields=['quotation_number']),
            models.Index(fields=['lead_id']),
        ]


# -----------------------------
# Quotation Item Model
# -----------------------------
class QuotationItem(models.Model):
    quotation = models.ForeignKey('Quotation', related_name='items', on_delete=models.CASCADE)

    name = models.CharField(
        max_length=255,
        validators=[RegexValidator(
            regex=r'^[A-Za-z0-9\s\-,.()]+$',
            message="Name can only contain letters, numbers, spaces, hyphens, commas, periods, and parentheses.",
        )]
    )

    qty = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percent'),
        ('amount', 'Amount'),
    ]
    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent'
    )
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    UNIT_CHOICES = [
        ('pcs', 'Piece'),
        ('m', 'Meter'),
    ]
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES, blank=True)
    custom_unit = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Quotation #{self.quotation.id})"

    @property
    def effective_unit(self):
        return self.custom_unit if self.custom_unit else self.unit

    @property
    def total_price(self):
        base = self.rate * self.qty
        if self.discount_type == 'percent':
            return base * (Decimal('1.00') - self.discount_value / Decimal('100.00'))
        else:
            return max(base - self.discount_value, Decimal('0.00'))


# -----------------------------
# Quotation Info Model
# -----------------------------
class QuotationInfo(models.Model):
    quotation = models.OneToOneField(
        Quotation, related_name='info', on_delete=models.CASCADE
    )
    quotation_to = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    phone = models.CharField(
        max_length=25, blank=True, null=True,
        validators=[RegexValidator(
            regex=r'^\+(0?[1-9][0-9]{0,2})[- ]?\d{7,10}$',
            message="Phone number must be valid."
        )]
    )

    def __str__(self):
        return f"Info for Quotation #{self.quotation.id}"
