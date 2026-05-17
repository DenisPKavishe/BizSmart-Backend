from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending all emails in BizSmart"""
    
    @staticmethod
    def send_welcome_email(user, password=None):
        """Send welcome email to new user"""
        subject = f"Welcome to BizSmart, {user.first_name or user.username}!"
        
        context = {
            'user': user,
            'business': user.business,
            'password': password,
            'login_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
        }
        
        html_message = render_to_string('emails/welcome.html', context)
        plain_message = strip_tags(html_message)
        
        return EmailService._send_email(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_invoice_email(invoice, customer_email, pdf_attachment=None):
        """Send invoice email to customer"""
        subject = f"Invoice #{invoice.invoice_number} from {invoice.business.name}"
        
        context = {
            'invoice': invoice,
            'business': invoice.business,
            'due_date': invoice.due_date,
            'total_amount': invoice.total_amount,
        }
        
        html_message = render_to_string('emails/invoice.html', context)
        plain_message = strip_tags(html_message)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer_email],
        )
        email.attach_alternative(html_message, "text/html")
        
        if pdf_attachment:
            email.attach(f"Invoice_{invoice.invoice_number}.pdf", pdf_attachment, 'application/pdf')
        
        return email.send()
    
    @staticmethod
    def send_low_stock_alert(products, business):
        """Send low stock alert to inventory manager"""
        if not products:
            return
        
        subject = f"⚠️ Low Stock Alert - {business.name}"
        
        context = {
            'business': business,
            'products': products,
            'alert_count': len(products),
        }
        
        html_message = render_to_string('emails/low_stock.html', context)
        plain_message = strip_tags(html_message)
        
        # Get inventory managers' emails
        from core.models import User
        recipients = User.objects.filter(
            business=business,
            role__name='inventory_manager',
            is_active=True
        ).values_list('email', flat=True)
        
        if not recipients:
            # Fallback to owner
            recipients = User.objects.filter(
                business=business,
                role__name='owner',
                is_active=True
            ).values_list('email', flat=True)
        
        return EmailService._send_email(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=list(recipients)
        )
    
    @staticmethod
    def send_payroll_summary(payroll, business):
        """Send payroll summary to accountant and owner"""
        subject = f"Payroll Summary - {business.name} - {payroll.month}/{payroll.year}"
        
        context = {
            'business': business,
            'payroll': payroll,
            'employees': payroll.items.all(),
        }
        
        html_message = render_to_string('emails/payroll_summary.html', context)
        plain_message = strip_tags(html_message)
        
        # Send to owner and accountant
        from core.models import User
        recipients = User.objects.filter(
            business=business,
            role__name__in=['owner', 'accountant'],
            is_active=True
        ).values_list('email', flat=True)
        
        return EmailService._send_email(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=list(recipients)
        )
    
    @staticmethod
    def send_daily_sales_report(business, sales_data, date):
        """Send daily sales report to owner and manager"""
        subject = f"Daily Sales Report - {business.name} - {date}"
        
        context = {
            'business': business,
            'date': date,
            'sales_data': sales_data,
            'total_sales': sales_data.get('total_sales', 0),
            'transactions': sales_data.get('transactions', 0),
        }
        
        html_message = render_to_string('emails/daily_sales.html', context)
        plain_message = strip_tags(html_message)
        
        # Send to owner and manager
        from core.models import User
        recipients = User.objects.filter(
            business=business,
            role__name__in=['owner', 'general_manager'],
            is_active=True
        ).values_list('email', flat=True)
        
        return EmailService._send_email(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=list(recipients)
        )
    
    @staticmethod
    def send_password_reset_email(user, reset_link):
        """Send password reset email"""
        subject = "Reset Your BizSmart Password"
        
        context = {
            'user': user,
            'reset_link': reset_link,
            'business': user.business,
        }
        
        html_message = render_to_string('emails/password_reset.html', context)
        plain_message = strip_tags(html_message)
        
        return EmailService._send_email(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def _send_email(subject, plain_message, html_message, recipient_list):
        """Internal method to send email"""
        email_enabled = getattr(settings, 'ENABLE_EMAIL_NOTIFICATIONS', False)
        
        if not email_enabled:
            logger.info(f"Email notifications disabled. Would send: {subject} to {recipient_list}")
            return True
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list,
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            logger.info(f"Email sent: {subject} to {recipient_list}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False