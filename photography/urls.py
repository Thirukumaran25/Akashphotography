from django.urls import path
from .views import *

urlpatterns = [

    path('', custom_login_view, name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', home, name='home'),

    path('projects/', projects, name='projects'),
    path('projects/details/<int:project_id>/', get_project_details, name='get_project_details'),
    path('projects/assign-team/', assign_team_to_project, name='assign_team_to_project'),
    path('projects/update-status/',update_project_status, name='update_project_status'),
    path('generate-pdf/', generate_pdf, name='generate_pdf'),
    path('projects/<int:project_id>/tasks/', get_admin_project_tasks, name='get_admin_project_tasks'),
    path('projects/tasks/add/', add_project_task, name='add_project_task'),

    path('projects/tasks/update/', update_project_task, name='update_project_task'),
    path('projects/tasks/delete/', delete_project_task, name='delete_project_task'),

    path('invoice/list/', invoice, name='invoice_list'),
    path('invoice/edit/<int:lead_id>/', create_invoice, name='create_invoice'),
    path('save-invoice/', save_invoice, name='save_invoice'),
    path('invoice/log-payment/',log_payment, name='log_payment'),
    path('invoice/data/<int:invoice_id>/', get_invoice_data, name='get_invoice_data'),
    path('invoice/search-leads/', search_leads_for_invoice, name='search_leads_for_invoice'),
    path('invoice/generate-from-lead/', generate_invoice_from_lead, name='generate_invoice_from_lead'),
    path('get-image-base64/', get_image_base64, name='get_image_base64'),

    path('leads/', create_lead, name='create_lead'),
    path('leads/update-status/', update_lead_status, name='update_lead_status'),
    
    path('get-persons/', get_persons, name='get_persons'),
    path('add-person/', add_person, name='add_person'),
    path('add-deliverable-quick/', add_deliverable_quick, name='add_deliverable_quick'),

    path("save-package/",save_package,name="save_package"),
    path("get-package/<int:pk>/",get_package,name="get_package"),
    path('get-task-templates/',  get_task_templates,  name='get_task_templates'),
    path('save-task-template/',  save_task_template,  name='save_task_template'),
    path('save-task-category/',  save_task_category,  name='save_task_category'),
    path("delete-package/<int:pk>/", delete_package, name="delete_package"),

    path('employees/', employees_list, name='employees_list'),

    path('sessions/', session_list_view, name='session_list'),
    path('sessions/api/details/<int:project_id>/', get_project_details_api, name='get_project_details_api'),
    path('sessions/api/save/', save_team_assignment_api, name='save_team_assignment_api'),



    path('employee-dashboard/', employee_dashboard, name='employee_dashboard'),
    path('employee-projects/', employee_projects, name='employee_projects'),
    path('employee-projects/<int:project_id>/tasks/', employee_project_tasks, name='employee_project_tasks'),
    path('api/task/<int:task_id>/complete/', mark_task_complete, name='mark_task_complete'),
    path('employee-dashboard/accept/', employee_accept_project, name='employee_accept_project'),
]