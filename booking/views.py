from datetime import datetime, timedelta

import pandas as pd
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import Restaurant, Table, Booking

# Booking settings (change these numbers if you want different slots)
SLOT_MINUTES = 30       # a new time slot every 30 minutes
BOOKING_MINUTES = 90    # each booking holds the table for 90 minutes


def generate_slots(restaurant):
    """All start times from opening time up to (not including) closing time."""
    today = datetime.today().date()
    current = datetime.combine(today, restaurant.opening_time)
    end = datetime.combine(today, restaurant.closing_time)
    step = timedelta(minutes=SLOT_MINUTES)

    slots = []
    while current < end:
        slots.append(current.time())
        current += step
    return slots


def table_is_free(table, booking_date, booking_time, exclude_id=None):
    """False if a confirmed booking on this table is within 90 minutes of the new time."""
    start = datetime.combine(booking_date, booking_time)
    window = timedelta(minutes=BOOKING_MINUTES)

    others = Booking.objects.filter(
        table=table,
        date=booking_date,
        status=Booking.STATUS_CONFIRMED
    )
    if exclude_id:
        others = others.exclude(id=exclude_id)

    for other in others:
        other_start = datetime.combine(other.date, other.time)
        if abs(other_start - start) < window:
            return False
    return True


def mark_past_bookings_completed():
    """Confirmed bookings whose date/time has passed become Completed."""
    now = datetime.now()
    Booking.objects.filter(status=Booking.STATUS_CONFIRMED).filter(
        Q(date__lt=now.date()) | Q(date=now.date(), time__lt=now.time())
    ).update(status=Booking.STATUS_COMPLETED)


def home(request):
    return render(request, 'home.html')


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def restaurant_list(request):
    restaurants = Restaurant.objects.all()
    data = []

    for restaurant in restaurants:
        tables = Table.objects.filter(restaurant=restaurant)
        data.append({
            'restaurant': restaurant,
            'tables': tables
        })

    return render(request, 'restaurant_list.html', {'data': data})


@login_required
def get_time_slots(request, table_id):
    """Returns the time slots for a table on a date, marking the ones already taken.

    When rescheduling, ?exclude=<booking id> stops the booking's own slot
    from being counted as taken.
    """
    table = get_object_or_404(Table, pk=table_id)

    try:
        booking_date = datetime.strptime(request.GET.get('date', ''), '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'slots': []})

    # Only ignore a booking that belongs to the logged-in user
    exclude_id = None
    exclude_param = request.GET.get('exclude')
    if exclude_param and exclude_param.isdigit():
        if Booking.objects.filter(id=int(exclude_param), user=request.user).exists():
            exclude_id = int(exclude_param)

    now = datetime.now()
    result = []
    for slot in generate_slots(table.restaurant):
        # Hide slots that have already passed
        if datetime.combine(booking_date, slot) < now:
            continue
        result.append({
            'value': slot.strftime('%H:%M'),
            'label': slot.strftime('%I:%M %p').lstrip('0'),
            'available': table_is_free(table, booking_date, slot, exclude_id=exclude_id),
        })

    return JsonResponse({'slots': result})


@login_required
def book_table(request, table_id):
    table = get_object_or_404(Table, pk=table_id)
    restaurant = table.restaurant

    # Clear old messages when opening the booking page
    if request.method == 'GET':
        list(messages.get_messages(request))

    if request.method == 'POST':
        date = request.POST.get('date')
        time = request.POST.get('time')
        guests = request.POST.get('guests')

        # Values to refill the form if there is an error
        context = {
            'table': table,
            'restaurant': restaurant,
            'date_value': date,
            'time_value': time,
            'guests_value': guests,
        }

        # Check if date or time is empty
        if not date or not time:
            messages.error(
                request,
                "Please select both date and time before booking."
            )
            return render(request, 'book_table.html', context)

        # Check the number of guests
        try:
            guests = int(guests)
        except (TypeError, ValueError):
            messages.error(request, "Please enter a valid number of guests.")
            return render(request, 'book_table.html', context)

        if guests < 1:
            messages.error(request, "Number of guests must be at least 1.")
            return render(request, 'book_table.html', context)

        if guests > table.seats:
            messages.error(
                request,
                f"This table seats {table.seats} guests at most. "
                f"Please choose a bigger table for {guests} guests."
            )
            return render(request, 'book_table.html', context)

        # Convert the submitted values to proper date/time objects
        try:
            booking_date = datetime.strptime(date, '%Y-%m-%d').date()
            booking_time = datetime.strptime(time, '%H:%M').time()
        except ValueError:
            messages.error(
                request,
                "Please enter a valid date and time."
            )
            return render(request, 'book_table.html', context)

        # Don't allow bookings in the past
        if datetime.combine(booking_date, booking_time) < datetime.now():
            messages.error(
                request,
                "You can't book a table in the past. Please choose a future date and time."
            )
            return render(request, 'book_table.html', context)

        # The time must be one of the restaurant's slots (this also enforces opening hours)
        if booking_time not in generate_slots(restaurant):
            messages.error(
                request,
                f"{restaurant.name} is open from "
                f"{restaurant.opening_time.strftime('%I:%M %p')} to "
                f"{restaurant.closing_time.strftime('%I:%M %p')}. "
                f"Please choose a time from the list."
            )
            return render(request, 'book_table.html', context)

        # Check that no other booking overlaps this one (cancelled bookings don't count)
        if not table_is_free(table, booking_date, booking_time):
            messages.error(
                request,
                f"This table is already booked around that time. Each booking holds "
                f"the table for {BOOKING_MINUTES} minutes. Please choose another slot."
            )
            return render(request, 'book_table.html', context)

        Booking.objects.create(
            table=table,
            user=request.user,
            date=booking_date,
            time=booking_time,
            guests=guests
        )

        # Go to the booking success page
        return redirect('booking_success')

    return render(request, 'book_table.html', {
        'table': table,
        'restaurant': restaurant
    })


def booking_success(request):
    return render(request, 'booking_success.html')


def get_available_tables(request):
    restaurant_id = request.GET.get('restaurant')
    date = request.GET.get('date')
    time = request.GET.get('time')

    # Get all tables for that restaurant
    tables = Table.objects.filter(restaurant_id=restaurant_id)

    # Tables with a confirmed booking at that date/time (cancelled ones don't block)
    booked_tables = Booking.objects.filter(
        date=date,
        time=time,
        table__restaurant_id=restaurant_id,
        status=Booking.STATUS_CONFIRMED
    ).values_list('table_id', flat=True)

    # Filter available tables
    available_tables = tables.exclude(id__in=booked_tables)

    data = {
        'tables': [
            {'id': table.id, 'number': table.table_number, 'seats': table.seats}
            for table in available_tables
        ]
    }

    return JsonResponse(data)


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if request.method == "POST" and booking.status == Booking.STATUS_CONFIRMED:
        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        messages.success(request, "Booking cancelled.")
    return redirect('my_bookings')


@login_required
def reschedule_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    table = booking.table
    restaurant = table.restaurant

    # Only confirmed, upcoming bookings can be rescheduled
    if booking.status != Booking.STATUS_CONFIRMED:
        messages.error(request, "Only confirmed bookings can be rescheduled.")
        return redirect('my_bookings')

    if datetime.combine(booking.date, booking.time) < datetime.now():
        messages.error(request, "This booking has already passed and can't be rescheduled.")
        return redirect('my_bookings')

    # Clear old messages when opening the page
    if request.method == 'GET':
        list(messages.get_messages(request))

    context = {
        'booking': booking,
        'table': table,
        'restaurant': restaurant,
        'date_value': booking.date.strftime('%Y-%m-%d'),
        'time_value': booking.time.strftime('%H:%M'),
        'guests_value': booking.guests,
    }

    if request.method == 'POST':
        date = request.POST.get('date')
        time = request.POST.get('time')
        guests = request.POST.get('guests')

        # Refill the form with what the user typed if there is an error
        context.update({
            'date_value': date,
            'time_value': time,
            'guests_value': guests,
        })

        if not date or not time:
            messages.error(request, "Please select both date and time.")
            return render(request, 'reschedule_booking.html', context)

        try:
            guests = int(guests)
        except (TypeError, ValueError):
            messages.error(request, "Please enter a valid number of guests.")
            return render(request, 'reschedule_booking.html', context)

        if guests < 1:
            messages.error(request, "Number of guests must be at least 1.")
            return render(request, 'reschedule_booking.html', context)

        if guests > table.seats:
            messages.error(
                request,
                f"This table seats {table.seats} guests at most."
            )
            return render(request, 'reschedule_booking.html', context)

        try:
            new_date = datetime.strptime(date, '%Y-%m-%d').date()
            new_time = datetime.strptime(time, '%H:%M').time()
        except ValueError:
            messages.error(request, "Please enter a valid date and time.")
            return render(request, 'reschedule_booking.html', context)

        if datetime.combine(new_date, new_time) < datetime.now():
            messages.error(
                request,
                "You can't move a booking to the past. Please choose a future date and time."
            )
            return render(request, 'reschedule_booking.html', context)

        if new_time not in generate_slots(restaurant):
            messages.error(
                request,
                f"{restaurant.name} is open from "
                f"{restaurant.opening_time.strftime('%I:%M %p')} to "
                f"{restaurant.closing_time.strftime('%I:%M %p')}. "
                f"Please choose a time from the list."
            )
            return render(request, 'reschedule_booking.html', context)

        # This booking itself doesn't count as a clash
        if not table_is_free(table, new_date, new_time, exclude_id=booking.id):
            messages.error(
                request,
                f"This table is already booked around that time. Each booking holds "
                f"the table for {BOOKING_MINUTES} minutes. Please choose another slot."
            )
            return render(request, 'reschedule_booking.html', context)

        booking.date = new_date
        booking.time = new_time
        booking.guests = guests
        booking.save()

        messages.success(request, "Booking rescheduled.")
        return redirect('my_bookings')

    return render(request, 'reschedule_booking.html', context)


@login_required
def my_bookings(request):
    mark_past_bookings_completed()
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('table__restaurant')
        .order_by('-date', '-time')
    )
    return render(request, 'my_bookings.html', {'bookings': bookings})


@staff_member_required
def admin_panel(request):
    return render(request, 'admin_panel.html')


def get_filtered_bookings(request):
    """Shared filter used by the report page and both exports."""
    mark_past_bookings_completed()

    restaurant_id = request.GET.get('restaurant')
    report_type = request.GET.get('report_type')
    status = request.GET.get('status')

    bookings = Booking.objects.select_related('user', 'table__restaurant')

    if restaurant_id:
        bookings = bookings.filter(table__restaurant__id=restaurant_id)

    # Status: blank = hide cancelled, "all" = everything, otherwise that status only
    if status == 'all':
        pass
    elif status in (Booking.STATUS_CONFIRMED, Booking.STATUS_CANCELLED, Booking.STATUS_COMPLETED):
        bookings = bookings.filter(status=status)
    else:
        bookings = bookings.exclude(status=Booking.STATUS_CANCELLED)

    today = datetime.today().date()
    if report_type == 'daily':
        # Bookings dated today
        bookings = bookings.filter(date=today)
    elif report_type == 'weekly':
        # Bookings from the last 7 days, up to today
        week_ago = today - timedelta(days=7)
        bookings = bookings.filter(date__range=[week_ago, today])
    elif report_type == 'upcoming':
        # Bookings from today through the next 7 days
        next_week = today + timedelta(days=7)
        bookings = bookings.filter(date__range=[today, next_week])

    return bookings


@staff_member_required
def admin_booking_report(request):
    restaurants = Restaurant.objects.all()
    bookings = get_filtered_bookings(request)

    return render(request, 'admin_booking_report.html', {
        'bookings': bookings,
        'restaurants': restaurants,
        'selected_restaurant': request.GET.get('restaurant'),
        'report_type': request.GET.get('report_type'),
        'status': request.GET.get('status', ''),
    })


@staff_member_required
def export_excel(request):
    bookings = get_filtered_bookings(request)

    data = []
    for booking in bookings:
        data.append({
            "User": booking.user.username,
            "Restaurant": booking.table.restaurant.name,
            "Table": booking.table.table_number,
            "Guests": booking.guests,
            "Date": booking.date,
            "Time": booking.time,
            "Status": booking.get_status_display(),
        })

    df = pd.DataFrame(
        data,
        columns=["User", "Restaurant", "Table", "Guests", "Date", "Time", "Status"]
    )

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="bookings.xlsx"'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Bookings')
        sheet = writer.sheets['Bookings']

        # Auto-fit column widths so dates and times are fully visible
        for column_cells in sheet.columns:
            longest = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )
            sheet.column_dimensions[column_cells[0].column_letter].width = longest + 4

    return response


@staff_member_required
def export_pdf(request):
    bookings = get_filtered_bookings(request)

    template_path = 'export_pdf.html'
    context = {'bookings': bookings}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bookings.pdf"'
    html = get_template(template_path).render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation error <pre>' + html + '</pre>')
    return response


@staff_member_required
def manage_tables(request):
    selected_restaurant_id = request.GET.get('restaurant')
    restaurants = Restaurant.objects.all()
    tables = Table.objects.none()

    if selected_restaurant_id:
        tables = Table.objects.filter(restaurant_id=selected_restaurant_id)

    context = {
        'restaurants': restaurants,
        'tables': tables,
        'selected_restaurant_id': selected_restaurant_id
    }
    return render(request, 'manage_tables.html', context)


@staff_member_required
def add_table(request):
    restaurants = Restaurant.objects.all()
    if request.method == 'POST':
        restaurant_id = request.POST.get('restaurant')
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        try:
            table_number = int(request.POST.get('table_number'))
            seats = int(request.POST.get('seats'))
        except (TypeError, ValueError):
            messages.error(request, "Table number and seats must be numbers.")
            return render(request, 'add_table.html', {'restaurants': restaurants})

        if table_number < 1 or seats < 1:
            messages.error(request, "Table number and seats must be at least 1.")
            return render(request, 'add_table.html', {'restaurants': restaurants})

        if Table.objects.filter(restaurant=restaurant, table_number=table_number).exists():
            messages.error(
                request,
                f"Table {table_number} already exists for {restaurant.name}. "
                f"Please use a different table number."
            )
            return render(request, 'add_table.html', {'restaurants': restaurants})

        Table.objects.create(restaurant=restaurant, table_number=table_number, seats=seats)
        return redirect(f'/admin-panel/manage-tables/?restaurant={restaurant_id}')

    return render(request, 'add_table.html', {'restaurants': restaurants})


@staff_member_required
def edit_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    restaurants = Restaurant.objects.all()

    if request.method == 'POST':
        restaurant_id = request.POST.get('restaurant')
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        try:
            table_number = int(request.POST.get('table_number'))
            seats = int(request.POST.get('seats'))
        except (TypeError, ValueError):
            messages.error(request, "Table number and seats must be numbers.")
            return render(request, 'edit_table.html', {'table': table, 'restaurants': restaurants})

        if table_number < 1 or seats < 1:
            messages.error(request, "Table number and seats must be at least 1.")
            return render(request, 'edit_table.html', {'table': table, 'restaurants': restaurants})

        duplicate = (
            Table.objects
            .filter(restaurant=restaurant, table_number=table_number)
            .exclude(id=table.id)
            .exists()
        )
        if duplicate:
            messages.error(
                request,
                f"Table {table_number} already exists for {restaurant.name}. "
                f"Please use a different table number."
            )
            return render(request, 'edit_table.html', {'table': table, 'restaurants': restaurants})

        table.table_number = table_number
        table.seats = seats
        table.restaurant = restaurant
        table.save()
        return redirect(f'/admin-panel/manage-tables/?restaurant={restaurant_id}')

    return render(request, 'edit_table.html', {'table': table, 'restaurants': restaurants})


@staff_member_required
def delete_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    restaurant_id = table.restaurant_id

    if request.method == 'POST':
        table.delete()

    return redirect(f'/admin-panel/manage-tables/?restaurant={restaurant_id}')