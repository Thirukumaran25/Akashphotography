from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, F
from django.utils import timezone
from django.db.models import Q
from datetime import date
from .models import *
import json
from weasyprint import HTML
from django.conf import settings
import base64
import os
from django.contrib.staticfiles import finders
from datetime import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


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
    full_path = os.path.join(settings.STATIC_ROOT, relative_path)
    try:
        with open(full_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        ext = relative_path.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'svg': 'svg+xml'}.get(ext, 'png')
        return f"data:image/{mime};base64,{encoded}"
    except FileNotFoundError:
        return ""


@csrf_exempt
def generate_pdf(request):
    if request.method == "POST":
        data = json.loads(request.body)
        html_content = data.get("html", "")
        filename = data.get("filename", "Invoice.pdf")
        try:
            pdf_bytes = HTML(string=html_content).write_pdf()
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)


def get_image_base64(request):
    image_path = request.GET.get('path', '')
    if '..' in image_path or image_path.startswith('/'):
        return JsonResponse({"error": "Invalid path"}, status=400)

    full_path = None
    found = finders.find(image_path)
    if found:
        full_path = found
    if not full_path:
        candidate = os.path.join(settings.STATIC_ROOT, image_path)
        if os.path.exists(candidate):
            full_path = candidate
    if not full_path:
        for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
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


def home(request):
    today = date.today()
    Lead.objects.filter(status='NEW', follow_up_date__lte=today).update(status='FOLLOW_UP')

    all_leads = Lead.objects.all()

    def calculate_leads_total(leads_queryset):
        total = 0
        for lead in leads_queryset:
            if lead.package:
                pkg_total = lead.package.services.aggregate(
                    total=Sum(F('cost') * F('qty'))
                )['total']
                total += pkg_total or 0
        return total

    new_leads = all_leads.filter(status='NEW')
    follow_up = all_leads.filter(status='FOLLOW_UP')
    accepted = all_leads.filter(status='ACCEPTED')
    lost = all_leads.filter(status='LOST')

    context = {
        'new_leads': new_leads,
        'follow_up': follow_up,
        'accepted': accepted,
        'lost': lost,
        'total_leads': all_leads.count(),
        'total_amount': f"{calculate_leads_total(all_leads):,.0f}",
        'accepted_amount': f"{calculate_leads_total(accepted):,.0f}",
        'lost_quoted_amount': f"{calculate_leads_total(lost):,.0f}",
    }
    return render(request, 'leads.html', context)


@csrf_exempt
def update_lead_status(request):
    if request.method == "POST":
        lead_id = request.POST.get("lead_id")
        new_status = request.POST.get("status")

        if lead_id and new_status:
            lead = get_object_or_404(Lead, id=lead_id)
            lead.status = new_status
            lead.save()

            if new_status == 'ACCEPTED' and lead.project:
                lead.project.status = 'ASSIGNED'
                lead.project.save()

                if lead.package:
                    invoice, created = Invoice.objects.get_or_create(
                        lead=lead,
                        defaults={
                            "invoice_number": f"AK-{Lead.objects.count() + 100}",
                            "due_date": lead.project.start_date,
                        }
                    )

                    if created:
                        for pkg_service in lead.package.services.all():
                            invoice_service = InvoiceService.objects.create(
                                invoice=invoice,
                                service_name=pkg_service.service_name,
                                qty=pkg_service.qty,
                                price=pkg_service.cost
                            )
                            if pkg_service.deliverables.exists():
                                invoice_service.deliverables.set(pkg_service.deliverables.all())
                            if pkg_service.persons.exists():
                                invoice_service.persons.set(pkg_service.persons.all())

                return JsonResponse({"success": True, "invoice_url": f"/invoice/edit/{lead.id}/"})
            return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


def projects(request):
    def format_projects(queryset):
        formatted_list = []
        for proj in queryset:
            lead = proj.lead_set.first()
            client_name = lead.name if lead else "Unknown Client"
            start_str = proj.start_date.strftime('%d %b, %Y') if proj.start_date else 'TBD'
            end_str = proj.end_date.strftime('%d %b, %Y') if proj.end_date else 'TBD'

            team = []
            for m in proj.assigned_employees.all():
                if m.name:
                    display_name = m.name.get_full_name() or m.name.username
                else:
                    display_name = "Unknown"
                initials = "".join([n[0] for n in display_name.split() if n])[:2].upper()
                team.append({"initials": initials})

            formatted_list.append({
                "id": proj.id,
                "client_name": client_name,
                "event_type": proj.project_name,
                "start_date": start_str,
                "end_date": end_str,
                "team": team,
            })
        return formatted_list

    context = {
        'assigned': format_projects(ProjectDetail.objects.filter(status='ASSIGNED', lead__status='ACCEPTED')),
        'pre_cards': format_projects(ProjectDetail.objects.filter(status='PRE')),
        'selection': format_projects(ProjectDetail.objects.filter(status='SELECTION')),
        'post': format_projects(ProjectDetail.objects.filter(status='POST')),
        'completed': format_projects(ProjectDetail.objects.filter(status='COMPLETED')),
    }

    return render(request, 'projects.html', context)


def get_project_details(request, project_id):
    project = get_object_or_404(ProjectDetail, id=project_id)
    lead = project.lead_set.first()

    def get_team_members(team_keyword):
        members = Employee.objects.filter(team__name__icontains=team_keyword)
        result = []
        for m in members:
            # FIX: safely extract string name from User object
            if m.name:
                display_name = m.name.get_full_name() or m.name.username
            else:
                display_name = "Unknown"
            initials = "".join([p[0] for p in display_name.split() if p])[:2].upper()
            result.append({"id": m.id, "name": display_name, "initials": initials})
        return result

    data = {
        "client_name": lead.name if lead else project.project_name,
        "location": project.project_address,
        "start_session": "TBD",
        "event_type": project.project_name,
        "start_date": project.start_date.strftime('%d %b, %Y') if project.start_date else "TBD",
        "end_date": project.end_date.strftime('%d %b, %Y') if project.end_date else "TBD",
        "general_team": get_team_members('General'),
        "pre_team": get_team_members('Pre'),
        "post_team": get_team_members('Post'),
    }
    return JsonResponse(data)


@csrf_exempt
def assign_team_to_project(request):
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        member_ids = request.POST.get("members", "").split(",")

        project = get_object_or_404(ProjectDetail, id=project_id)

        if member_ids and member_ids[0] != "":
            employees = Employee.objects.filter(id__in=member_ids)
            project.assigned_employees.set(employees)

        if project.status == 'ASSIGNED':
            project.status = 'PRE'
            project.save()
            auto_generate_deliverable_tasks(project)

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
    employee = Employee.objects.all()
    return render(request, 'team_members.html', {'employees': employee})


def create_lead(request):
    if request.method == "POST":
        project = ProjectDetail.objects.create(
            project_name=request.POST.get("project_name"),
            mobile_number=request.POST.get("project_mobile"),
            project_address=request.POST.get("project_address"),
            start_date=request.POST.get("start_date"),
            end_date=request.POST.get("end_date")
        )

        package_id = request.POST.get("package")
        package = Package.objects.filter(id=package_id).first() if package_id else None

        Lead.objects.create(
            name=request.POST.get("name"),
            mobile_number=request.POST.get("mobile_number"),
            email=request.POST.get("email") or None,
            address=request.POST.get("address") or None,
            lead_source=request.POST.get("lead_source") or 'Other',
            follow_up_date=request.POST.get("follow_up_date") or None,
            status='NEW',
            package=package,
            project=project
        )
        return redirect('home')

    packages = Package.objects.all()
    teams = Team.objects.all()
    available_deliverables = Deliverable.objects.all()
    available_persons = Person.objects.all()

    packages_with_total = []
    for pkg in packages:
        packages_with_total.append({
            "id": pkg.id,
            "package_name": pkg.package_name,
            "total_cost": pkg.total_cost
        })

    return render(request, "create_lead.html", {
        "packages": packages_with_total,
        "teams": teams,
        "available_deliverables": available_deliverables,
        "available_persons": available_persons,
    })


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
    data = [
        {
            "id":        t.id,
            "phase":     t.phase,                                    
            "category":  t.category.name if t.category else "General",
            "task_name": t.task_name,
        }
        for t in templates
    ]
    return JsonResponse({"templates": data})

def save_task_template(request):
    """
    POST /save-task-template/
    Body: { phase, category, task_name }
    Creates TaskCategory if it doesn't exist, then creates TaskList.
    Returns: { id, phase, category, task_name }
    """
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)
 
    data      = json.loads(request.body)
    phase     = data.get("phase", "PRE")
    cat_name  = (data.get("category") or "General").strip()
    task_name = (data.get("task_name") or "").strip()
 
    if not task_name:
        return JsonResponse({"status": "error", "message": "task_name required"}, status=400)
 
    category, _ = TaskCategory.objects.get_or_create(name=cat_name)
    task = TaskList.objects.create(
        phase     = phase,
        category  = category,
        task_name = task_name,
    )
    return JsonResponse({
        "id":        task.id,
        "phase":     task.phase,
        "category":  category.name,
        "task_name": task.task_name,
    })
 
def save_task_category(request):
    """
    POST /save-task-category/
    Body: { name }
    Returns: { id, name }
    """
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)
 
    data = json.loads(request.body)
    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"status": "error", "message": "name required"}, status=400)
 
    cat, _ = TaskCategory.objects.get_or_create(name=name)
    return JsonResponse({"id": cat.id, "name": cat.name})
 
def save_package(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)
 
    data         = json.loads(request.body)
    package_id   = data.get("package_id")
    package_name = data.get("package_name", "").strip()
    services     = data.get("services", [])
    task_ids_map = data.get("task_template_ids", {}) 
 
    if not package_name:
        return JsonResponse({"status": "error", "message": "Package name required"}, status=400)
 
    # ── Create or update package ──────────────────────────────────────────────
    if package_id:
        pkg = get_object_or_404(Package, id=package_id)
        pkg.package_name = package_name
        pkg.save()
        pkg.services.all().delete()
    else:
        pkg = Package.objects.create(package_name=package_name)
 
    # ── Save services (unchanged logic) ──────────────────────────────────────
    for s in services:
        svc = PackageService.objects.create(
            package      = pkg,
            service_name = s["service_name"],
            qty          = int(s.get("qty", 1)),
            cost         = float(s.get("cost", 0)),
        )
        for pid in s.get("person_ids", []):
            try:
                svc.persons.add(Person.objects.get(id=pid))
            except Person.DoesNotExist:
                pass
        for did in s.get("deliverable_ids", []):
            try:
                svc.deliverables.add(Deliverable.objects.get(id=did))
            except Deliverable.DoesNotExist:
                pass
 
    # ── Save task template associations ──────────────────────────────────────
    pkg.task_templates.clear()
    for phase_key, ids in task_ids_map.items():
        for tid in ids:
            try:
                pkg.task_templates.add(TaskList.objects.get(id=tid))
            except TaskList.DoesNotExist:
                pass
 
    return JsonResponse({"status": "success", "package_id": pkg.id})

def get_package(request, pk=None, package_id=None):
    """
    GET /get-package/<id>/
    Returns package details including task_template_ids for the edit modal.
    Accepts both ?pk and ?package_id URL kwargs for compatibility.
    """
    lookup = pk or package_id
    pkg = get_object_or_404(Package, id=lookup)
 
    services = []
    for svc in pkg.services.prefetch_related('persons', 'deliverables').all():
        services.append({
            "service_name": svc.service_name,
            "qty":          svc.qty,
            "cost":         str(svc.cost),
            "persons": [
                {"id": p.id, "name": p.name, "price": str(p.price)}
                for p in svc.persons.all()
            ],
            "deliverables": [
                {"id": d.id, "title": d.title, "price": str(d.price)}
                for d in svc.deliverables.all()
            ],
        })
 
    task_template_ids = {"PRE": [], "SELECTION": [], "POST": []}
    for t in pkg.task_templates.select_related('category').all():
        if t.phase in task_template_ids:
            task_template_ids[t.phase].append(t.id)
 
    return JsonResponse({
        "id":                pkg.id,
        "name":              pkg.package_name,
        "services":          services,
        "task_template_ids": task_template_ids,
    })

def invoice(request):
    all_invoices = Invoice.objects.all().select_related('lead', 'lead__project').order_by('-created_at')
    total_paid = PaymentRecord.objects.aggregate(total=Sum('amount'))['total'] or 0.00

    total_upcoming = 0.0
    total_past_due = 0.0
    today = date.today()

    pending_invoices = []
    completed_invoices = []

    for inv in all_invoices:
        paid_amount = inv.payments.aggregate(total=Sum('amount'))['total'] or 0.00
        balance = float(inv.grand_total) - float(paid_amount)

        inv.display_amount = inv.grand_total
        inv.balance = balance
        inv.project_name = inv.lead.project.project_name if inv.lead.project else inv.lead.name

        if inv.status in [Invoice.PaymentStatus.PENDING, Invoice.PaymentStatus.PARTIAL]:
            pending_invoices.append(inv)
            if inv.due_date and inv.due_date < today:
                total_past_due += balance
            else:
                total_upcoming += balance
        else:
            completed_invoices.append(inv)

    context = {
        'total_paid': total_paid,
        'total_upcoming': total_upcoming,
        'total_past_due': total_past_due,
        'pending_invoices': pending_invoices,
        'completed_invoices': completed_invoices,
    }

    return render(request, 'invoice.html', context)


def create_invoice(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    invoice = get_object_or_404(Invoice, lead=lead)
    available_deliverables = Deliverable.objects.all()
    available_persons = Person.objects.all()

    context = {
        'lead': lead,
        'invoice': invoice,
        'services': invoice.services.all(),
        'subtotal': invoice.subtotal,
        'grand_total': invoice.grand_total,
        'tax_amount': invoice.tax_amount,
        'pre_paid': invoice.pre_paid_amount,
        'available_deliverables': available_deliverables,
        'available_persons': available_persons,
    }
    return render(request, "create_invoice.html", context)


@csrf_exempt
def log_payment(request):
    if request.method == "POST":
        invoice_id = request.POST.get("invoice_id")
        amount = request.POST.get("amount")
        method = request.POST.get("payment_method")
        payment_date = request.POST.get("date")
        reference = request.POST.get("reference", "")

        invoice = get_object_or_404(Invoice, id=invoice_id)

        PaymentRecord.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=method,
            date=payment_date,
            reference=reference
        )

        all_payments = invoice.payments.aggregate(total=Sum('amount'))['total'] or 0.00
        remaining_due = float(invoice.grand_total) - float(all_payments)

        if remaining_due <= 0:
            invoice.status = Invoice.PaymentStatus.COMPLETED
        else:
            invoice.status = Invoice.PaymentStatus.PARTIAL

        invoice.save()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@csrf_exempt
def save_invoice(request):
    if request.method == "POST":
        data = json.loads(request.body)
        invoice_id = data.get("invoice_id")

        try:
            invoice = Invoice.objects.get(id=invoice_id)
            invoice.pre_paid_amount = data.get("pre_paid_amount", 0)
            invoice.discount_amount = data.get("discount_amount", 0)
            invoice.tax_rate = data.get("tax_rate", 0)
            invoice.notes = data.get("notes", "")

            due_date = data.get("due_date")
            if due_date:
                invoice.due_date = due_date

            invoice.save()
            
            # Clear old services to rebuild them based on the updated form
            invoice.services.all().delete()

            for s_data in data.get("services", []):
                new_service = InvoiceService.objects.create(
                    invoice=invoice,
                    service_name=s_data.get("service_name"),
                    qty=int(s_data.get("qty", 1)),
                    price=float(s_data.get("price", 0))
                )

                deliverable_ids = s_data.get("deliverable_ids", [])
                if deliverable_ids:
                    new_service.deliverables.set(Deliverable.objects.filter(id__in=deliverable_ids))

                person_ids = s_data.get("person_ids", [])
                if person_ids:
                    new_service.persons.set(Person.objects.filter(id__in=person_ids))

            if invoice.lead and invoice.lead.project:
                if invoice.lead.project.status in ['PRE', 'SELECTION', 'POST', 'COMPLETED']:
                    auto_generate_deliverable_tasks(invoice.lead.project)

            return JsonResponse({"status": "success", "invoice_id": invoice.id})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

@csrf_exempt
def generate_invoice_from_lead(request):
    if request.method == "POST":
        lead_id = request.POST.get("lead_id")
        lead = get_object_or_404(Lead, id=lead_id)

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

            due_date = lead.project.start_date if lead.project else None

            new_invoice = Invoice.objects.create(
                lead=lead,
                invoice_number=invoice_number,
                due_date=due_date,
            )

            if lead.package:
                for pkg_service in lead.package.services.all():
                    invoice_service = InvoiceService.objects.create(
                        invoice=new_invoice,
                        service_name=pkg_service.service_name,
                        qty=pkg_service.qty,
                        price=pkg_service.cost
                    )
                    if pkg_service.deliverables.exists():
                        invoice_service.deliverables.set(pkg_service.deliverables.all())
                    if pkg_service.persons.exists():
                        invoice_service.persons.set(pkg_service.persons.all())

        return JsonResponse({"success": True, "invoice_url": f"/invoice/edit/{lead.id}/"})
    return JsonResponse({"success": False}, status=400)


def get_invoice_data(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    paid_amount = invoice.payments.aggregate(total=Sum('amount'))['total'] or 0.00

    services = []
    for s in invoice.services.all():
        services.append({
            "service_name": s.service_name,
            "qty": s.qty,
            "price": float(s.price),
            "total_amount": float(s.total_amount),
            "deliverables": [d.title for d in s.deliverables.all()]
        })

    subtotal = float(invoice.subtotal)
    discount = float(invoice.discount_amount)
    tax = float(invoice.tax_amount)
    pre_paid = float(invoice.pre_paid_amount)
    total_amount = (subtotal - discount) + tax
    balance_due = total_amount - pre_paid - float(paid_amount)

    data = {
        "invoice_number": invoice.invoice_number,
        "client_name": invoice.lead.name,
        "project_name": invoice.lead.project.project_name if invoice.lead.project else "",
        "email": invoice.lead.email or "client@email.com",
        "due_date": invoice.due_date.strftime('%m/%d/%Y') if invoice.due_date else "N/A",
        "services": services,
        "subtotal": subtotal,
        "discount_amount": discount,
        "tax_amount": tax,
        "total_amount": total_amount,
        "pre_paid_amount": pre_paid,
        "paid_amount": float(paid_amount),
        "balance_due": max(0, balance_due),
    }
    return JsonResponse(data)


def search_leads_for_invoice(request):
    query = request.GET.get('q', '').strip()
    leads = Lead.objects.filter(invoice__isnull=True)

    if query:
        leads = leads.filter(
            Q(name__icontains=query) |
            Q(project__project_name__icontains=query) |
            Q(email__icontains=query) |
            Q(mobile_number__icontains=query)
        )
    leads = leads[:5]

    results = []
    for lead in leads:
        results.append({
            "id": lead.id,
            "name": lead.name,
            "project_name": lead.project.project_name if lead.project else "No Project",
            "email": lead.email or "",
            "mobile": lead.mobile_number
        })

    return JsonResponse({"results": results})


@csrf_exempt
def add_person(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        price = data.get("price", 0)
        if not name:
            return JsonResponse({"error": "Name required"}, status=400)
        person = Person.objects.create(name=name, price=price)
        return JsonResponse({"id": person.id, "name": person.name, "price": float(person.price)})
    return JsonResponse({"error": "Invalid"}, status=400)


@csrf_exempt
def add_deliverable_quick(request):
    if request.method == "POST":
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        price = data.get("price", 0)
        if not title:
            return JsonResponse({"error": "Title required"}, status=400)
        d = Deliverable.objects.create(title=title, price=price)
        return JsonResponse({"id": d.id, "title": d.title, "price": float(d.price)})
    return JsonResponse({"error": "Invalid"}, status=400)


def get_persons(request):
    persons = list(Person.objects.values('id', 'name', 'price'))
    for p in persons:
        p['price'] = float(p['price'])
    return JsonResponse({"persons": persons})


def employees_list(request):
    all_employees = Employee.objects.select_related('team').prefetch_related('assigned_projects')

    employee_data = []
    active_count = 0
    today = date.today()

    for emp in all_employees:
        active_projects = emp.assigned_projects.exclude(status='COMPLETED').order_by('end_date')

        if active_projects.exists():
            active_count += 1

        deadlines = active_projects[:2]
        upcoming = active_projects[:3]

        if emp.name:
            display_name = emp.name.get_full_name() or emp.name.username
        else:
            display_name = "Unknown"

        initials = "".join([n[0] for n in display_name.split() if n])[:2].upper()

        employee_data.append({
            'id': emp.id,
            'name': display_name,
            'initials': initials,
            'role': emp.team.name if emp.team else "General",
            'deadlines': deadlines,
            'upcoming': upcoming,
        })

    context = {
        'employees': employee_data,
        'total_employees': all_employees.count(),
        'active_employees': active_count,
    }

    return render(request, 'employees.html', context)


def session_list_view(request):
    all_projects = ProjectDetail.objects.filter(
        lead__status='ACCEPTED'
    ).order_by('start_date').prefetch_related('assigned_employees').distinct()

    today = datetime.now().date()
    grouped_projects = {}

    for proj in all_projects:
        if proj.start_date:
            month_key = proj.start_date.strftime('%B %Y')
            if month_key not in grouped_projects:
                grouped_projects[month_key] = []
            grouped_projects[month_key].append(proj)

    context = {
        'grouped_projects': grouped_projects,
    }
    return render(request, 'sessions.html', context)


def get_project_details_api(request, project_id):
    project = get_object_or_404(ProjectDetail, id=project_id)

    # 🌟 FIX: Find overlapping projects in the SAME MONTH and YEAR
    if project.start_date:
        overlapping_projects = ProjectDetail.objects.filter(
            start_date__year=project.start_date.year,
            start_date__month=project.start_date.month
        ).exclude(id=project.id)
    else:
        overlapping_projects = ProjectDetail.objects.none()

    booked_employee_details = {}
    for p in overlapping_projects:
        date_str = p.start_date.strftime('%d %b, %Y') if p.start_date else 'TBD'
        booking_info = f"{p.project_name} ({date_str})"
        
        for emp_id in p.assigned_employees.values_list('id', flat=True):
            if emp_id not in booked_employee_details:
                booked_employee_details[emp_id] = []
            booked_employee_details[emp_id].append(booking_info)

    assigned_ids = list(project.assigned_employees.values_list('id', flat=True))

    availability_data = {}
    teams = Team.objects.prefetch_related('members').all()

    for team in teams:
        team_members = []
        for emp in team.members.all():
            if emp.name:
                display_name = emp.name.get_full_name() or emp.name.username
            else:
                display_name = "Unknown"

            initials = "".join([n[0] for n in display_name.split() if n])[:2].upper()
            
            # If the employee is in ANY project this month, they are booked
            is_booked = emp.id in booked_employee_details
            
            # Join multiple bookings into a single string with new lines
            booking_text = " \n".join(booked_employee_details.get(emp.id, []))

            team_members.append({
                'id': emp.id,
                'name': display_name,
                'initials': initials,
                'is_booked': is_booked,
                'booking_text': booking_text,
            })
        availability_data[team.name] = team_members

    # Format time strings safely
    start_time_str = project.start_time.strftime('%H:%M') if getattr(project, 'start_time', None) else ''
    end_time_str = project.end_time.strftime('%H:%M') if getattr(project, 'end_time', None) else ''

    response_data = {
        'project': {
            'id': project.id,
            'name': project.project_name,
            'address': project.project_address,
            'start_date': project.start_date.strftime('%d/%m/%Y') if project.start_date else '',
            'end_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
            'start_time': start_time_str, 
            'end_time': end_time_str,     
        },
        'availability': availability_data,
        'assigned_ids': assigned_ids, 
    }
    return JsonResponse(response_data)


def auto_generate_deliverable_tasks(project):
    lead = project.lead_set.first()

    if not lead:
        return

    # 1. Fetch all Master Task Templates attached to the Package (PRE, SELECTION, POST)
    if lead.package:
        # Loop through all the templates you selected for this package in the admin panel
        for template in lead.package.task_templates.all():
            cat_name = template.category.name if template.category else "General"
            
            # get_or_create ensures we never duplicate tasks if this runs twice
            Task.objects.get_or_create(
                project=project,
                task_name=template.task_name,
                phase=template.phase,
                category=cat_name,
                defaults={'status': 'ON_HOLD'}
            )

    # 2. Fetch specific Deliverables for POST PRODUCTION
    # We prioritize the final Invoice services, but fallback to the base Package services if no invoice exists yet.
    invoice = Invoice.objects.filter(lead=lead).first()

    if invoice:
        # Generate from Invoice Services
        for service in invoice.services.all():
            for d in service.deliverables.all():
                Task.objects.get_or_create(
                    project=project,
                    task_name=d.title,
                    phase='POST',
                    category=service.service_name, 
                    defaults={'status': 'ON_HOLD'}
                )
    elif lead.package:
        for service in lead.package.services.all():
            for d in service.deliverables.all():
                Task.objects.get_or_create(
                    project=project,
                    task_name=d.title,
                    phase='POST',
                    category=service.service_name, 
                    defaults={'status': 'ON_HOLD'}
                )

@csrf_exempt
def save_team_assignment_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        project_id = data.get('project_id')
        selected_employee_ids = data.get('employee_ids', [])
        deadline_date = data.get('deadline_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        project = get_object_or_404(ProjectDetail, id=project_id)
        project.assigned_employees.set(selected_employee_ids)

        if deadline_date:
            try:
                project.end_date = datetime.strptime(deadline_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            project.end_date = None
                
        project.start_time = start_time if start_time else None
        project.end_time = end_time if end_time else None

        if project.status == 'ASSIGNED':
            project.status = 'PRE'
            
        project.save()
        auto_generate_deliverable_tasks(project)
        if project.end_date:
            project.tasks.all().update(due_date=project.end_date)

        return JsonResponse({'status': 'success', 'message': 'Team assigned successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)


def get_admin_project_tasks(request, project_id):
    project = get_object_or_404(ProjectDetail, id=project_id)

    # ── Team members with team_type classification ───────────────────────────
    team_members = []
    for emp in project.assigned_employees.select_related('team', 'name').all():
        display_name = (emp.name.get_full_name() or emp.name.username) if emp.name else "Unknown"
        initials     = "".join([n[0] for n in display_name.split() if n])[:2].upper()
        team_lower   = emp.team.name.lower() if emp.team else ""

        if "post" in team_lower:
            team_type = "post"
        elif "pre" in team_lower:
            team_type = "pre"
        else:
            team_type = "general"

        team_members.append({
            "id":        emp.id,
            "name":      display_name,
            "initials":  initials,
            "team_type": team_type,
            "team_name": emp.team.name if emp.team else "General",
        })

    # ── Phase → best-fit employee ────────────────────────────────────────────
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
        "PRE":       best_for_phase("PRE"),
        "SELECTION": best_for_phase("SELECTION"),
        "POST":      best_for_phase("POST"),
    }

    # ── Group tasks by phase DB key (PRE / SELECTION / POST) ─────────────────
    # Keys match Task.phase field values so the JS PHASES array can look them up directly.
    grouped_tasks = {"PRE": [], "SELECTION": [], "POST": []}

    for task in project.tasks.select_related('assigned_to', 'assigned_to__name').all():
        phase_key = task.phase   # DB value: 'PRE', 'SELECTION', 'POST'
        if phase_key not in grouped_tasks:
            grouped_tasks[phase_key] = []

        # Auto-assign unassigned tasks
        if task.assigned_to is None and team_members:
            default_id = phase_default.get(phase_key)
            if default_id:
                try:
                    task.assigned_to = Employee.objects.get(id=default_id)
                    task.save(update_fields=['assigned_to'])
                except Employee.DoesNotExist:
                    pass

        # Serialize assigned employee
        assigned_id   = None
        assigned_name = None
        if task.assigned_to and task.assigned_to.name:
            assigned_id   = task.assigned_to.id
            assigned_name = (
                task.assigned_to.name.get_full_name()
                or task.assigned_to.name.username
            )

        grouped_tasks[phase_key].append({
            "id":               task.id,
            "title":            task.task_name,
            "phase":            task.phase,           # DB key
            # ↓ THIS was the missing field causing everything to show as "General"
            "category":         task.category if task.category else "General",
            "assigned_to_id":   assigned_id,
            "assigned_to_name": assigned_name,
            "status":           task.status,
            "start_date":       task.created_at.strftime('%Y-%m-%d') if task.created_at else "",
            "due_date":         task.due_date.strftime('%Y-%m-%d') if task.due_date else "",
            "progress":         100 if task.status == 'COMPLETED' else (50 if task.status == 'OPEN' else 10),
        })

    # ── Templates ─────────────────────────────────────────────────────────────
    template_data = [
        {
            "id":        t.id,
            "phase":     t.phase,                                    # DB key: PRE / SELECTION / POST
            "category":  t.category.name if t.category else "General",
            "task_name": t.task_name,
        }
        for t in TaskList.objects.all().select_related('category')
    ]

    return JsonResponse({
        "team_members":  team_members,
        "phase_default": phase_default,
        "tasks":         grouped_tasks,   
        "templates":     template_data,
    })


@csrf_exempt
def add_project_task(request):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)

    project_id   = request.POST.get("project_id")
    template_id  = request.POST.get("template_id")
    custom_title = request.POST.get("title", "New Task")
    raw_phase    = request.POST.get("phase", "PRE")  

    project  = get_object_or_404(ProjectDetail, id=project_id)
    db_phase = raw_phase if raw_phase in ("PRE","SELECTION","POST") else "PRE"

    task_name = custom_title
    category  = "General"
    if template_id:
        template  = get_object_or_404(TaskList, id=template_id)
        db_phase  = template.phase
        task_name = template.task_name
        category  = template.category.name if template.category else "General"

  
    keyword_map = {"PRE": "pre", "SELECTION": "SELECTION", "POST": "post"}
    keyword     = keyword_map.get(db_phase, "general")
    assigned_emps = project.assigned_employees.select_related('team').all()

    auto_assignee = None
    for emp in assigned_emps:
        if keyword in (emp.team.name.lower() if emp.team else ""):
            auto_assignee = emp; break
    if auto_assignee is None:
        for emp in assigned_emps:
            if "general" in (emp.team.name.lower() if emp.team else ""):
                auto_assignee = emp; break
    if auto_assignee is None and assigned_emps.exists():
        auto_assignee = assigned_emps.first()

    Task.objects.create(
        project     = project,
        phase       = db_phase,
        category    = category,
        task_name   = task_name,
        status      = 'ON_HOLD',
        assigned_to = auto_assignee,
    )
    return JsonResponse({"status": "success"})


@csrf_exempt
def add_project_task(request):
    if request.method == "POST":
        project_id   = request.POST.get("project_id")
        template_id  = request.POST.get("template_id")
        custom_title = request.POST.get("title", "New Task")
        raw_phase    = request.POST.get("phase", "PRE PRODUCTION")

        project = get_object_or_404(ProjectDetail, id=project_id)

        phase_map = {
            'PRE PRODUCTION':  'PRE',
            'SELECTION':       'SELECTION',
            'POST PRODUCTION': 'POST',
        }
        db_phase = phase_map.get(raw_phase.upper(), 'PRE')

        # ── Determine phase from template if provided ─────────────────────
        if template_id:
            template = get_object_or_404(TaskList, id=template_id)
            db_phase  = template.phase

        # ── Find best-fit assignee for this phase ─────────────────────────
        phase_to_team_keyword = {
            'PRE':       'pre',
            'SELECTION': 'general',
            'POST':      'post',
        }
        keyword = phase_to_team_keyword.get(db_phase, 'general')

        # Assigned employees on this project
        assigned_emps = project.assigned_employees.select_related('team').all()

        auto_assignee = None
        # 1st pass: exact keyword match
        for emp in assigned_emps:
            team_name = emp.team.name.lower() if emp.team else ""
            if keyword in team_name:
                auto_assignee = emp
                break

        # 2nd pass: 'general' fallback
        if auto_assignee is None:
            for emp in assigned_emps:
                team_name = emp.team.name.lower() if emp.team else ""
                if "general" in team_name:
                    auto_assignee = emp
                    break

        # 3rd pass: whoever is first
        if auto_assignee is None and assigned_emps.exists():
            auto_assignee = assigned_emps.first()

        # ── Create the task ───────────────────────────────────────────────
        if template_id:
            Task.objects.create(
                project     = project,
                phase       = template.phase,
                category    = template.category.name if template.category else "SELECTION",
                task_name   = template.task_name,
                status      = 'ON_HOLD',
                assigned_to = auto_assignee,   # ← auto-assign
            )
        else:
            Task.objects.create(
                project     = project,
                phase       = db_phase,
                category    = "SELECTION",
                task_name   = custom_title,
                status      = 'ON_HOLD',
                assigned_to = auto_assignee,   # ← auto-assign
            )

        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error"}, status=400)


@csrf_exempt
def update_project_task(request):
    """
    FIX: This view was missing entirely — admin task saves were silently failing.
    Handles title, assigned_to, status, due_date updates from the task modal.
    """
    if request.method == "POST":
        task_id = request.POST.get("task_id")
        task = get_object_or_404(Task, id=task_id)

        title = request.POST.get("title")
        if title:
            task.task_name = title.strip()

        assigned_to = request.POST.get("assigned_to")
        if assigned_to is not None:
            if assigned_to == '' or assigned_to == 'null':
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
                from datetime import date as date_type
                task.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        start_date = request.POST.get("start_date")
        # start_date is auto_now_add so we don't update it, just ignore

        task.save()
        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@csrf_exempt
def delete_project_task(request):
    """
    FIX: This view was missing entirely — delete was silently failing.
    """
    if request.method == "POST":
        task_id = request.POST.get("task_id")
        task = get_object_or_404(Task, id=task_id)
        task.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


# ----------------------------------------
# EMPLOYEE VIEWS
# ----------------------------------------

def employee_dashboard(request):
    """
    FIX: Notifications now ONLY show ASSIGNED (Upcoming) projects waiting to be accepted.
    """
    employee = request.user.employee_profile

    if employee.name:
        display_name = employee.name.get_full_name() or employee.name.username
    else:
        display_name = request.user.get_full_name() or request.user.username

    initials = "".join([n[0] for n in display_name.split() if n])[:2].upper()

    ongoing_count = employee.assigned_projects.filter(status__in=['PRE', 'SELECTION', 'POST']).count()
    upcoming_count = employee.assigned_projects.filter(status='ASSIGNED').count()
    completed_count = employee.assigned_projects.filter(status='COMPLETED').count()
    
    # 🌟 FIX: Only show 'ASSIGNED' projects in the notification list
    notifications = employee.assigned_projects.filter(status='ASSIGNED').order_by('start_date')[:6]

    context = {
        'employee': employee,
        'display_name': display_name,
        'initials': initials,
        'ongoing_count': ongoing_count,
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'notifications': notifications,
    }
    return render(request, 'teams/employee_dashboard.html', context)


@csrf_exempt
def employee_accept_project(request):
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        project = get_object_or_404(ProjectDetail, id=project_id)
        
        if project.status == 'ASSIGNED':
            project.status = 'PRE'
            project.save()
            return JsonResponse({"status": "success"})
            
    return JsonResponse({"status": "error"}, status=400)


def employee_projects(request):
    try:
        employee = request.user.employee_profile
        display_name = employee.name.get_full_name() or employee.name.username if employee.name else "Unknown"
        initials = "".join([n[0] for n in display_name.split() if n])[:2].upper()

        ongoing_projects = list(employee.assigned_projects.filter(status__in=['PRE', 'SELECTION', 'POST']).order_by('end_date'))
        completed_projects = list(employee.assigned_projects.filter(status='COMPLETED').order_by('-end_date'))
        
        # 🌟 NEW: Fetch Upcoming Projects (Not accepted yet)
        upcoming_projects = list(employee.assigned_projects.filter(status='ASSIGNED').order_by('start_date'))

        for proj in ongoing_projects:
            emp_tasks = proj.tasks.filter(assigned_to=employee)
            proj.total_emp_tasks = emp_tasks.count()
            proj.completed_emp_tasks = emp_tasks.filter(status='COMPLETED').count()

        for proj in completed_projects:
            emp_tasks = proj.tasks.filter(assigned_to=employee)
            proj.total_emp_tasks = emp_tasks.count()
            proj.completed_emp_tasks = emp_tasks.filter(status='COMPLETED').count()

    except AttributeError:
        ongoing_projects = []
        upcoming_projects = [] # Default fallback
        completed_projects = []
        employee = None
        display_name = ""
        initials = ""

    context = {
        'ongoing_projects': ongoing_projects,
        'upcoming_projects': upcoming_projects, # 🌟 Pass to template
        'completed_projects': completed_projects,
        'employee': employee,
        'display_name': display_name,
        'initials': initials,
    }
    return render(request, 'teams/employee_projects.html', context)


def employee_project_tasks(request, project_id):
    project = get_object_or_404(ProjectDetail, id=project_id)

    try:
        employee = request.user.employee_profile

        if employee.name:
            display_name = employee.name.get_full_name() or employee.name.username
        else:
            display_name = request.user.get_full_name() or request.user.username
        initials = "".join([n[0] for n in display_name.split() if n])[:2].upper()

        my_tasks = project.tasks.filter(assigned_to=employee)
        other_tasks = project.tasks.exclude(assigned_to=employee)

        grouped_my_tasks = {}
        for task in my_tasks:
            phase_name = task.get_phase_display()
            cat_name = task.category if task.category else "General"
            
            if phase_name not in grouped_my_tasks:
                grouped_my_tasks[phase_name] = {}
            if cat_name not in grouped_my_tasks[phase_name]:
                grouped_my_tasks[phase_name][cat_name] = []
                
            grouped_my_tasks[phase_name][cat_name].append(task)

    except AttributeError:
        employee = None
        display_name = ""
        initials = ""
        my_tasks = []
        grouped_my_tasks = {}
        other_tasks = project.tasks.all()

    context = {
        'project': project,
        'my_tasks': my_tasks, 
        'grouped_my_tasks': grouped_my_tasks,
        'other_tasks': other_tasks,
        'employee': employee,
        'display_name': display_name,
        'initials': initials,
    }
    return render(request, 'teams/employee_project_tasks.html', context)

@csrf_exempt
def mark_task_complete(request, task_id):
    """
    FIX: employees can mark tasks OPEN or ON_HOLD as complete (previously only OPEN allowed).
    FIX: smart phase progression logic preserved.
    """
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)

        try:
            employee = request.user.employee_profile

            # FIX: allow completing tasks that are OPEN or ON_HOLD
            if task.assigned_to == employee and task.status != 'COMPLETED':
                task.status = 'COMPLETED'
                task.save()

                project = task.project
                current_phase = task.phase

                # Smart phase progression: advance project if all tasks in phase done
                incomplete_tasks_in_phase = project.tasks.filter(
                    phase=current_phase
                ).exclude(status='COMPLETED').exists()

                if not incomplete_tasks_in_phase:
                    if current_phase == 'PRE':
                        project.status = 'SELECTION'
                    elif current_phase == 'SELECTION':
                        project.status = 'POST'
                    elif current_phase == 'POST':
                        if not project.tasks.exclude(status='COMPLETED').exists():
                            project.status = 'COMPLETED'

                    project.save()

                # Return updated counts so the frontend progress bar refreshes
                total_tasks = project.tasks.filter(assigned_to=employee).count()
                completed_tasks = project.tasks.filter(
                    assigned_to=employee, status='COMPLETED'
                ).count()

                return JsonResponse({
                    'status': 'success',
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                })
            else:
                return JsonResponse(
                    {'status': 'error', 'message': 'Unauthorized or task already completed'},
                    status=403
                )

        except AttributeError:
            return JsonResponse({'status': 'error', 'message': 'No employee profile'}, status=403)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)