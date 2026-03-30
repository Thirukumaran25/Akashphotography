from django.urls import path
from .views import *

urlpatterns = [

    path('', custom_login_view, name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', home, name='home'),
    path('quotation/', quotation_builder_view, name='quotation_builder'),
    path('quotation/view/<uuid:token>/', public_quotation_view, name='public_quotation_view'),

    path('admin-notifications/mark-read/', admin_mark_read, name='admin_mark_read'),
    path('admin-notifications/mark-all-read/', admin_mark_all_read, name='admin_mark_all_read'),
    path('lead/', lead, name='lead'),
    path('projects/', projects, name='projects'),
    path('projects/details/<int:project_id>/', get_project_details, name='get_project_details'),
    path('projects/assign-team/', assign_team_to_project, name='assign_team_to_project'),
    path('projects/update-status/',update_project_status, name='update_project_status'),
    path('generate-pdf/', generate_pdf_endpoint, name='generate_pdf'),
    path('projects/<int:project_id>/tasks/', get_admin_project_tasks, name='get_admin_project_tasks'),
    path('projects/tasks/add/', add_project_task, name='add_project_task'),

    path('projects/tasks/update/', update_project_task, name='update_project_task'),
    path('projects/tasks/delete/', delete_project_task, name='delete_project_task'),
    path('projects/assign-team-basic/', assign_team_from_projects, name='assign_team_from_projects'),

    path('invoice/list/', invoice, name='invoice_list'),
    path('invoice/edit/<int:lead_id>/', create_invoice, name='create_invoice'),
    path('save-invoice/', save_invoice, name='save_invoice'),
    path('invoice/log-payment/',log_payment, name='log_payment'),
    path('invoice/data/<int:invoice_id>/', get_invoice_data, name='get_invoice_data'),
    path('invoice/search-leads/', search_leads_for_invoice, name='search_leads_for_invoice'),
    path('invoice/generate-from-lead/', generate_invoice_from_lead, name='generate_invoice_from_lead'),
    path('get-image-base64/', get_image_base64, name='get_image_base64'),

    path('leads/', create_lead, name='create_lead'),
    path('edit-lead/<int:lead_id>/', edit_lead, name='edit_lead'),
    path('leads/update-status/', update_lead_status, name='update_lead_status'),
    path('add-deliverable-quick/', add_deliverable_quick, name='add_deliverable_quick'),
    path('add-sub-service/', add_sub_service, name='add_sub_service'),
    path('get-sub-services/', get_sub_services, name='get_sub_services'),
    path('add-additional-service/', add_additional_service, name='add_additional_service'),
    
    path("save-package/",save_package,name="save_package"),
    path("get-package/<int:pk>/",get_package,name="get_package"),
    path('get-package/', get_package, name='get_package_multi'),
    path('get-task-templates/',  get_task_templates,  name='get_task_templates'),
    path('save-task-template/',  save_task_template,  name='save_task_template'),
    path('save-task-category/',  save_task_category,  name='save_task_category'),
    path("delete-package/<int:pk>/", delete_package, name="delete_package"),

    path('employees/', employees_list, name='employees_list'),

    path('sessions/', session_list_view,   name='session_list'),
    path('sessions/project/<int:project_id>/',get_project_details_api, name='get_project_details_api'),
    path('sessions/assign-crew/', save_team_assignment_api, name='save_team_assignment_api'),

    path('employee-dashboard/', employee_dashboard, name='employee_dashboard'),
    path('employee-projects/', employee_projects, name='employee_projects'),
    path('employee-projects/<int:project_id>/tasks/', employee_project_tasks, name='employee_project_tasks'),
    path('api/task/<int:task_id>/complete/', mark_task_complete, name='mark_task_complete'),
    path('employee-dashboard/accept/', employee_accept_project, name='employee_accept_project'),
    path('api/shoot/<int:assignment_id>/complete/', mark_shoot_complete, name='mark_shoot_complete'),
    path('api/expense/submit/', submit_expense, name='submit_expense'),

    path('notifications/', get_employee_notifications,  name='get_notifications'),
    path('notifications/<int:notif_id>/read/', mark_notification_read,  name='mark_notification_read'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='mark_all_notifications_read'),


    path('galleries/', gallery_dashboard, name='gallery_dashboard'),
    path('gallery/create/', create_gallery, name='create_gallery'),
    path('gallery/<int:gallery_id>/', gallery_overview, name='gallery_overview'),
    path('gallery/<int:gallery_id>/favorites/', gallery_favorites, name='gallery_favorites'),
    path('galleries/edit/<int:gallery_id>/', edit_gallery, name='edit_gallery'),
    path('gallery/edit/<int:gallery_id>/add-folder/', add_folder_to_gallery, name='edit_add_folder'),
    path('gallery/edit/delete-photo/', delete_photo, name='edit_delete_photo'),
    path('gallery/edit/upload-photos/<int:folder_id>/', upload_images_to_folder, name='edit_upload_photos'),
    path('gallery/folder/<int:folder_id>/', client_folder_view, name='client_folder'),
    path('gallery/toggle-favorite/', toggle_favorite, name='toggle_favorite'),
    path('gallery/<int:gallery_id>/generate-link/', generate_share_link, name='generate_share_link'),
    path('shared/<uuid:token>/', client_shared_gallery, name='client_shared_gallery'),
    path('shared/<uuid:token>/folder/<int:folder_id>/', shared_folder_view, name='shared_folder'),
    path('shared/<uuid:token>/favorites/', shared_favorites_view, name='shared_favorites'),
    path('shared/<uuid:token>/submit/', submit_gallery_selection, name='submit_gallery_selection'),
]