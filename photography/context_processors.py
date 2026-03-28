from .models import *

def notifications_context(request):
    if request.user.is_authenticated:
        try:
            user_profile = request.user.employee_profile
            
            # 1. Base query for unread notifications
            base_query = EmployeeNotification.objects.filter(
                employee=user_profile, 
                is_read=False
            )
            
            # 2. Get the TOTAL count for the red badge (before slicing)
            total_unread = base_query.count()
            
            # 3. Get the 10 most recent for the dropdown list
            notifications = base_query.order_by('-created_at')[:10]
            
            return {
                'unread_notifications': notifications,
                'unread_count': total_unread
            }
        except Exception as e:
            print(f"Context Processor Error: {e}")
            return {'unread_notifications': [], 'unread_count': 0}
            
    return {'unread_notifications': [], 'unread_count': 0}