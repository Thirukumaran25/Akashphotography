from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import *


class PackageServiceInline(admin.TabularInline):
    model  = PackageService
    extra  = 1
    filter_horizontal = ['sub_services']
    fields = ['service_name', 'sub_services', 'qty', 'cost']
 
 
class LeadAdditionalServiceInline(admin.TabularInline):
    model  = LeadAdditionalService
    extra  = 0
    fields = ['name', 'price', 'qty']
 
 
class InvoiceServiceInline(admin.TabularInline):
    model             = InvoiceService
    extra             = 0
    filter_horizontal = ['deliverables', 'sub_services']
    fields            = ['service_name', 'qty', 'price', 'sub_services', 'deliverables']
 
 
class PaymentRecordInline(admin.TabularInline):
    model      = PaymentRecord
    extra      = 0
    fields     = ['amount', 'payment_method', 'date', 'reference']
    readonly_fields = ['date']



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



class QuotationSettingsMediaInline(admin.TabularInline):
    model       = QuotationSettingsMedia
    extra       = 1
    fields      = ['section', 'order', 'caption', 'image', 'video', 'media_preview_inline']
    readonly_fields = ['media_preview_inline']
    ordering    = ['section', 'order']
 
    def media_preview_inline(self, obj):
        if not obj.pk:
            return '—'
        if obj.video:
            return format_html(
                '<video src="{}" style="height:56px;width:80px;object-fit:cover;border-radius:4px;" muted preload="metadata"></video>'
                '<br><span style="font-size:10px;color:#2563eb;font-weight:700;">🎬 VIDEO</span>',
                obj.video.url
            )
        elif obj.image:
            return format_html(
                '<img src="{}" style="height:56px;width:80px;object-fit:cover;border-radius:4px;">',
                obj.image.url
            )
        return mark_safe('<span style="color:#d1d5db;font-size:11px;">No media yet</span>')
    media_preview_inline.short_description = 'Preview'
 
 
@admin.register(QuotationSettings)
class QuotationSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'logo_preview', 'media_count']
    inlines      = [QuotationSettingsMediaInline]
    fieldsets = (
        ('Studio Identity', {
            'description': 'Your studio logo appears in the topbar, hero brand circle, and footer.',
            'fields': ('name', 'logo'),
        }),
        ('Terms & Conditions', {
            'description': (
                'Enter each term on a new line. '
                'Each non-empty line becomes a numbered point on the quotation page.'
            ),
            'fields': ('terms_and_conditions',),
        }),
    )
 
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:40px;object-fit:contain;'
                'background:#f3f4f6;padding:4px;border-radius:4px;">',
                obj.logo.url
            )
        return mark_safe('<span style="color:#d1d5db;">No logo</span>')
    logo_preview.short_description = 'Logo'
 
    def media_count(self, obj):
        total  = obj.media_items.count()
        videos = obj.media_items.exclude(video='').exclude(video=None).count()
        images = total - videos
        if not total:
            return mark_safe('<span style="color:#d1d5db;">No media</span>')
        return format_html(
            '<span style="color:#059669;font-weight:700;">🖼 {}</span> &nbsp;'
            '<span style="color:#2563eb;font-weight:700;">🎬 {}</span>',
            images, videos,
        )
    media_count.short_description = 'Media'
 
 
@admin.register(QuotationSettingsMedia)
class QuotationSettingsMediaAdmin(admin.ModelAdmin):
    """
    Standalone admin so you can also manage media items directly.
    """
    list_display   = ['settings', 'section_badge', 'order', 'caption', 'media_preview', 'media_type']
    list_filter    = ['settings', 'section']
    list_editable  = ['order', 'caption']
    ordering       = ['settings', 'section', 'order']
    search_fields  = ['caption', 'settings__name']
    fieldsets = (
        ('Placement', {
            'description': (
                '<strong>HERO</strong>: hero background — upload a video for cinematic effect.<br>'
                '<strong>STORY</strong>: 2 images — "Our Story" left image &amp; "Hey Sweethearts" editorial.<br>'
                '<strong>SIGNATURE</strong>: 5 portrait images — staggered gallery (centre item is largest).<br>'
                '<strong>FOOTER</strong>: 4 square images — small thumbnails in footer strip.<br>'
                '<strong>FILMS</strong>: up to 3 videos — shown in the "Our Films" video grid.'
            ),
            'fields': ('settings', 'section', 'order', 'caption'),
        }),
        ('Media', {
            'description': (
                'Upload either an <strong>image</strong> OR a <strong>video</strong>. '
                'If both are provided, the <strong>video takes priority</strong>.'
            ),
            'fields': ('image', 'video'),
        }),
    )
 
    def section_badge(self, obj):
        colors = {
            'HERO':      '#2563eb',
            'STORY':     '#7c3aed',
            'SIGNATURE': '#A9323D',
            'FOOTER':    '#059669',
            'FILMS':     '#d97706',
        }
        color = colors.get(obj.section, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;">{}</span>',
            color, obj.section
        )
    section_badge.short_description = 'Section'
 
    def media_preview(self, obj):
        if obj.video:
            return format_html(
                '<video src="{}" style="height:48px;width:64px;object-fit:cover;border-radius:4px;" muted preload="metadata"></video>',
                obj.video.url
            )
        elif obj.image:
            return format_html(
                '<img src="{}" style="height:48px;width:64px;object-fit:cover;border-radius:4px;">',
                obj.image.url
            )
        return mark_safe('<span style="color:#d1d5db;font-size:11px;">No media</span>')
    media_preview.short_description = 'Preview'
 
    def media_type(self, obj):
        if obj.video:
            return mark_safe('<span style="color:#2563eb;font-size:11px;font-weight:700;">🎬 VIDEO</span>')
        elif obj.image:
            return mark_safe('<span style="color:#059669;font-size:11px;font-weight:700;">🖼 IMAGE</span>')
        return mark_safe('<span style="color:#d1d5db;font-size:11px;">—</span>')
    media_type.short_description = 'Type'
 


@admin.register(CrewAssignment)
class CrewAssignmentAdmin(admin.ModelAdmin):
    list_display  = ['project', 'employee_name', 'subservice', 'date', 'start_time', 'end_time']
    list_filter   = ['project', 'subservice', 'date']
    search_fields = ['project__project_name', 'employee__name__first_name']
 
    def employee_name(self, obj):
        return obj.employee.name.get_full_name() or obj.employee.name.username if obj.employee.name else '—'
    employee_name.short_description = 'Employee'
 
 
@admin.register(EmployeeNotification)
class EmployeeNotificationAdmin(admin.ModelAdmin):
    list_display  = ['employee_name', 'title', 'project', 'subservice', 'date', 'is_read_badge', 'created_at']
    list_filter   = ['is_read', 'created_at', 'project']
    search_fields = ['title', 'message', 'employee__name__first_name']
    readonly_fields = ['created_at']
    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description='Mark selected as Read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected as Unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
 
    def employee_name(self, obj):
        return obj.employee.name.get_full_name() or obj.employee.name.username if obj.employee.name else '—'
    employee_name.short_description = 'Employee'
 
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:#16a34a;font-weight:700;">✓ Read</span>')
        return format_html('<span style="color:#A9323D;font-weight:700;">● Unread</span>')
    is_read_badge.short_description = 'Status'



admin.site.register(Deliverable)