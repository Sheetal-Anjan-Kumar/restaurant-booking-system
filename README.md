\# Restaurant Table Booking System



A web app built with Django where customers can book tables at restaurants, and staff can manage tables and view booking reports.



\## Features



\### For customers

\- Register, log in, and log out

\- Browse restaurants and their tables

\- Book a table by choosing a date, a time slot, and the number of guests

\- Time slots every 30 minutes within the restaurant's opening hours

\- Each booking holds the table for 90 minutes, so overlapping bookings are blocked

\- Guest count is checked against the table's seats

\- Bookings in the past are not allowed

\- View all your bookings with a status: Confirmed, Cancelled, or Completed

\- Reschedule or cancel upcoming bookings (cancelled bookings are kept in your history)



\### For staff

\- Admin panel with a booking report

\- Filter the report by restaurant, date range (daily, weekly, upcoming), and status

\- Export the filtered report to Excel (.xlsx) or PDF

\- Add, edit, and delete tables for each restaurant

\- Duplicate table numbers within a restaurant are blocked

\- Staff-only access to all admin pages

\- Django admin for restaurants (including opening and closing times) and bookings, with bulk actions to mark bookings Completed or Cancelled



\## Tech stack

\- Python and Django

\- SQLite

\- Bootstrap 5

\- pandas and openpyxl (Excel export)

\- xhtml2pdf (PDF export)



\## Getting started



1\. Clone the repository

```

&#x20;  git clone https://github.com/Sheetal-Anjan-Kumar/restaurant-booking-system.git

&#x20;  cd restaurant-booking-system

```



2\. Create and activate a virtual environment (Windows)

```

&#x20;  python -m venv venv

&#x20;  venv\\Scripts\\activate

```



3\. Install the dependencies

```

&#x20;  pip install -r requirements.txt

```



4\. Set up the database

```

&#x20;  python manage.py migrate

```



5\. Create an admin account

```

&#x20;  python manage.py createsuperuser

```



6\. Start the server

```

&#x20;  python manage.py runserver

```



7\. Open `http://127.0.0.1:8000/` in your browser.



\## Adding restaurants and tables



The database starts empty. To add data:



1\. Go to `http://127.0.0.1:8000/admin/` and log in with your admin account.

2\. Under \*\*Restaurants\*\*, add a restaurant with its name, location, and opening and closing times (the default is 11:00 AM to 11:00 PM).

3\. Add tables from the staff panel at `http://127.0.0.1:8000/admin-panel/manage-tables/`, or from the Django admin.



Customers can then register and start booking.



\## Configuration



Booking settings are at the top of `booking/views.py`:



\- `SLOT\_MINUTES`: gap between time slots (default 30)

\- `BOOKING\_MINUTES`: how long each booking holds a table (default 90)



For deployment, set these environment variables:



\- `DJANGO\_SECRET\_KEY`: your own secret key

\- `DJANGO\_DEBUG`: set to `False` in production



\## Project structure



```

booking/              Main app: models, views, forms, templates

restaurant\_booking/   Project settings and URLs

manage.py

requirements.txt

```



\## Possible future improvements

\- Email confirmations

\- Online payments

\- Automated tests

\- A dashboard with charts

