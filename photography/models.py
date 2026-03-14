from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User


class ProjectDetail(models.Model):
    STATUS_CHOICES = [
        ('ASSIGNED', 'To Be Assigned'),
        ('PRE', 'Pre Production'),
        ('SELECTION', 'Selection'),
        ('POST', 'Post Production'),
        ('COMPLETED', 'Completed'),
    ]
    project_name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15)
    project_address = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    assigned_employees = models.ManyToManyField('Employee', blank=True, related_name='assigned_projects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Project Detail"
        verbose_name_plural = "Project Details"

    def __str__(self):
        return self.project_name

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("The end date cannot be earlier than the start date.")


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    name = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_profile')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.name} ({self.team.name if self.team else 'No Team'})"
    

class Service(models.Model):
    service_name = models.CharField(max_length=200)
    team = models.CharField(max_length=200)
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.service_name
    
    
class Deliverable(models.Model):
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.title} (₹{self.price})"


class SubService(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} (₹{self.price})"


class Package(models.Model):
    package_name = models.CharField(max_length=200)
    @property
    def total_cost(self):
        total = 0.0
        for service in self.services.all():
            total += float(service.cost) * service.qty
        return total
    
    def __str__(self):
        return self.package_name


class PackageService(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="services")
    service_name = models.CharField(max_length=255)
    sub_services = models.ManyToManyField(SubService, blank=True)
    qty = models.IntegerField(default=1)
    cost = models.FloatField(default=0)


class Lead(models.Model):
    LEAD_SOURCE_CHOICES = [
        ('Website', 'Website'),
        ('Social Media', 'Social Media'),
        ('Referral', 'Referral'),
        ('Direct', 'Direct'),
        ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('NEW', 'NEW'),
        ('FOLLOW_UP', 'FOLLOW UP'),
        ('ACCEPTED', 'ACCEPTED'),
        ('LOST', 'LOST'),
    ]

    name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    lead_source = models.CharField(max_length=50, choices=LEAD_SOURCE_CHOICES, default='Other', blank=True, null=True)
    packages = models.ManyToManyField(Package, blank=True, related_name='leads')
    deliverables = models.ManyToManyField(Deliverable, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    project = models.ForeignKey(ProjectDetail, on_delete=models.SET_NULL, null=True, blank=True)
    follow_up_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'

    @property
    def total_cost(self):
        total = 0.0
        for pkg in self.packages.all():
            total += float(pkg.total_cost)
        for d in self.deliverables.all():
            total += float(d.price)
        for a in self.additional_services.all():
            total += float(a.price) * int(a.qty)
        return total

    def __str__(self):
        return f"{self.name} - {self.mobile_number}"


class TaskCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Task Category"
        verbose_name_plural = "Task Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class TaskList(models.Model):
    PHASE_CHOICES = [
        ('PRE', 'PRE PRODUCTION'),
        ('SELECTION', 'SELECTION'),
        ('POST', 'POST PRODUCTION'),
    ]

    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='PRE')
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True)
    task_name = models.CharField(max_length=255)

    class Meta:
        ordering = ['phase', 'category__name', 'task_name']
        verbose_name = "Task List"
        verbose_name_plural = "Task List"

    def __str__(self):
        category_display = self.category.name if self.category else "General"
        return f"[{self.get_phase_display()}] {category_display} - {self.task_name}"

class Task(models.Model):
    PHASE_CHOICES = [
        ('PRE', 'PRE PRODUCTION'),
        ('SELECTION', 'SELECTION'),
        ('POST', 'POST PRODUCTION'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
    ]

    project = models.ForeignKey('ProjectDetail', on_delete=models.CASCADE, related_name='tasks')
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='PRE')
    category = models.CharField(max_length=255)
    task_name = models.CharField(max_length=255)
    assigned_to = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ON_HOLD')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['phase', 'category', 'due_date']
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self):
        emp_name = self.assigned_to.name if self.assigned_to else "Unassigned"
        return f"{self.task_name} ({emp_name}) - {self.project.project_name}"
    

class Invoice(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PARTIAL = 'PARTIAL', 'Partial'
        COMPLETED = 'COMPLETED', 'Completed'

    lead = models.OneToOneField('Lead', on_delete=models.CASCADE, unique=True, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    due_date = models.DateField(null=True, blank=True)
    pre_paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    notes = models.TextField(blank=True, default="Thank you for your business.")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        total = 0.0
        for service in self.services.all():
            total += float(service.price) * service.qty
        return total

    @property
    def tax_amount(self):
        post_discount = self.subtotal - float(self.discount_amount)
        return post_discount * (float(self.tax_rate) / 100)

    @property
    def grand_total(self):
        post_discount = self.subtotal - float(self.discount_amount)
        return post_discount + self.tax_amount - float(self.pre_paid_amount)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.lead.name}"


class InvoiceService(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='services', on_delete=models.CASCADE)
    service_name = models.CharField(max_length=255)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    deliverables = models.ManyToManyField(Deliverable, blank=True)
    sub_services = models.ManyToManyField(SubService, blank=True) 

    @property
    def total_amount(self):
        return self.qty * self.price


class PaymentRecord(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=100)
    date = models.DateField(default=timezone.now)
    reference = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Payment ₹{self.amount} for Invoice {self.invoice.invoice_number}"
    

class AdditionalService(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} (₹{self.price})"
    
class LeadAdditionalService(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='additional_services')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    qty = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.qty}x {self.name} for {self.lead.name}"