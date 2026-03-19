from django.contrib import admin
from .models import *

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'mobile_number', 'email', 'lead_source', 'get_packages', 'created_at']
    list_filter = ['lead_source', 'created_at']
    search_fields = ['name', 'mobile_number', 'email']
    readonly_fields = ['created_at', 'updated_at']

    def get_packages(self, obj):
        return ", ".join([p.package_name for p in obj.packages.all()])
    get_packages.short_description = 'Packages'


@admin.register(ProjectDetail)
class ProjectDetailAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'mobile_number', 'start_date', 'end_date', 'created_at']
    list_filter = ['start_date', 'end_date']
    search_fields = ['project_name', 'mobile_number']

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'team']
    filter_horizontal = ['subservices']


class PackageServiceInline(admin.TabularInline):
    model = PackageService
    extra = 1

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("service_name", "team", "cost")
    search_fields = ("service_name", "team")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("package_name",)
    search_fields = ("package_name",)
    inlines = [PackageServiceInline]


class PackageServiceAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'package', 'qty', 'cost')

admin.site.register(PackageService, PackageServiceAdmin)


@admin.register(SubService)
class SubServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price') 
    search_fields = ('name',)        
    list_filter = ('price',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'project', 'assigned_to', 'phase', 'status', 'due_date')
    list_filter = ('status', 'phase', 'project', 'assigned_to')
    search_fields = ('task_name', 'category')


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(TaskList)
class TaskListAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'get_category_name', 'phase')
    list_filter = ('phase', 'category')
    search_fields = ('task_name', 'category__name')
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else "—"
    get_category_name.short_description = 'Category'


@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)


@admin.register(QuotationShowcase)
class QuotationShowcaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'order', 'has_image', 'has_video')
    list_filter = ('section',)
    list_editable = ('order',)
    
    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    
    def has_video(self, obj):
        return bool(obj.video)
    has_video.boolean = True


@admin.register(QuotationSettings)
class QuotationSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'has_logo', 'has_banner')
    
    def has_logo(self, obj):
        return bool(obj.logo)
    has_logo.boolean = True
    has_logo.short_description = 'Logo Uploaded'

    def has_banner(self, obj):
        return bool(obj.banner_image)
    has_banner.boolean = True
    has_banner.short_description = 'Banner Uploaded'