from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator
)
from decimal import Decimal
from datetime import date, timedelta
from nepali_datetime import date as nep_date
import re


class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # -----------------------------
    # Basic Quotation Fields
    # -----------------------------
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

    # -----------------------------
    # Quotation Info Fields
    # -----------------------------
    quotation_to = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(
        max_length=25, blank=True, null=True,
        validators=[RegexValidator(
            regex=r'^\+(0?[1-9][0-9]{0,2})[- ]?\d{7,10}$',
            message="Phone number must be valid."
        )]
    )

    # -----------------------------
    # Quotation Items (as JSON)
    # -----------------------------
    items = models.JSONField(default=list)  

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    VALID_NAME_REGEX = re.compile(r"^[A-Za-z0-9\s\-\.,'()]+$")

    # -----------------------------
    # Fiscal Year Helper
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
            while Quotation.objects.filter(quotation_number=f"{prefix}-{new_num}").exists():
                new_num += 1

            return f"{prefix}-{new_num}"

    # -----------------------------
    # Validation for items + discounts
    # -----------------------------
    def clean_items(self):
        """Validate each item in JSON list."""
        for i, data in enumerate(self.items):
            required_keys = ["name", "qty", "rate", "discount_type", "discount_value", "unit", "custom_unit"]
            for key in required_keys:
                if key not in data:
                    raise ValidationError(f"Item {i+1}: Missing key '{key}'")

            name = data.get("name", "").strip()
            if not self.VALID_NAME_REGEX.match(name):
                raise ValidationError(f"Item {i+1}: Invalid name format.")

            try:
                qty = Decimal(str(data.get("qty", "0.00")))
                rate = Decimal(str(data.get("rate", "0.00")))
            except Exception:
                raise ValidationError(f"Item {i+1}: Quantity and rate must be valid decimal numbers.")

            if qty < 0 or rate < 0:
                raise ValidationError(f"Item {i+1}: Quantity and rate cannot be negative.")

            discount_type = data.get("discount_type")
            discount_value = Decimal(str(data.get("discount_value", "0.00")))

            if discount_type not in ["percent", "amount"]:
                raise ValidationError(f"Item {i+1}: Invalid discount type. Must be 'percent' or 'amount'.")
            if discount_value < 0:
                raise ValidationError(f"Item {i+1}: Discount value cannot be negative.")

            if self.subtotal_discount > 0 and discount_value > 0:
                raise ValidationError("Cannot apply both subtotal discount and item discount value.")

    def clean(self):
        super().clean()
        self.clean_items()

    # -----------------------------
    # Auto save handlers
    # -----------------------------
    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.quotation_number:
            self.quotation_number = self.generate_quotation_number()
        if not self.validity_date:
            self.validity_date = date.today() + timedelta(days=14)

        # Normalize item names
        for item in self.items:
            if "name" in item:
                item["name"] = item["name"].strip().title()

        super().save(*args, **kwargs)

    # -----------------------------
    # Utility Calculations
    # -----------------------------
    def item_total(self, item):
        qty = Decimal(str(item.get("qty", "0.00")))
        rate = Decimal(str(item.get("rate", "0.00")))
        discount_type = item.get("discount_type", "percent")
        discount_value = Decimal(str(item.get("discount_value", "0.00")))

        base = qty * rate
        if discount_type == "percent":
            return base * (Decimal("1.00") - discount_value / Decimal("100.00"))
        else:
            return max(base - discount_value, Decimal("0.00"))

    def grand_total(self):
        total = sum(self.item_total(item) for item in self.items)
        if self.subtotal_discount > 0:
            total -= total * (self.subtotal_discount / Decimal("100.00"))
        vat_amount = total * (self.vat / Decimal("100.00"))
        return total + vat_amount

    def __str__(self):
        return f"{self.quotation_number or 'Quotation'} - Lead #{self.lead_id or 'N/A'} ({self.status})"

    class Meta:
        indexes = [
            models.Index(fields=['quotation_number']),
            models.Index(fields=['lead_id']),
        ]
