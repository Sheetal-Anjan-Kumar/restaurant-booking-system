from django.contrib import admin
from .models import Restaurant, Table, Booking


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'opening_time', 'closing_time')
    search_fields = ('name', 'location')


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'table_number', 'seats')
    list_filter = ('restaurant',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'table', 'guests', 'date', 'time', 'status', 'created_at')
    list_filter = ('status', 'date', 'table__restaurant')
    search_fields = ('user__username',)
    ordering = ('-date', '-time')
    actions = ['mark_completed', 'mark_cancelled']

    @admin.action(description="Mark selected bookings as Completed")
    def mark_completed(self, request, queryset):
        updated = queryset.update(status=Booking.STATUS_COMPLETED)
        self.message_user(request, f"{updated} booking(s) marked as Completed.")

    @admin.action(description="Mark selected bookings as Cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status=Booking.STATUS_CANCELLED)
        self.message_user(request, f"{updated} booking(s) marked as Cancelled.")