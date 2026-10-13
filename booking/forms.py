from django import forms
from .models import Booking, Table
from django.forms.widgets import DateInput, TimeInput

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['table', 'date', 'time']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'restaurant' in self.data and 'date' in self.data and 'time' in self.data:
            try:
                restaurant_id = int(self.data.get('restaurant'))
                date = self.data.get('date')
                time = self.data.get('time')

                booked_tables = Booking.objects.filter(
                    table__restaurant_id=restaurant_id,
                    date=date,
                    time=time
                ).values_list('table_id', flat=True)

                self.fields['table'].queryset = Table.objects.filter(restaurant_id=restaurant_id).exclude(id__in=booked_tables)

            except (ValueError, TypeError):
                pass  # fallback to default
        else:
            self.fields['table'].queryset = Table.objects.none()


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['restaurant', 'table_number', 'seats']