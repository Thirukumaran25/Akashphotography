from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, F
from django.utils import timezone
from django.db.models import Q
from datetime import date
from .models import *
import json
from weasyprint import HTML
from asgiref.sync import async_to_sync


@csrf_exempt
def generate_pdf(request):
    """ Generates a PDF using WeasyPrint """
    if request.method == "POST":
        data = json.loads(request.body)
        html_content = data.get("html", "")
        filename = data.get("filename", "Invoice.pdf")

        try:
            base_url = request.build_absolute_uri('/')
            pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf()

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            print("WeasyPrint Error:", str(e))
            return JsonResponse({"error": str(e)}, status=500)
            
    return JsonResponse({"error": "Invalid request"}, status=400)



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
            return JsonResponse({"success": True})
            
    return JsonResponse({"success": False}, status=400)


def projects(request):
    # Helper function to format projects for the Kanban board
    def format_projects(queryset):
        formatted_list = []
        for proj in queryset:
            lead = proj.lead_set.first()
            client_name = lead.name if lead else "Unknown Client"
            start_str = proj.start_date.strftime('%d %b, %Y') if proj.start_date else 'TBD'
            end_str = proj.end_date.strftime('%d %b, %Y') if proj.end_date else 'TBD'
            
            # Get initials of assigned team members
            team = [{"initials": "".join([p[0] for p in m.name.split()])[:2].upper()} for m in proj.assigned_employees.all()]
            
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


# --- API: GET PROJECT DETAILS FOR TEAM POPUP ---
def get_project_details(request, project_id):
    project = get_object_or_404(ProjectDetail, id=project_id)
    lead = project.lead_set.first()
    
    def get_team_members(team_keyword):
        members = Employee.objects.filter(team__name__icontains=team_keyword)
        return [{"id": m.id, "name": m.name, "initials": "".join([p[0] for p in m.name.split()])[:2].upper()} for m in members]

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


# --- API: ASSIGN TEAM & MOVE TO PRE-PRODUCTION ---
@csrf_exempt
def assign_team_to_project(request):
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        member_ids = request.POST.get("members", "").split(",")
        
        project = get_object_or_404(ProjectDetail, id=project_id)
        
        if member_ids and member_ids[0] != "":
            employees = Employee.objects.filter(id__in=member_ids)
            project.assigned_employees.set(employees)
            
        project.status = 'PRE'
        project.save()
        return JsonResponse({"success": True})
        
    return JsonResponse({"success": False}, status=400)


# --- API: DRAG AND DROP STATUS UPDATE ---
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
    employee=Employee.objects.all()
    return render(request, 'team_members.html',employee)



def create_lead(request):
    if request.method == "POST":
        # 1. Save Project Details
        project = ProjectDetail.objects.create(
            project_name=request.POST.get("project_name"),
            mobile_number=request.POST.get("project_mobile"),
            project_address=request.POST.get("project_address"),
            start_date=request.POST.get("start_date"),
            end_date=request.POST.get("end_date")
        )

        # 2. Get the selected Package
        package_id = request.POST.get("package")
        package = Package.objects.filter(id=package_id).first() if package_id else None

        # 3. Create the Lead and link everything
        Lead.objects.create(
            name=request.POST.get("name"),
            mobile_number=request.POST.get("mobile_number"),
            email=request.POST.get("email") or None,
            address=request.POST.get("address") or None,
            lead_source=request.POST.get("lead_source") or 'Other',
            follow_up_date=request.POST.get("follow_up_date") or None,
            status='NEW', # Automatically goes to the NEW column
            package=package,
            project=project # Links to the project we just created
        )
        return redirect('home')

    packages = Package.objects.all()
    teams = Team.objects.all()
    
    # 🌟 NEW: Fetch all available deliverables to send to the dropdown
    available_deliverables = Deliverable.objects.all()

    packages_with_total = []

    for pkg in packages:
        # Utilize the @property we created in the model
        packages_with_total.append({
            "id": pkg.id,
            "package_name": pkg.package_name,
            "total_cost": pkg.total_cost
        })

    return render(request, "create_lead.html",{
        "packages": packages_with_total,
        "teams": teams,
        "available_deliverables": available_deliverables, # Sent to frontend
    })


@csrf_exempt
def save_package(request):
    if request.method == "POST":
        data = json.loads(request.body)
        package_id = data.get("package_id")  # None if new
        name = data["package_name"]
        services = data["services"]

        if package_id:
            # Update existing package
            package = Package.objects.get(id=package_id)
            package.package_name = name
            package.save()
            package.services.all().delete()  # clear old services
        else:
            package = Package.objects.create(package_name=name)

        # Save new services
        for s in services:
            ps = PackageService.objects.create(
                package=package,
                service_name=s["service_name"],
                qty=s["qty"],
                cost=s["cost"],
            )
            # Assign multiple teams (ManyToMany)
            if "teams" in s:
                ps.teams.set(s["teams"])
                
            # 🌟 NEW: Link the selected Deliverable models using IDs
            if "deliverable_ids" in s:
                deliverables_qs = Deliverable.objects.filter(id__in=s["deliverable_ids"])
                ps.deliverables.set(deliverables_qs)

        return JsonResponse({"status": "success", "id": package.id, "name": package.package_name})


def get_package(request, pk):
    package = Package.objects.get(id=pk)
    services = []
    for s in package.services.all():
        services.append({
            "service_name": s.service_name,
            "qty": s.qty,
            "cost": s.cost,
            # 🌟 NEW: Send Deliverables as a list of dictionaries so JS has the price data
            "deliverables": [
                {"id": d.id, "title": d.title, "price": float(d.price)} for d in s.deliverables.all()
            ],
            "teams": list(s.teams.values_list("id", flat=True)),
            "team_names": list(s.teams.values_list("name", flat=True)),
        })
    return JsonResponse({"name": package.package_name, "services": services})


@csrf_exempt
def delete_package(request, pk):
    if request.method == "POST":
        try:
            Package.objects.get(id=pk).delete()
            return JsonResponse({"status": "success"})
        except Package.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Package not found"})
        


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

                if lead.package and not hasattr(lead, 'invoice'):
                    count = Lead.objects.count() + 100
                    invoice_number = f"AK-{count}"
                    due_date = lead.project.start_date

                    new_invoice = Invoice.objects.create(
                        lead=lead, 
                        invoice_number=invoice_number,
                        due_date=due_date,
                    )

                    for pkg_service in lead.package.services.all():
                        invoice_service = InvoiceService.objects.create(
                            invoice=new_invoice,
                            service_name=pkg_service.service_name,
                            qty=pkg_service.qty,
                            price=pkg_service.cost
                        )
                        
                        if pkg_service.deliverables.exists():
                            invoice_service.deliverables.set(pkg_service.deliverables.all())
                
                return JsonResponse({"success": True, "invoice_url": f"/invoice/edit/{lead.id}/"})

            return JsonResponse({"success": True})
            
    return JsonResponse({"success": False}, status=400)


def invoice(request):
    """ Loads the main Invoice List page with calculated stats and groups """
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
    """ Loads the editable, design-perfect invoice creation page """
    lead = get_object_or_404(Lead, id=lead_id)
    invoice = get_object_or_404(Invoice, lead=lead)
    available_deliverables = Deliverable.objects.all()
    context = {
        'lead': lead,
        'invoice': invoice,
        'services': invoice.services.all(),
        'subtotal': invoice.subtotal,
        'grand_total': invoice.grand_total,
        'tax_amount': invoice.tax_amount,
        'pre_paid': invoice.pre_paid_amount,
        'available_deliverables': available_deliverables,
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
        
        # Log the payment with all fields from the modal
        PaymentRecord.objects.create(
            invoice=invoice, 
            amount=amount, 
            payment_method=method,
            date=payment_date,
            reference=reference
        )
        
        # Check total payments vs total dues to automatically update status
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
                    deliverables_qs = Deliverable.objects.filter(id__in=deliverable_ids)
                    new_service.deliverables.set(deliverables_qs)

            return JsonResponse({"status": "success", "invoice_id": invoice.id})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@csrf_exempt
def generate_invoice_from_lead(request):
    if request.method == "POST":
        lead_id = request.POST.get("lead_id")
        lead = get_object_or_404(Lead, id=lead_id)

        # 1. Force status to ACCEPTED
        lead.status = 'ACCEPTED'
        lead.save()

        if lead.project:
            lead.project.status = 'ASSIGNED'
            lead.project.save()

        # 2. Safely create Invoice if it doesn't exist yet
        if not hasattr(lead, 'invoice'):
            
            # 🌟 NEW BULLETPROOF UNIQUE ID GENERATOR 🌟
            base_count = Invoice.objects.count() + 100
            invoice_number = f"AK-{base_count}"
            
            # Keep incrementing until we find a number that definitely does not exist
            while Invoice.objects.filter(invoice_number=invoice_number).exists():
                base_count += 1
                invoice_number = f"AK-{base_count}"

            due_date = lead.project.start_date if lead.project else None

            # Create the blank invoice wrapper
            new_invoice = Invoice.objects.create(
                lead=lead,
                invoice_number=invoice_number,
                due_date=due_date,
            )

            # Copy package services if they exist
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