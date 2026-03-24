from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, F
from django.utils import timezone
from django.db.models import Q
from datetime import date, timedelta
from .models import *
import json
from weasyprint import HTML
from django.conf import settings as django_settings
import base64
import os
from django.contrib.staticfiles import finders
from datetime import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.template.loader import render_to_string
import json
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from django.contrib.auth.decorators import login_required


def custom_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('home')
        else:
            return redirect('employee_dashboard')

    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        login_role = request.POST.get('login_role')
        user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            if login_role == 'admin':
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, "Access Denied: You do not have Admin privileges.")
                    return redirect('login')
            elif login_role == 'team':
                login(request, user)
                return redirect('employee_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'login.html')


def custom_logout_view(request):
    logout(request)
    return redirect('login')


def get_static_image_base64(relative_path):
    full_path = os.path.join(django_settings.STATIC_ROOT, relative_path)
    try:
        with open(full_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        ext = relative_path.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'svg': 'svg+xml'}.get(ext, 'png')
        return f"data:image/{mime};base64,{encoded}"
    except FileNotFoundError:
        return ""


def generate_pdf_endpoint(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        raw_html = data.get('html')

        if raw_html:
            html_string = raw_html
        else:
            qs = QuotationSettings.objects.prefetch_related('media_items').first()
            all_media = list(qs.media_items.all()) if qs else []

            def get_section(key):
                return [m for m in all_media if m.section == key]

            hero_items = [m for m in get_section('HERO') if m.image and m.image.name]
            banner_media = hero_items[0] if hero_items else None

            context = {
                'show_bill_to':        data.get('show_bill_to', True),
                'display_name':        data.get('display_name', 'Valued Client'),
                'initials':            data.get('initials', '--'),
                'email':               data.get('email', ''),
                'grand_total':         data.get('grand_total', '0'),
                'packages':            data.get('packages', []),
                'single_packages':     data.get('single_packages', []),
                'deliverables':        data.get('deliverables', []),
                'additional_services': data.get('additional_services', []),
                'settings':            qs,
                'banner_media':        banner_media,
                'story_media':         get_section('STORY'),
                'signature_media':     get_section('SIGNATURE'),
                'footer_media':        get_section('FOOTER'),
            }
            html_string = render_to_string('quotation_pdf_template.html', context)

        pdf_file = HTML(
            string=html_string,
            base_url=request.build_absolute_uri('/')
        ).write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="quotation.pdf"'
        return response


def get_image_base64(request):
    image_path = request.GET.get('path', '')
    if '..' in image_path or image_path.startswith('/'):
        return JsonResponse({"error": "Invalid path"}, status=400)

    full_path = None
    found = finders.find(image_path)
    if found:
        full_path = found
    if not full_path:
        candidate = os.path.join(django_settings.STATIC_ROOT, image_path)
        if os.path.exists(candidate):
            full_path = candidate
    if not full_path:
        for static_dir in getattr(django_settings, 'STATICFILES_DIRS', []):
            candidate = os.path.join(static_dir, image_path)
            if os.path.exists(candidate):
                full_path = candidate
                break

    if not full_path:
        return JsonResponse({"error": "Image not found"}, status=404)

    try:
        with open(full_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        ext = image_path.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'svg': 'svg+xml'}.get(ext, 'png')
        return JsonResponse({"data_uri": f"data:image/{mime};base64,{encoded}"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def quotation_builder_view(request):
    all_packages = Package.objects.prefetch_related('services__sub_services').all()
    all_deliverables = Deliverable.objects.all()
    all_additional_services = AdditionalService.objects.all()
    showcase_media = QuotationShowcase.objects.all()
    context = {
        'packages': all_packages,
        'deliverables': all_deliverables,
        'additional_services': all_additional_services,
        'base_total': 0,
        'hero_media': showcase_media.filter(section='HERO'),
        'story_media': showcase_media.filter(section='STORY'),
        'signature_media': showcase_media.filter(section='SIGNATURE'),
        'footer_media': showcase_media.filter(section='FOOTER'),
    }
    return render(request, 'quotation_builder.html', context)


def public_quotation_view(request, token):
    lead = get_object_or_404(Lead, secure_token=token)
    qs = QuotationSettings.objects.prefetch_related('media_items').first()
    all_media = list(qs.media_items.all()) if qs else []

    def get_section(key):
        return [m for m in all_media if m.section == key]

    context = {
        'lead':                lead,
        'packages':            lead.packages.prefetch_related('services__sub_services').all(),
        'deliverables':        lead.deliverables.all(),
        'additional_services': lead.additional_services.all(),
        'total_cost':          lead.total_cost,
        'settings':            qs,
        'hero_media':       get_section('HERO'),
        'story_media':      get_section('STORY'),
        'signature_media':  get_section('SIGNATURE'),
        'footer_media':     get_section('FOOTER'),
        'films_media':      get_section('FILMS'),
    }
    return render(request, 'public_quotation_view.html', context)


@login_required(login_url='login')
def home(request):
    today = date.today()
    Lead.objects.filter(status='NEW', follow_up_date__lte=today).update(status='FOLLOW_UP')
    all_leads = Lead.objects.all()

    def calculate_leads_total(leads_queryset):
        total = 0
        for lead in leads_queryset:
            total += lead.total_cost
        return total

    new_leads = all_leads.filter(status='NEW')
    follow_up = all_leads.filter(status='FOLLOW_UP')
    accepted  = all_leads.filter(status='ACCEPTED')
    lost      = all_leads.filter(status='LOST')

    context = {
        'new_leads': new_leads,
        'follow_up': follow_up,
        'accepted':  accepted,
        'lost':      lost,
        'total_leads':          all_leads.count(),
        'total_amount':         f"{calculate_leads_total(all_leads):,.0f}",
        'accepted_amount':      f"{calculate_leads_total(accepted):,.0f}",
        'lost_quoted_amount':   f"{calculate_leads_total(lost):,.0f}",
    }
    return render(request, 'leads.html', context)


@csrf_exempt
def update_lead_status(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    lead_id    = request.POST.get("lead_id")
    new_status = request.POST.get("status")
    if not (lead_id and new_status):
        return JsonResponse({"success": False}, status=400)

    lead = get_object_or_404(Lead, id=lead_id)
    lead.status = new_status
    lead.save()

    if new_status == 'ACCEPTED' and lead.project:
        lead.project.status = 'ASSIGNED'
        lead.project.save()

        if lead.packages.exists() or lead.deliverables.exists() or lead.additional_services.exists():
            invoice = Invoice.objects.filter(lead=lead).first()
            if not invoice:
                base_count  = Invoice.objects.count() + 100
                invoice_num = f"AK-{base_count}"
                while Invoice.objects.filter(invoice_number=invoice_num).exists():
                    base_count  += 1
                    invoice_num  = f"AK-{base_count}"

                invoice = Invoice.objects.create(lead=lead, invoice_number=invoice_num, due_date=None)

                for pkg in lead.packages.all():
                    for pkg_svc in pkg.services.all():
                        inv_svc = InvoiceService.objects.create(
                            invoice=invoice,
                            service_name=pkg_svc.service_name,
                            qty=pkg_svc.qty,
                            price=pkg_svc.cost,
                        )
                        if pkg_svc.sub_services.exists():
                            inv_svc.sub_services.set(pkg_svc.sub_services.all())

                if lead.deliverables.exists():
                    total_d = sum(d.price for d in lead.deliverables.all())
                    row = InvoiceService.objects.create(
                        invoice=invoice, service_name="Deliverables", qty=1, price=total_d
                    )
                    row.deliverables.set(lead.deliverables.all())

                for a in lead.additional_services.all():
                    InvoiceService.objects.create(
                        invoice=invoice,
                        service_name=f"{a.name} (Additional)",
                        qty=a.qty,
                        price=a.price,
                    )

            return JsonResponse({"success": True, "invoice_url": f"/invoice/edit/{lead.id}/"})

    return JsonResponse({"success": True})


def projects(request):
    def format_projects(queryset):
        formatted_list = []
        for proj in queryset:
            lead        = proj.lead_set.first()
            client_name = lead.name if lead else "Unknown Client"
            start_str   = proj.start_date.strftime('%d %b, %Y') if proj.start_date else 'TBD'
            end_str     = proj.end_date.strftime('%d %b, %Y')   if proj.end_date   else 'TBD'

            # Show only PROJECT-board crew on the project card (not session shoot crew)
            project_emp_ids = list(
                CrewAssignment.objects.filter(project=proj, source='PROJECT')
                .values_list('employee_id', flat=True).distinct()
            )
            team = []
            for m in Employee.objects.filter(id__in=project_emp_ids).select_related('name'):
                display_name = (m.name.get_full_name() or m.name.username) if m.name else "Unknown"
                initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()
                team.append({"initials": initials})

            formatted_list.append({
                "id":          proj.id,
                "client_name": client_name,
                "event_type":  proj.project_name,
                "start_date":  start_str,
                "end_date":    end_str,
                "team":        team,
            })
        return formatted_list

    context = {
        'assigned':  format_projects(ProjectDetail.objects.filter(status='ASSIGNED', lead__status='ACCEPTED')),
        'pre_cards': format_projects(ProjectDetail.objects.filter(status='PRE')),
        'selection': format_projects(ProjectDetail.objects.filter(status='SELECTION')),
        'post':      format_projects(ProjectDetail.objects.filter(status='POST')),
        'completed': format_projects(ProjectDetail.objects.filter(status='COMPLETED')),
    }
    return render(request, 'projects.html', context)


def get_project_details(request, project_id):
    """
    Projects board Assign Team popup.
    Pre-selects only PROJECT-source crew — session crew is never shown here.
    """
    project = get_object_or_404(ProjectDetail, id=project_id)
    lead    = project.lead_set.first()

    pre_task         = project.tasks.filter(phase='PRE').first()
    pre_deadline_str = pre_task.due_date.strftime('%Y-%m-%d') if pre_task and pre_task.due_date else ""

    def get_team_members(team_keyword):
        members = Employee.objects.filter(team__name__icontains=team_keyword)
        result  = []
        for m in members:
            display  = (m.name.get_full_name() or m.name.username) if m.name else "Unknown"
            initials = "".join([p[0] for p in display.split() if p])[:2].upper()
            result.append({"id": m.id, "name": display, "initials": initials})
        return result

    # Pre-select only PROJECT-board crew (not session crew)
    project_assigned_ids = list(
        CrewAssignment.objects.filter(project=project, source='PROJECT')
        .values_list('employee_id', flat=True).distinct()
    )

    data = {
        "client_name":       lead.name if lead else project.project_name,
        "location":          project.project_address,
        "start_session":     "TBD",
        "event_type":        project.project_name,
        "start_date":        project.start_date.strftime('%d %b, %Y') if project.start_date else "TBD",
        "end_date":          project.end_date.strftime('%d %b, %Y')   if project.end_date   else "TBD",
        "deadline_date":     project.end_date.strftime('%Y-%m-%d')    if project.end_date   else "",
        "pre_deadline_date": pre_deadline_str,
        "general_team":      get_team_members('General'),
        "pre_team":          get_team_members('Pre'),
        "post_team":         get_team_members('Post'),
        "assigned_ids":      project_assigned_ids,   # PROJECT crew only
    }
    return JsonResponse(data)


@csrf_exempt
def assign_team_from_projects(request):
    """
    Projects board save. Only touches SOURCE='PROJECT' crew.
    SESSION assignments are never deleted or modified here.
    """
    from .models import CrewAssignment, EmployeeNotification, SubService

    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)

    project_id    = request.POST.get('project_id')
    raw_ids       = request.POST.get('employee_ids', '[]')
    post_deadline = request.POST.get('deadline_date', '')
    pre_deadline  = request.POST.get('pre_deadline', '')

    try:
        emp_ids = json.loads(raw_ids)
    except Exception:
        emp_ids = [x.strip() for x in raw_ids.split(',') if x.strip()]

    project = get_object_or_404(ProjectDetail, id=project_id)

    # Delete only PROJECT-source assignments; leave SESSION intact
    CrewAssignment.objects.filter(project=project, source='PROJECT').delete()

    if post_deadline:
        try:
            parsed_post = datetime.strptime(post_deadline, '%Y-%m-%d').date()
            project.end_date = parsed_post
            project.tasks.filter(phase__in=['SELECTION', 'POST']).update(due_date=parsed_post)
        except ValueError:
            pass

    if pre_deadline:
        try:
            parsed_pre = datetime.strptime(pre_deadline, '%Y-%m-%d').date()
            project.tasks.filter(phase='PRE').update(due_date=parsed_pre)
        except ValueError:
            pass

    project.save()

    if project.end_date:
        project.tasks.filter(due_date__isnull=True).update(due_date=project.end_date)

    # Rebuild M2M = new PROJECT crew + existing SESSION crew
    session_emp_ids = list(
        CrewAssignment.objects.filter(project=project, source='SESSION')
        .values_list('employee_id', flat=True).distinct()
    )
    all_emp_ids = list(set([str(x) for x in emp_ids] + [str(x) for x in session_emp_ids]))
    project.assigned_employees.set(all_emp_ids)
    project.save()

    try:
        auto_generate_deliverable_tasks(project)
    except Exception:
        pass

    generic_ss, _ = SubService.objects.get_or_create(
        name="General Assignment", defaults={'price': 0}
    )

    notified = set()
    for emp in Employee.objects.filter(id__in=emp_ids):
        ss = emp.subservices.first() or generic_ss
        CrewAssignment.objects.create(
            project=project,
            employee=emp,
            subservice=ss,
            service_name=project.project_name,
            date=project.start_date,
            source='PROJECT',
        )
        EmployeeNotification.objects.create(
            employee=emp,
            project=project,
            subservice=ss,
            title=f"New Assignment: {project.project_name}",
            message=f"You have been assigned to {project.project_name}.",
            date=project.start_date,
        )
        notified.add(emp.id)

    return JsonResponse({'status': 'success', 'notified_count': len(notified)})


@csrf_exempt
def assign_team_to_project(request):
    """Legacy endpoint — same isolation: only PROJECT-source crew touched."""
    from .models import CrewAssignment, EmployeeNotification, SubService

    if request.method == "POST":
        project_id    = request.POST.get("project_id")
        member_ids    = request.POST.get("members", "").split(",")
        deadline_date = request.POST.get("deadline_date", "")

        project = get_object_or_404(ProjectDetail, id=project_id)

        if member_ids and member_ids[0] != "":
            employees = Employee.objects.filter(id__in=member_ids)

            if deadline_date:
                try:
                    project.end_date = datetime.strptime(deadline_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

            generic_ss, _ = SubService.objects.get_or_create(name="General Assignment", defaults={'price': 0})
            for emp in employees:
                ss = emp.subservices.first() or generic_ss
                ca, created = CrewAssignment.objects.get_or_create(
                    project=project, employee=emp, source='PROJECT',
                    defaults={
                        'subservice':   ss,
                        'service_name': project.project_name,
                        'date':         project.start_date,
                        'is_accepted':  False,
                    }
                )
                if created:
                    EmployeeNotification.objects.create(
                        employee=emp, project=project, subservice=ss,
                        title=f"New Assignment: {project.project_name}",
                        message=f"You have been assigned to {project.project_name}.",
                        date=project.start_date
                    )

            # Rebuild M2M from both sources
            project_emp_ids = list(
                CrewAssignment.objects.filter(project=project, source='PROJECT')
                .values_list('employee_id', flat=True).distinct()
            )
            session_emp_ids = list(
                CrewAssignment.objects.filter(project=project, source='SESSION')
                .values_list('employee_id', flat=True).distinct()
            )
            project.assigned_employees.set(list(set(project_emp_ids + session_emp_ids)))

        # Status moves to PRE only on employee acceptance
        project.save()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@csrf_exempt
def update_project_status(request):
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        new_status = request.POST.get("status")
        if project_id and new_status:
            project = get_object_or_404(ProjectDetail, id=project_id)
            project.status = new_status
            project.save()
            return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


def sessions(request):
    return render(request, 'sessions.html')


def team_members(request):
    return render(request, 'team_members.html', {'employees': Employee.objects.all()})


def create_lead(request):
    if request.method == "POST":
        project = ProjectDetail.objects.create(
            project_name=request.POST.get("project_name"),
            mobile_number=request.POST.get("project_mobile"),
            project_address=request.POST.get("project_address"),
            start_date=request.POST.get("start_date"),
            end_date=request.POST.get("end_date")
        )

        package_ids_str    = request.POST.get("package")
        package_ids        = [int(id) for id in package_ids_str.split(',')] if package_ids_str else []
        deliverable_ids_str = request.POST.get("deliverables")
        deliverable_ids    = [int(id) for id in deliverable_ids_str.split(',')] if deliverable_ids_str else []

        lead = Lead.objects.create(
            name=request.POST.get("name"),
            mobile_number=request.POST.get("mobile_number"),
            email=request.POST.get("email") or None,
            address=request.POST.get("address") or None,
            lead_source=request.POST.get("lead_source") or 'Other',
            follow_up_date=request.POST.get("follow_up_date") or None,
            status='NEW',
            project=project
        )

        if package_ids:
            lead.packages.set(Package.objects.filter(id__in=package_ids))
        if deliverable_ids:
            lead.deliverables.set(Deliverable.objects.filter(id__in=deliverable_ids))

        additional_services_str = request.POST.get("additional_services")
        if additional_services_str:
            for item in additional_services_str.split(','):
                parts = item.split('|')
                if len(parts) == 3:
                    LeadAdditionalService.objects.create(
                        lead=lead, name=parts[0],
                        price=float(parts[1]), qty=int(parts[2])
                    )

        return JsonResponse({"success": True, "secure_token": str(lead.secure_token)})

    packages = Package.objects.all()
    packages_with_total = [
        {"id": pkg.id, "package_name": pkg.package_name, "total_cost": f"{pkg.total_cost:,.0f}"}
        for pkg in packages
    ]
    return render(request, "create_lead.html", {
        "packages":                      packages_with_total,
        "teams":                         Team.objects.all(),
        "available_sub_services":        SubService.objects.all(),
        "available_deliverables":        Deliverable.objects.all(),
        "available_additional_services": AdditionalService.objects.all(),
    })


def edit_lead(request, lead_id):
    lead    = get_object_or_404(Lead, id=lead_id)
    project = lead.project

    if request.method == "POST":
        lead.name           = request.POST.get("name")
        lead.mobile_number  = request.POST.get("mobile_number")
        lead.email          = request.POST.get("email") or None
        lead.address        = request.POST.get("address") or None
        lead.lead_source    = request.POST.get("lead_source") or 'Other'
        lead.follow_up_date = request.POST.get("follow_up_date") or None
        lead.save()

        if project:
            project.project_name    = request.POST.get("project_name")
            project.mobile_number   = request.POST.get("project_mobile")
            project.project_address = request.POST.get("project_address")
            project.start_date      = request.POST.get("start_date")
            project.end_date        = request.POST.get("end_date") or None
            project.save()

        package_ids = [int(i) for i in request.POST.get("package", "").split(',') if i.strip()]
        lead.packages.set(Package.objects.filter(id__in=package_ids))

        deliv_ids = [int(i) for i in request.POST.get("deliverables", "").split(',') if i.strip()]
        lead.deliverables.set(Deliverable.objects.filter(id__in=deliv_ids))

        lead.additional_services.all().delete()
        add_svc_str = request.POST.get("additional_services", "")
        if add_svc_str:
            for item in add_svc_str.split(','):
                parts = item.split('|')
                if len(parts) == 3:
                    try:
                        LeadAdditionalService.objects.create(
                            lead=lead, name=parts[0],
                            price=float(parts[1]), qty=int(parts[2]),
                        )
                    except (ValueError, IndexError):
                        pass

        return JsonResponse({"success": True, "secure_token": str(lead.secure_token)})

    packages_with_total = [
        {"id": p.id, "package_name": p.package_name, "total_cost": f"{p.total_cost:,.0f}"}
        for p in Package.objects.all()
    ]
    import json as _json
    selected_add_services = _json.dumps([
        {"id": str(a.id), "name": a.name, "price": float(a.price), "qty": a.qty}
        for a in lead.additional_services.all()
    ])
    return render(request, "edit_lead.html", {
        "lead":                          lead,
        "project":                       project,
        "packages":                      packages_with_total,
        "available_sub_services":        SubService.objects.all(),
        "available_deliverables":        Deliverable.objects.all(),
        "available_additional_services": AdditionalService.objects.all(),
        "selected_package_ids":          ",".join(str(p.id) for p in lead.packages.all()),
        "selected_deliverable_ids":      ",".join(str(d.id) for d in lead.deliverables.all()),
        "selected_add_services":         selected_add_services,
    })


@csrf_exempt
def add_additional_service(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({"error": "Name required"}, status=400)
        svc = AdditionalService.objects.create(name=name, price=data.get("price", 0))
        return JsonResponse({"id": svc.id, "name": svc.name, "price": float(svc.price)})
    return JsonResponse({"error": "Invalid"}, status=400)


@csrf_exempt
def delete_package(request, pk):
    if request.method == "POST":
        try:
            Package.objects.get(id=pk).delete()
            return JsonResponse({"status": "success"})
        except Package.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Package not found"})


def get_task_templates(request):
    templates = TaskList.objects.select_related('category').all()
    return JsonResponse({"templates": [
        {"id": t.id, "phase": t.phase,
         "category": t.category.name if t.category else "General",
         "task_name": t.task_name}
        for t in templates
    ]})


def save_task_template(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)
    data      = json.loads(request.body)
    phase     = data.get("phase", "PRE")
    cat_name  = (data.get("category") or "General").strip()
    task_name = (data.get("task_name") or "").strip()
    if not task_name:
        return JsonResponse({"status": "error", "message": "task_name required"}, status=400)
    category, _ = TaskCategory.objects.get_or_create(name=cat_name)
    task = TaskList.objects.create(phase=phase, category=category, task_name=task_name)
    return JsonResponse({"id": task.id, "phase": task.phase, "category": category.name, "task_name": task.task_name})


def save_task_category(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)
    name = (json.loads(request.body).get("name") or "").strip()
    if not name:
        return JsonResponse({"status": "error", "message": "name required"}, status=400)
    cat, _ = TaskCategory.objects.get_or_create(name=name)
    return JsonResponse({"id": cat.id, "name": cat.name})


@csrf_exempt
def save_package(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)
    data         = json.loads(request.body)
    package_id   = data.get("package_id")
    package_name = data.get("package_name", "").strip()
    if not package_name:
        return JsonResponse({"status": "error", "message": "Package name required"}, status=400)

    if package_id:
        pkg = get_object_or_404(Package, id=package_id)
        pkg.package_name = package_name
        pkg.save()
        pkg.services.all().delete()
    else:
        pkg = Package.objects.create(package_name=package_name)

    for s in data.get("services", []):
        svc = PackageService.objects.create(
            package=pkg, service_name=s["service_name"],
            qty=int(s.get("qty") or 1), cost=float(s.get("cost") or 0),
        )
        for pid in s.get("sub_service_ids", []):
            try:
                svc.sub_services.add(SubService.objects.get(id=pid))
            except SubService.DoesNotExist:
                pass
    return JsonResponse({"status": "success", "package_id": pkg.id})


def get_package(request, pk=None, package_id=None):
    lookup    = pk or package_id
    ids_param = request.GET.get('ids')
    lead_id   = request.GET.get('lead_id')

    packages = Package.objects.none()
    if ids_param:
        packages = Package.objects.filter(id__in=[int(i) for i in ids_param.split(',')])
    elif lookup and lookup != 'None':
        packages = Package.objects.filter(id=lookup)

    services = []
    for pkg in packages:
        for svc in pkg.services.prefetch_related('sub_services').all():
            services.append({
                "service_name": svc.service_name,
                "qty":          svc.qty,
                "cost":         str(svc.cost),
                "sub_services": [{"id": p.id, "name": p.name, "price": str(p.price)} for p in svc.sub_services.all()]
            })

    deliverables = []
    additional_services = []
    if lead_id and lead_id != 'None':
        try:
            lead = Lead.objects.get(id=lead_id)
            deliverables        = [{"title": d.title, "price": str(d.price)} for d in lead.deliverables.all()]
            additional_services = [{"title": a.name, "price": str(a.price), "qty": a.qty} for a in lead.additional_services.all()]
        except Lead.DoesNotExist:
            pass

    pkg_list = list(packages)
    return JsonResponse({
        "id":       pkg_list[0].id if len(pkg_list) == 1 else None,
        "ids":      [p.id for p in pkg_list],
        "name":     " + ".join([p.package_name for p in pkg_list]),
        "services": services,
        "deliverables": deliverables,
        "additional_services": additional_services,
    })


@csrf_exempt
def add_sub_service(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({"error": "Name required"}, status=400)
        sub = SubService.objects.create(name=name, price=data.get("price", 0))
        return JsonResponse({"id": sub.id, "name": sub.name, "price": float(sub.price)})
    return JsonResponse({"error": "Invalid"}, status=400)


def get_sub_services(request):
    subs = list(SubService.objects.values('id', 'name', 'price'))
    for p in subs:
        p['price'] = float(p['price'])
    return JsonResponse({"sub_services": subs})


def invoice(request):
    all_invoices = Invoice.objects.all().select_related('lead', 'lead__project').order_by('-created_at')
    payments_sum = PaymentRecord.objects.aggregate(total=Sum('amount'))['total'] or 0.00
    pre_paid_sum = all_invoices.aggregate(total=Sum('pre_paid_amount'))['total'] or 0.00
    total_paid   = float(payments_sum) + float(pre_paid_sum)
    total_upcoming = 0.0
    total_past_due = 0.0
    today = date.today()
    pending_invoices = []
    partial_invoices = []
    completed_invoices = []

    for inv in all_invoices:
        paid_amount = inv.payments.aggregate(total=Sum('amount'))['total'] or 0.00
        balance     = float(inv.grand_total) - float(inv.pre_paid_amount) - float(paid_amount)
        inv.display_amount = inv.grand_total
        inv.balance        = max(0, balance)
        inv.project_name   = inv.lead.project.project_name if inv.lead.project else inv.lead.name

        if inv.status == Invoice.PaymentStatus.PENDING:
            pending_invoices.append(inv)
        elif inv.status == Invoice.PaymentStatus.PARTIAL:
            partial_invoices.append(inv)
        else:
            completed_invoices.append(inv)

        if inv.status in [Invoice.PaymentStatus.PENDING, Invoice.PaymentStatus.PARTIAL]:
            if inv.due_date and inv.due_date < today:
                total_past_due += inv.balance
            else:
                total_upcoming += inv.balance

    return render(request, 'invoice.html', {
        'total_paid':        total_paid,
        'total_upcoming':    total_upcoming,
        'total_past_due':    total_past_due,
        'pending_invoices':  pending_invoices,
        'partial_invoices':  partial_invoices,
        'completed_invoices': completed_invoices,
    })


def create_invoice(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    inv  = get_object_or_404(Invoice, lead=lead)
    return render(request, "create_invoice.html", {
        'lead': lead, 'invoice': inv, 'services': inv.services.all(),
        'subtotal': inv.subtotal, 'grand_total': inv.grand_total,
        'tax_amount': inv.tax_amount, 'pre_paid': inv.pre_paid_amount,
        'available_deliverables': Deliverable.objects.all(),
        'available_sub_services': SubService.objects.all(),
        'available_additional_services': AdditionalService.objects.all(),
    })


@csrf_exempt
def log_payment(request):
    if request.method == "POST":
        inv           = get_object_or_404(Invoice, id=request.POST.get("invoice_id"))
        existing_paid = inv.payments.aggregate(total=Sum('amount'))['total'] or 0.00
        remaining     = float(inv.grand_total) - float(inv.pre_paid_amount) - float(existing_paid)

        try:
            pay_amount = float(request.POST.get("amount"))
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "error": "Invalid amount"}, status=400)

        if pay_amount <= 0:
            return JsonResponse({"success": False, "error": "Amount must be greater than zero"}, status=400)
        if pay_amount > remaining + 0.01:
            return JsonResponse({"success": False,
                "error": f"Amount ₹{pay_amount:,.2f} exceeds outstanding balance ₹{remaining:,.2f}"}, status=400)

        PaymentRecord.objects.create(
            invoice=inv, amount=pay_amount,
            payment_method=request.POST.get("payment_method"),
            date=request.POST.get("date"),
            reference=request.POST.get("reference", "")
        )
        all_payments  = inv.payments.aggregate(total=Sum('amount'))['total'] or 0.00
        remaining_due = float(inv.grand_total) - float(inv.pre_paid_amount) - float(all_payments)
        inv.status = Invoice.PaymentStatus.COMPLETED if remaining_due <= 0.01 else Invoice.PaymentStatus.PARTIAL
        inv.save()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@csrf_exempt
def save_invoice(request):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            inv = Invoice.objects.get(id=data.get("invoice_id"))
            inv.pre_paid_amount = data.get("pre_paid_amount", 0)
            inv.discount_amount = data.get("discount_amount", 0)
            inv.tax_rate        = data.get("tax_rate", 0)
            inv.notes           = data.get("notes", "")
            if data.get("due_date"):
                inv.due_date = data.get("due_date")
            inv.save()
            inv.services.all().delete()

            for s_data in data.get("services", []):
                new_svc = InvoiceService.objects.create(
                    invoice=inv, service_name=s_data.get("service_name"),
                    qty=int(s_data.get("qty", 1)), price=float(s_data.get("price", 0))
                )
                if s_data.get("deliverable_ids"):
                    new_svc.deliverables.set(Deliverable.objects.filter(id__in=s_data["deliverable_ids"]))
                if s_data.get("sub_service_ids"):
                    new_svc.sub_services.set(SubService.objects.filter(id__in=s_data["sub_service_ids"]))

            if inv.lead and inv.lead.project:
                if inv.lead.project.status in ['PRE', 'SELECTION', 'POST', 'COMPLETED']:
                    auto_generate_deliverable_tasks(inv.lead.project)

            return JsonResponse({"status": "success", "invoice_id": inv.id})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@csrf_exempt
def generate_invoice_from_lead(request):
    if request.method == "POST":
        lead = get_object_or_404(Lead, id=request.POST.get("lead_id"))
        lead.status = 'ACCEPTED'
        lead.save()
        if lead.project:
            lead.project.status = 'ASSIGNED'
            lead.project.save()

        if not hasattr(lead, 'invoice'):
            base_count = Invoice.objects.count() + 100
            invoice_number = f"AK-{base_count}"
            while Invoice.objects.filter(invoice_number=invoice_number).exists():
                base_count += 1
                invoice_number = f"AK-{base_count}"

            new_invoice = Invoice.objects.create(lead=lead, invoice_number=invoice_number, due_date=None)

            for pkg in lead.packages.all():
                for pkg_service in pkg.services.all():
                    inv_svc = InvoiceService.objects.create(
                        invoice=new_invoice, service_name=pkg_service.service_name,
                        qty=pkg_service.qty, price=pkg_service.cost
                    )
                    if pkg_service.sub_services.exists():
                        inv_svc.sub_services.set(pkg_service.sub_services.all())

            if lead.deliverables.exists():
                deliv_row = InvoiceService.objects.create(
                    invoice=new_invoice, service_name="Deliverables",
                    qty=1, price=sum([d.price for d in lead.deliverables.all()])
                )
                deliv_row.deliverables.set(lead.deliverables.all())

            for add_svc in lead.additional_services.all():
                InvoiceService.objects.create(
                    invoice=new_invoice,
                    service_name=f"{add_svc.name} (Additional)",
                    qty=add_svc.qty, price=add_svc.price
                )

        return JsonResponse({"success": True, "invoice_url": f"/invoice/edit/{lead.id}/"})
    return JsonResponse({"success": False}, status=400)


def get_invoice_data(request, invoice_id):
    inv         = get_object_or_404(Invoice, id=invoice_id)
    paid_amount = inv.payments.aggregate(total=Sum('amount'))['total'] or 0.00
    subtotal    = float(inv.subtotal)
    discount    = float(inv.discount_amount)
    tax         = float(inv.tax_amount)
    pre_paid    = float(inv.pre_paid_amount)
    total_amount = (subtotal - discount) + tax
    balance_due  = total_amount - pre_paid - float(paid_amount)

    return JsonResponse({
        "invoice_number": inv.invoice_number,
        "client_name":    inv.lead.name,
        "project_name":   inv.lead.project.project_name if inv.lead.project else "",
        "email":          inv.lead.email or "client@email.com",
        "due_date":       inv.due_date.strftime('%m/%d/%Y') if inv.due_date else "N/A",
        "services": [
            {"service_name": s.service_name, "qty": s.qty, "price": float(s.price),
             "total_amount": float(s.total_amount),
             "deliverables": [d.title for d in s.deliverables.all()]}
            for s in inv.services.all()
        ],
        "subtotal": subtotal, "discount_amount": discount, "tax_amount": tax,
        "total_amount": total_amount, "pre_paid_amount": pre_paid,
        "paid_amount": float(paid_amount), "balance_due": max(0, balance_due),
    })


def search_leads_for_invoice(request):
    query = request.GET.get('q', '').strip()
    leads = Lead.objects.filter(invoice__isnull=True)
    if query:
        leads = leads.filter(
            Q(name__icontains=query) | Q(project__project_name__icontains=query) |
            Q(email__icontains=query) | Q(mobile_number__icontains=query)
        )
    return JsonResponse({"results": [
        {"id": l.id, "name": l.name,
         "project_name": l.project.project_name if l.project else "No Project",
         "email": l.email or "", "mobile": l.mobile_number}
        for l in leads[:5]
    ]})


@csrf_exempt
def add_deliverable_quick(request):
    if request.method == "POST":
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        if not title:
            return JsonResponse({"error": "Title required"}, status=400)
        d = Deliverable.objects.create(title=title, price=data.get("price", 0))
        return JsonResponse({"id": d.id, "title": d.title, "price": float(d.price)})
    return JsonResponse({"error": "Invalid"}, status=400)


def employees_list(request):
    all_employees = Employee.objects.select_related('team').prefetch_related('assigned_projects')
    employee_data = []
    active_count  = 0

    for emp in all_employees:
        active_projects = emp.assigned_projects.exclude(status='COMPLETED').order_by('end_date')
        if active_projects.exists():
            active_count += 1
        display_name = (emp.name.get_full_name() or emp.name.username) if emp.name else "Unknown"
        initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()
        employee_data.append({
            'id': emp.id, 'name': display_name, 'initials': initials,
            'role': emp.team.name if emp.team else "General",
            'deadlines': active_projects[:2], 'upcoming': active_projects[:3],
        })

    return render(request, 'employees.html', {
        'employees': employee_data,
        'total_employees': all_employees.count(),
        'active_employees': active_count,
    })


# ─────────────────────────────────────────────────────────────────────────────
# SESSIONS — fully_assigned uses SESSION-source crew ONLY
# ─────────────────────────────────────────────────────────────────────────────

def _is_fully_assigned(project):
    """
    Returns True only when all required shoot-day subservice roles
    are covered by SESSION-source CrewAssignments.
    PROJECT-board assignments are never counted here.
    """
    from collections import Counter
    lead = project.lead_set.first()
    if not lead:
        return False

    required_roles = Counter()
    inv = Invoice.objects.filter(lead=lead).prefetch_related('services__sub_services').first()
    if inv:
        for inv_svc in inv.services.all():
            for ss in inv_svc.sub_services.all():
                required_roles[(inv_svc.service_name, ss.id)] += 1
    else:
        for pkg in lead.packages.prefetch_related('services__sub_services').all():
            for pkg_svc in pkg.services.all():
                for ss in pkg_svc.sub_services.all():
                    required_roles[(pkg_svc.service_name, ss.id)] += 1

    if not required_roles:
        return False

    # Count only SESSION-source assignments
    assigned_roles = Counter()
    for ca in CrewAssignment.objects.filter(project=project, source='SESSION'):
        assigned_roles[(ca.service_name, ca.subservice_id)] += 1

    for role_key, needed in required_roles.items():
        if assigned_roles[role_key] < needed:
            return False
    return True


def session_list_view(request):
    today = date.today()
    all_projects = (
        ProjectDetail.objects
        .filter(lead__status='ACCEPTED')
        .order_by('start_date')
        .prefetch_related('assigned_employees__subservices', 'lead_set')
        .distinct()
    )

    grouped_projects = {}
    for proj in all_projects:
        proj.fully_assigned = _is_fully_assigned(proj)
        # session_crew_count = SESSION-only crew count (for badge display in template)
        proj.session_crew_count = (
            CrewAssignment.objects
            .filter(project=proj, source='SESSION')
            .values('employee_id').distinct().count()
        )
        key = proj.start_date.strftime('%B %Y') if proj.start_date else 'To Be Decided'
        grouped_projects.setdefault(key, []).append(proj)

    return render(request, 'sessions.html', {
        'grouped_projects': grouped_projects,
        'all_projects':     all_projects,
        'today':            today,
    })


def get_project_details_api(request, project_id):
    """
    Sessions modal API.
    Pre-selects only SESSION-source assignments.
    PROJECT-board crew is completely excluded.
    """
    project = get_object_or_404(ProjectDetail, id=project_id)
    lead    = project.lead_set.first()

    service_map = {}
    if lead:
        inv = Invoice.objects.filter(lead=lead).prefetch_related('services__sub_services').first()
        if inv:
            for inv_svc in inv.services.all():
                subs = list(inv_svc.sub_services.all())
                if not subs:
                    continue
                svc_key = inv_svc.service_name
                service_map.setdefault(svc_key, [])
                for ss in subs:
                    if ss not in service_map[svc_key]:
                        service_map[svc_key].append(ss)

        if not service_map:
            for pkg in lead.packages.prefetch_related('services__sub_services').all():
                for pkg_svc in pkg.services.all():
                    subs = list(pkg_svc.sub_services.all())
                    if not subs:
                        continue
                    svc_key = pkg_svc.service_name
                    service_map.setdefault(svc_key, [])
                    for ss in subs:
                        if ss not in service_map[svc_key]:
                            service_map[svc_key].append(ss)

    if not service_map:
        all_ss = list(SubService.objects.all())
        if all_ss:
            service_map['All Services'] = all_ss

    # Only SESSION-source assignments pre-populate the modal
    session_cas = CrewAssignment.objects.filter(project=project, source='SESSION')
    assignments_data = [
        {
            'employee_id':   ca.employee_id,
            'subservice_id': ca.subservice_id,
            'service_name':  ca.service_name or '',
            'date':          ca.date.strftime('%Y-%m-%d')  if ca.date       else '',
            'start_time':    ca.start_time.strftime('%H:%M') if ca.start_time else '',
            'end_time':      ca.end_time.strftime('%H:%M')   if ca.end_time   else '',
        }
        for ca in session_cas
    ]

    # assigned_ids = SESSION crew only
    session_assigned_ids = list(session_cas.values_list('employee_id', flat=True).distinct())

    # Build booked-dates map
    booked_dates_map = {}
    all_other_ca = CrewAssignment.objects.exclude(project=project).select_related('project')
    projects_with_detailed = set()

    for ca in all_other_ca:
        projects_with_detailed.add(ca.project_id)
        if ca.date:
            ds = ca.date.strftime('%Y-%m-%d')
            emp_id = ca.employee_id
            booked_dates_map.setdefault(emp_id, {}).setdefault(ds, [])
            if ca.project.project_name not in booked_dates_map[emp_id][ds]:
                booked_dates_map[emp_id][ds].append(ca.project.project_name)

    for p in ProjectDetail.objects.exclude(id=project.id).exclude(id__in=projects_with_detailed).prefetch_related('assigned_employees'):
        if p.start_date:
            ds = p.start_date.strftime('%Y-%m-%d')
            for emp in p.assigned_employees.all():
                booked_dates_map.setdefault(emp.id, {}).setdefault(ds, [])
                if p.project_name not in booked_dates_map[emp.id][ds]:
                    booked_dates_map[emp.id][ds].append(p.project_name)

    availability = {}
    for svc_name, subservices in service_map.items():
        ss_payload = []
        for ss in subservices:
            members = []
            for emp in Employee.objects.filter(subservices=ss).select_related('name'):
                display  = (emp.name.get_full_name() or emp.name.username) if emp.name else 'Unknown'
                initials = ''.join([c[0] for c in display.split() if c])[:2].upper()
                members.append({
                    'id': emp.id, 'name': display, 'initials': initials,
                    'booked_dates': booked_dates_map.get(emp.id, {}),
                })
            ss_payload.append({'id': ss.id, 'name': ss.name, 'members': members})
        availability[svc_name] = {'subservices': ss_payload}

    st = project.start_time.strftime('%H:%M') if getattr(project, 'start_time', None) else ''
    et = project.end_time.strftime('%H:%M')   if getattr(project, 'end_time',   None) else ''

    return JsonResponse({
        'project': {
            'id': project.id, 'name': project.project_name,
            'address': project.project_address,
            'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            'start_time': st, 'end_time': et,
        },
        'availability': availability,
        'assigned_ids':  session_assigned_ids,   # SESSION crew only
        'assignments':   assignments_data,        # SESSION assignments only
    })


def auto_generate_deliverable_tasks(project):
    lead = project.lead_set.first()
    if not lead:
        return
    inv = Invoice.objects.filter(lead=lead).prefetch_related('services__deliverables').first()
    if inv:
        for svc in inv.services.all():
            for d in svc.deliverables.all():
                Task.objects.get_or_create(
                    project=project, task_name=f"Deliver: {d.title}",
                    phase='POST', category='Deliverables', defaults={'status': 'ON_HOLD'},
                )
    else:
        for d in lead.deliverables.all():
            Task.objects.get_or_create(
                project=project, task_name=f"Deliver: {d.title}",
                phase='POST', category='Deliverables', defaults={'status': 'ON_HOLD'},
            )


@csrf_exempt
def save_team_assignment_api(request):
    """
    Sessions page crew save.
    Touches ONLY SESSION-source assignments. PROJECT-source is never touched.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    from .models import CrewAssignment, EmployeeNotification, SubService

    project_id      = request.POST.get('project_id')
    raw_ids         = request.POST.get('employee_ids', '[]')
    raw_assignments = request.POST.get('assignments', '[]')

    try:
        emp_ids = json.loads(raw_ids)
    except Exception:
        emp_ids = [int(x) for x in raw_ids.split(',') if x.strip()]

    try:
        assignment_records = json.loads(raw_assignments)
    except Exception:
        assignment_records = []

    project = get_object_or_404(ProjectDetail, id=project_id)

    # Delete only SESSION assignments — PROJECT assignments are untouched
    CrewAssignment.objects.filter(project=project, source='SESSION').delete()

    # Rebuild M2M: PROJECT crew stays, SESSION crew replaced with new selection
    project_emp_ids = list(
        CrewAssignment.objects.filter(project=project, source='PROJECT')
        .values_list('employee_id', flat=True).distinct()
    )
    all_emp_ids = list(set([str(x) for x in emp_ids] + [str(x) for x in project_emp_ids]))
    project.assigned_employees.set(all_emp_ids)
    project.save()

    generic_ss, _ = SubService.objects.get_or_create(
        name="General Assignment", defaults={'price': 0}
    )

    notified = set()
    for rec in assignment_records:
        emp_id       = rec.get('employee_id')
        ss_id        = rec.get('subservice_id')
        service_name = rec.get('service_name', '')
        rec_date     = rec.get('date')       or None
        rec_start    = rec.get('start_time') or None
        rec_end      = rec.get('end_time')   or None

        if not emp_id or not ss_id:
            continue
        try:
            emp = Employee.objects.get(id=emp_id)
            ss  = SubService.objects.get(id=ss_id)
        except Exception:
            continue

        CrewAssignment.objects.create(
            project=project, employee=emp, subservice=ss,
            service_name=service_name,
            date=rec_date, start_time=rec_start, end_time=rec_end,
            source='SESSION',
        )
        if emp_id not in notified:
            notified.add(emp_id)
            EmployeeNotification.objects.create(
                employee=emp, project=project, subservice=ss,
                title=f"New Assignment: {project.project_name}",
                message=f"You have been assigned to {project.project_name}. Your role: {ss.name}.",
                date=rec_date, start_time=rec_start,
            )

    return JsonResponse({'status': 'success', 'notified_count': len(notified)})


def get_admin_project_tasks(request, project_id):
    project = get_object_or_404(ProjectDetail, id=project_id)

    # Task dropdown shows only PROJECT-board crew
    project_crew_ids = list(
        CrewAssignment.objects.filter(project=project, source='PROJECT')
        .values_list('employee_id', flat=True).distinct()
    )
    if project_crew_ids:
        crew_queryset = Employee.objects.filter(id__in=project_crew_ids).select_related('team', 'name')
    else:
        crew_queryset = project.assigned_employees.select_related('team', 'name').all()

    team_members = []
    for emp in crew_queryset:
        display_name = (emp.name.get_full_name() or emp.name.username) if emp.name else "Unknown"
        initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()
        team_lower   = emp.team.name.lower() if emp.team else ""
        team_type    = "post" if "post" in team_lower else ("pre" if "pre" in team_lower else "general")
        team_members.append({
            "id": emp.id, "name": display_name, "initials": initials,
            "team_type": team_type, "team_name": emp.team.name if emp.team else "General",
        })

    def best_for_phase(phase_key):
        wanted = {"PRE": "pre", "SELECTION": "general", "POST": "post"}.get(phase_key, "general")
        for m in team_members:
            if m["team_type"] == wanted:
                return m["id"]
        for m in team_members:
            if m["team_type"] == "general":
                return m["id"]
        return team_members[0]["id"] if team_members else None

    phase_default = {
        "PRE": best_for_phase("PRE"),
        "SELECTION": best_for_phase("SELECTION"),
        "POST": best_for_phase("POST"),
    }

    grouped_tasks = {"PRE": [], "SELECTION": [], "POST": []}
    for task in project.tasks.select_related('assigned_to', 'assigned_to__name').all():
        phase_key = task.phase
        if phase_key not in grouped_tasks:
            grouped_tasks[phase_key] = []

        if task.assigned_to is None and team_members:
            default_id = phase_default.get(phase_key)
            if default_id:
                try:
                    task.assigned_to = Employee.objects.get(id=default_id)
                    task.save(update_fields=['assigned_to'])
                except Employee.DoesNotExist:
                    pass

        assigned_id   = None
        assigned_name = None
        if task.assigned_to and task.assigned_to.name:
            assigned_id   = task.assigned_to.id
            assigned_name = task.assigned_to.name.get_full_name() or task.assigned_to.name.username

        grouped_tasks[phase_key].append({
            "id": task.id, "title": task.task_name, "phase": task.phase,
            "category": task.category if task.category else "General",
            "assigned_to_id": assigned_id, "assigned_to_name": assigned_name,
            "status": task.status,
            "start_date": task.created_at.strftime('%Y-%m-%d') if task.created_at else "",
            "due_date":   task.due_date.strftime('%Y-%m-%d')   if task.due_date   else "",
            "progress":   100 if task.status == 'COMPLETED' else (50 if task.status == 'OPEN' else 10),
        })

    return JsonResponse({
        "team_members":  team_members,
        "phase_default": phase_default,
        "tasks":         grouped_tasks,
        "templates": [
            {"id": t.id, "phase": t.phase,
             "category": t.category.name if t.category else "General",
             "task_name": t.task_name}
            for t in TaskList.objects.all().select_related('category')
        ],
    })


@csrf_exempt
def add_project_task(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)

    project     = get_object_or_404(ProjectDetail, id=request.POST.get("project_id"))
    template_id = request.POST.get("template_id")
    raw_phase   = request.POST.get("phase", "PRE PRODUCTION")
    phase_map   = {'PRE PRODUCTION': 'PRE', 'SELECTION': 'SELECTION', 'POST PRODUCTION': 'POST'}
    db_phase    = phase_map.get(raw_phase.upper(), 'PRE')
    category    = "General"
    task_name   = request.POST.get("title", "New Task")

    if template_id:
        tmpl      = get_object_or_404(TaskList, id=template_id)
        db_phase  = tmpl.phase
        task_name = tmpl.task_name
        category  = tmpl.category.name if tmpl.category else "General"

    keyword       = {'PRE': 'pre', 'SELECTION': 'general', 'POST': 'post'}.get(db_phase, 'general')
    assigned_emps = project.assigned_employees.select_related('team').all()
    auto_assignee = None
    for emp in assigned_emps:
        if keyword in (emp.team.name.lower() if emp.team else ""):
            auto_assignee = emp
            break
    if auto_assignee is None:
        for emp in assigned_emps:
            if "general" in (emp.team.name.lower() if emp.team else ""):
                auto_assignee = emp
                break
    if auto_assignee is None and assigned_emps.exists():
        auto_assignee = assigned_emps.first()

    target_due_date = None
    if db_phase == 'PRE':
        existing_pre = project.tasks.filter(phase='PRE').exclude(due_date__isnull=True).first()
        target_due_date = existing_pre.due_date if existing_pre else None
    else:
        target_due_date = project.end_date

    Task.objects.create(
        project=project, phase=db_phase, category=category,
        task_name=task_name, status='ON_HOLD', assigned_to=auto_assignee,
        due_date=target_due_date,
    )
    return JsonResponse({"status": "success"})


@csrf_exempt
def update_project_task(request):
    if request.method == "POST":
        task = get_object_or_404(Task, id=request.POST.get("task_id"))
        if request.POST.get("title"):
            task.task_name = request.POST["title"].strip()

        assigned_to = request.POST.get("assigned_to")
        if assigned_to is not None:
            if assigned_to in ('', 'null'):
                task.assigned_to = None
            else:
                try:
                    task.assigned_to = Employee.objects.get(id=int(assigned_to))
                except (Employee.DoesNotExist, ValueError):
                    task.assigned_to = None

        status = request.POST.get("status")
        if status and status in ['OPEN', 'ON_HOLD', 'COMPLETED']:
            task.status = status

        due_date = request.POST.get("due_date")
        if due_date:
            try:
                task.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        task.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@csrf_exempt
def delete_project_task(request):
    if request.method == "POST":
        task = get_object_or_404(Task, id=request.POST.get("task_id"))
        task.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# EMPLOYEE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def employee_dashboard(request):
    from .models import CrewAssignment, EmployeeNotification

    employee     = request.user.employee_profile
    display_name = (employee.name.get_full_name() or employee.name.username) if employee.name else (request.user.get_full_name() or request.user.username)
    initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()

    accepted_project_ids = set(
        CrewAssignment.objects.filter(employee=employee, source='PROJECT', is_accepted=True)
        .values_list('project_id', flat=True).distinct()
    )
    session_project_ids = set(
        CrewAssignment.objects.filter(employee=employee, source='SESSION')
        .values_list('project_id', flat=True).distinct()
    )
    session_all_done_ids = set()
    for pid in session_project_ids:
        total = CrewAssignment.objects.filter(project_id=pid, employee=employee, source='SESSION').count()
        done  = CrewAssignment.objects.filter(project_id=pid, employee=employee, source='SESSION', is_accepted=True).count()
        if total > 0 and done == total:
            session_all_done_ids.add(pid)

    real_project_ids = set(
        CrewAssignment.objects.filter(employee=employee, source='PROJECT')
        .exclude(service_name='Accepted')
        .values_list('project_id', flat=True).distinct()
    )
    project_all_tasks_done_ids = set()
    for pid in real_project_ids:
        total_tasks = Task.objects.filter(project_id=pid, assigned_to=employee).count()
        done_tasks  = Task.objects.filter(project_id=pid, assigned_to=employee, status='COMPLETED').count()
        if total_tasks > 0 and done_tasks == total_tasks:
            project_all_tasks_done_ids.add(pid)

    completed_ids = session_all_done_ids | project_all_tasks_done_ids

    all_my_assignments = CrewAssignment.objects.filter(employee=employee).select_related('project').distinct()
    seen = set()
    ongoing_count = upcoming_count = completed_count = 0
    notification_projects_map = {}

    for asgn in all_my_assignments:
        pid = asgn.project_id
        if pid in seen:
            continue
        seen.add(pid)
        proj = asgn.project

        if proj.status == 'COMPLETED' or pid in completed_ids:
            completed_count += 1
        elif pid in accepted_project_ids:
            ongoing_count += 1
        else:
            upcoming_count += 1
            if pid not in notification_projects_map:
                notification_projects_map[pid] = proj
                proj.my_assignments = []
            notification_projects_map[pid].my_assignments.append(asgn)

    notification_projects = sorted(
        notification_projects_map.values(),
        key=lambda p: p.start_date if p.start_date else datetime.max.date()
    )[:10]

    unread_notifications = list(
        EmployeeNotification.objects.filter(employee=employee, is_read=False)
        .select_related('project', 'subservice').order_by('-created_at')[:15]
    )

    return render(request, 'teams/employee_dashboard.html', {
        'employee': employee, 'display_name': display_name, 'initials': initials,
        'ongoing_count': ongoing_count, 'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'notifications': notification_projects,
        'unread_notifications': unread_notifications,
        'unread_count': len(unread_notifications),
    })


@csrf_exempt
def employee_accept_project(request):
    from .models import CrewAssignment, SubService
    if request.method == "POST":
        project  = get_object_or_404(ProjectDetail, id=request.POST.get("project_id"))
        employee = request.user.employee_profile

        has_project_assignment = CrewAssignment.objects.filter(
            project=project, employee=employee, source='PROJECT'
        ).exists()

        if has_project_assignment:
            CrewAssignment.objects.filter(
                project=project, employee=employee, source='PROJECT'
            ).update(is_accepted=True)
            if project.status == 'ASSIGNED':
                project.status = 'PRE'
                project.save()
        else:
            generic_ss, _ = SubService.objects.get_or_create(
                name="General Assignment", defaults={'price': 0}
            )
            CrewAssignment.objects.get_or_create(
                project=project, employee=employee, source='PROJECT',
                defaults={'subservice': generic_ss, 'service_name': 'Accepted', 'is_accepted': True}
            )
            CrewAssignment.objects.filter(
                project=project, employee=employee, source='PROJECT'
            ).update(is_accepted=True)

        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


def employee_projects(request):
    from .models import CrewAssignment
    try:
        employee     = request.user.employee_profile
        display_name = (employee.name.get_full_name() or employee.name.username) if employee.name else "Unknown"
        initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()
        all_assigned = employee.assigned_projects.all()

        accepted_project_ids = set(
            CrewAssignment.objects.filter(employee=employee, source='PROJECT', is_accepted=True)
            .values_list('project_id', flat=True).distinct()
        )
        session_project_ids = set(
            CrewAssignment.objects.filter(employee=employee, source='SESSION')
            .values_list('project_id', flat=True).distinct()
        )
        session_all_done_ids = set()
        for pid in session_project_ids:
            total = CrewAssignment.objects.filter(project_id=pid, employee=employee, source='SESSION').count()
            done  = CrewAssignment.objects.filter(project_id=pid, employee=employee, source='SESSION', is_accepted=True).count()
            if total > 0 and done == total:
                session_all_done_ids.add(pid)

        project_all_tasks_done_ids = set()
        for pid in set(
            CrewAssignment.objects.filter(employee=employee, source='PROJECT')
            .exclude(service_name='Accepted')
            .values_list('project_id', flat=True).distinct()
        ):
            total_tasks = Task.objects.filter(project_id=pid, assigned_to=employee).count()
            done_tasks  = Task.objects.filter(project_id=pid, assigned_to=employee, status='COMPLETED').count()
            if total_tasks > 0 and done_tasks == total_tasks:
                project_all_tasks_done_ids.add(pid)

        completed_ids = (
            set(all_assigned.filter(status='COMPLETED').values_list('id', flat=True))
            | session_all_done_ids
            | project_all_tasks_done_ids
        )

        completed_projects = list(all_assigned.filter(id__in=completed_ids).order_by('-end_date'))
        ongoing_projects   = list(all_assigned.filter(id__in=accepted_project_ids).exclude(id__in=completed_ids).order_by('end_date'))
        upcoming_projects  = list(all_assigned.exclude(id__in=accepted_project_ids).exclude(id__in=completed_ids).order_by('start_date'))

        for proj in ongoing_projects + completed_projects + upcoming_projects:
            proj.my_assignments = list(
                CrewAssignment.objects.filter(project=proj, employee=employee)
                .exclude(service_name='Accepted')
                .select_related('subservice').order_by('source', 'id')
            )
        for proj in ongoing_projects + completed_projects:
            emp_tasks = proj.tasks.filter(assigned_to=employee)
            proj.total_emp_tasks     = emp_tasks.count()
            proj.completed_emp_tasks = emp_tasks.filter(status='COMPLETED').count()

    except AttributeError:
        ongoing_projects = upcoming_projects = completed_projects = []
        employee = None
        display_name = initials = ""

    return render(request, 'teams/employee_projects.html', {
        'ongoing_projects': ongoing_projects,
        'upcoming_projects': upcoming_projects,
        'completed_projects': completed_projects,
        'employee': employee,
        'display_name': display_name,
        'initials': initials,
    })


def employee_project_tasks(request, project_id):
    from .models import CrewAssignment
    project = get_object_or_404(ProjectDetail, id=project_id)
    try:
        employee     = request.user.employee_profile
        display_name = (employee.name.get_full_name() or employee.name.username) if employee.name else (request.user.get_full_name() or request.user.username)
        initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()

        has_real_project_assignment = CrewAssignment.objects.filter(
            project=project, employee=employee, source='PROJECT'
        ).exclude(service_name='Accepted').exists()

        has_session_assignment = CrewAssignment.objects.filter(
            project=project, employee=employee, source='SESSION'
        ).exists()

        if has_real_project_assignment:
            my_tasks    = project.tasks.filter(assigned_to=employee)
            other_tasks = project.tasks.exclude(assigned_to=employee)
            grouped_my_tasks = {}
            for task in my_tasks:
                phase_name = task.get_phase_display()
                cat_name   = task.category if task.category else "General"
                grouped_my_tasks.setdefault(phase_name, {}).setdefault(cat_name, []).append(task)
        else:
            my_tasks = other_tasks = project.tasks.none()
            grouped_my_tasks = {}

        session_assignments = list(
            CrewAssignment.objects.filter(project=project, employee=employee, source='SESSION')
            .select_related('subservice').order_by('date', 'start_time')
        )
        project_assignments = list(
            CrewAssignment.objects.filter(project=project, employee=employee, source='PROJECT')
            .exclude(service_name='Accepted').select_related('subservice').order_by('id')
        )
        my_assignments = session_assignments if session_assignments else project_assignments

    except AttributeError:
        employee = None
        display_name = initials = ""
        my_tasks = grouped_my_tasks = other_tasks = my_assignments = []
        has_real_project_assignment = has_session_assignment = False
        session_assignments = project_assignments = []

    return render(request, 'teams/employee_project_tasks.html', {
        'project': project,
        'my_tasks': my_tasks,
        'grouped_my_tasks': grouped_my_tasks,
        'other_tasks': other_tasks,
        'employee': employee,
        'display_name': display_name,
        'initials': initials,
        'my_assignments': my_assignments,
        'session_assignments': session_assignments,
        'project_assignments': project_assignments,
        'has_project_assignment': has_real_project_assignment,
        'has_session_assignment': has_session_assignment,
    })


@csrf_exempt
def mark_shoot_complete(request, assignment_id):
    from .models import CrewAssignment
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    try:
        employee = request.user.employee_profile
    except AttributeError:
        return JsonResponse({'status': 'error', 'message': 'No employee profile'}, status=403)

    ca = get_object_or_404(CrewAssignment, id=assignment_id, employee=employee)
    ca.is_accepted = True
    ca.save(update_fields=['is_accepted'])
    all_my_session = CrewAssignment.objects.filter(project=ca.project, employee=employee, source='SESSION')
    all_completed  = all_my_session.filter(is_accepted=True).count() == all_my_session.count()
    return JsonResponse({'status': 'success', 'all_completed': all_completed})


@csrf_exempt
def mark_task_complete(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        try:
            employee = request.user.employee_profile
            if task.status == 'COMPLETED':
                return JsonResponse({'status': 'error', 'message': 'Already completed'}, status=400)
            if task.assigned_to is not None and task.assigned_to != employee:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

            task.status = 'COMPLETED'
            task.save()

            project       = task.project
            current_phase = task.phase

            if not project.tasks.filter(phase=current_phase).exclude(status='COMPLETED').exists():
                if current_phase == 'PRE':
                    project.status = 'SELECTION'
                elif current_phase == 'SELECTION':
                    project.status = 'POST'
                elif current_phase == 'POST':
                    if not project.tasks.filter(phase='POST').exclude(status='COMPLETED').exists():
                        project.status = 'COMPLETED'
                project.save()

            total_tasks     = project.tasks.filter(assigned_to=employee).count()
            completed_tasks = project.tasks.filter(assigned_to=employee, status='COMPLETED').count()
            return JsonResponse({'status': 'success', 'total_tasks': total_tasks, 'completed_tasks': completed_tasks})

        except AttributeError:
            return JsonResponse({'status': 'error', 'message': 'No employee profile'}, status=403)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def get_employee_notifications(request):
    try:
        employee = request.user.employee_profile
    except AttributeError:
        return JsonResponse({'notifications': [], 'unread_count': 0})

    from .models import EmployeeNotification
    notifs = EmployeeNotification.objects.filter(
        employee=employee
    ).select_related('project', 'subservice').order_by('-created_at')[:20]

    data = [
        {
            'id': n.id, 'title': n.title, 'message': n.message,
            'project':    n.project.project_name if n.project else '',
            'subservice': n.subservice.name      if n.subservice else '',
            'date':       n.date.strftime('%d %b, %Y') if n.date else '',
            'start_time': str(n.start_time)[:5]  if n.start_time else '',
            'is_read':    n.is_read,
            'created_at': n.created_at.strftime('%d %b %Y, %H:%M'),
        }
        for n in notifs
    ]
    return JsonResponse({'notifications': data, 'unread_count': sum(1 for n in data if not n['is_read'])})


@csrf_exempt
def mark_notification_read(request, notif_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    from .models import EmployeeNotification
    notif = get_object_or_404(EmployeeNotification, id=notif_id)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'status': 'success'})


@csrf_exempt
def mark_all_notifications_read(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    try:
        employee = request.user.employee_profile
    except AttributeError:
        return JsonResponse({'status': 'error'}, status=403)
    from .models import EmployeeNotification
    EmployeeNotification.objects.filter(employee=employee, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})