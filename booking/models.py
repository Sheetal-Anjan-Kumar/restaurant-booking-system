from datetime import time as dtime

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    location = models.TextField()
    opening_time = models.TimeField(default=dtime(11, 0))
    closing_time = models.TimeField(default=dtime(23, 0))

    def __str__(self):
        return self.name

class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table_number = models.IntegerField()
    seats = models.IntegerField()

    def __str__(self):
        return f"{self.restaurant.name} - Table {self.table_number} ({self.seats} seats)"

class Booking(models.Model):
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_CONFIRMED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Only confirmed bookings block a table. Cancelled and completed ones don't.
        if self.status == self.STATUS_CONFIRMED:
            conflicts = Booking.objects.filter(
                table=self.table,
                date=self.date,
                time=self.time,
                status=self.STATUS_CONFIRMED
            )
            # Don't count this booking against itself when it is being updated
            if self.pk:
                conflicts = conflicts.exclude(pk=self.pk)
            if conflicts.exists():
                raise ValidationError('This table is already booked for the selected date and time.')

    def save(self, *args, **kwargs):
        self.clean()  # validate before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.table} on {self.date} ({self.get_status_display()})"