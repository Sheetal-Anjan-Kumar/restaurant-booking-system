from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.home, name='home'),
    path('book/<int:table_id>/', views.book_table, name='book_table'),
    path('book/<int:table_id>/slots/', views.get_time_slots, name='get_time_slots'),
    path('success/', views.booking_success, name='booking_success'),
    path('get-available-tables/', views.get_available_tables, name='get_available_tables'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('reschedule/<int:booking_id>/', views.reschedule_booking, name='reschedule_booking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/bookings-report/', views.admin_booking_report, name='admin_booking_report'),
    path('admin-panel/export-excel/', views.export_excel, name='export_excel'),
    path('admin-panel/export-pdf/', views.export_pdf, name='export_pdf'),
    path('admin-panel/manage-tables/', views.manage_tables, name='manage_tables'),
    path('admin-panel/add-table/', views.add_table, name='add_table'),
    path('admin-panel/edit-table/<int:table_id>/', views.edit_table, name='edit_table'),
    path('admin-panel/delete-table/<int:table_id>/', views.delete_table, name='delete_table'),
]