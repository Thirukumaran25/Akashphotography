from django.contrib import admin
from .models import *

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'mobile_number', 'email', 'lead_source', 'package', 'created_at']
    list_filter = ['lead_source', 'created_at']
    search_fields = ['name', 'mobile_number', 'email']
    readonly_fields = ['created_at', 'updated_at']

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
    list_display = ['name', 'team', 'date_joined']
    list_filter = ['team', 'date_joined']
    search_fields = ['name']


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
    list_display = ('service_name', 'package', 'display_teams', 'qty', 'cost')

    def display_teams(self, obj):
        return ", ".join([t.name for t in obj.teams.all()])
    display_teams.short_description = "Teams"

admin.site.register(PackageService, PackageServiceAdmin)


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = ('title', 'price') 
    search_fields = ('title',)        
    list_filter = ('price',)