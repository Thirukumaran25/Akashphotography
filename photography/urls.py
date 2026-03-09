from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('projects/', projects, name='projects'),
    path('projects/details/<int:project_id>/', get_project_details, name='get_project_details'),
    path('projects/assign-team/', assign_team_to_project, name='assign_team_to_project'),
    path('projects/update-status/',update_project_status, name='update_project_status'),
    path('generate-pdf/', generate_pdf, name='generate_pdf'),

    path('invoice/list/', invoice, name='invoice_list'),
    path('invoice/edit/<int:lead_id>/', create_invoice, name='create_invoice'),
    path('save-invoice/', save_invoice, name='save_invoice'),
    path('invoice/log-payment/',log_payment, name='log_payment'),
    path('invoice/data/<int:invoice_id>/', get_invoice_data, name='get_invoice_data'),
    path('invoice/search-leads/', search_leads_for_invoice, name='search_leads_for_invoice'),
    path('invoice/generate-from-lead/', generate_invoice_from_lead, name='generate_invoice_from_lead'),
    path('get-image-base64/', get_image_base64, name='get_image_base64'),

    path('sessions/', sessions, name='sessions'),
    path('team_members/', team_members, name='team_members'),

    path('leads/', create_lead, name='create_lead'),
    path('leads/update-status/', update_lead_status, name='update_lead_status'),
    
    path("save-package/",save_package,name="save_package"),
    path("get-package/<int:pk>/",get_package,name="get_package"),
    path("delete-package/<int:pk>/", delete_package, name="delete_package"),
]