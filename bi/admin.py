from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import BIReportCache, BusinessInsight


@admin.register(BIReportCache)
class BIReportCacheAdmin(admin.ModelAdmin):
    list_display = ['business', 'report_type', 'period_start', 'period_end', 'updated_at']
    list_filter = ['report_type', 'business', 'created_at']
    search_fields = ['business__name', 'report_type']
    readonly_fields = ['created_at', 'updated_at', 'data_preview']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('business', 'report_type', 'period_start', 'period_end')
        }),
        ('Data', {
            'fields': ('data_preview',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def data_preview(self, obj):
        if obj.data:
            import json
            preview = json.dumps(obj.data, indent=2)[:500]
            return format_html('<pre style="background:#f5f5f5;padding:10px;border-radius:5px;overflow:auto;max-height:300px;">{}</pre>', preview)
        return 'No data'
    data_preview.short_description = 'Data Preview'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(BusinessInsight)
class BusinessInsightAdmin(admin.ModelAdmin):
    list_display = [
        'business', 'title', 'insight_type_colored', 'category_colored', 
        'metric_value_display', 'is_active', 'created_at'
    ]
    list_filter = ['insight_type', 'category', 'is_active', 'business', 'created_at']
    search_fields = ['title', 'description', 'business__name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Insight Information', {
            'fields': ('business', 'title', 'insight_type', 'category')
        }),
        ('Details', {
            'fields': ('description', 'recommendation', 'metric_value')
        }),
        ('Status', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def insight_type_colored(self, obj):
        colors = {
            'positive': 'green',
            'warning': 'orange',
            'critical': 'red',
            'opportunity': 'blue',
        }
        color = colors.get(obj.insight_type, 'black')
        type_display = obj.get_insight_type_display()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, type_display
        )
    insight_type_colored.short_description = 'Type'
    
    def category_colored(self, obj):
        colors = {
            'sales': 'blue',
            'inventory': 'orange',
            'financial': 'green',
            'hr': 'purple',
            'customer': 'teal',
            'general': 'gray',
        }
        color = colors.get(obj.category, 'black')
        category_display = obj.get_category_display()
        return format_html(
            '<span style="color: {};">{}</span>',
            color, category_display
        )
    category_colored.short_description = 'Category'
    
    def metric_value_display(self, obj):
        if obj.metric_value:
            if obj.category == 'sales' or obj.category == 'financial':
                return format_html('<b>TZS {:.2f}</b>', obj.metric_value)
            return format_html('<b>{}</b>', obj.metric_value)
        return '-'
    metric_value_display.short_description = 'Value'
    
    actions = ['mark_as_active', 'mark_as_inactive', 'generate_new_insights']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} insights marked as active.')
    mark_as_active.short_description = 'Mark selected insights as Active'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} insights marked as inactive.')
    mark_as_inactive.short_description = 'Mark selected insights as Inactive'
    
    def generate_new_insights(self, request, queryset):
        from .services import BusinessIntelligenceService
        
        businesses = set(insight.business for insight in queryset)
        count = 0
        for business in businesses:
            service = BusinessIntelligenceService(business)
            insights = service.generate_insights()
            
            for insight_data in insights:
                BusinessInsight.objects.update_or_create(
                    business=business,
                    title=insight_data['title'],
                    defaults={
                        'insight_type': insight_data['type'],
                        'category': insight_data['category'],
                        'description': insight_data['description'],
                        'recommendation': insight_data['recommendation'],
                        'metric_value': insight_data['metric_value'],
                        'is_active': True,
                        'expires_at': timezone.now().date() + timezone.timedelta(days=30)
                    }
                )
                count += 1
            self.message_user(request, f'Generated {count} insights for {business.name}')
    generate_new_insights.short_description = 'Generate fresh insights for selected'


class BIDashboardAdmin(admin.ModelAdmin):
    """Custom admin view for BI dashboard"""
    
    def changelist_view(self, request, extra_context=None):
        from .services import BusinessIntelligenceService
        
        extra_context = extra_context or {}
        
        if request.user.business:
            service = BusinessIntelligenceService(request.user.business)
            
            try:
                kpi = service.get_kpi_dashboard()
                insights = service.generate_insights()
                
                extra_context.update({
                    'kpi': kpi,
                    'insights': insights[:5],
                    'has_data': True
                })
            except Exception as e:
                extra_context.update({
                    'has_data': False,
                    'error': str(e)
                })
        
        return super().changelist_view(request, extra_context=extra_context)


admin.site.site_header = 'BizSmart Business Intelligence'
admin.site.site_title = 'BizSmart BI Admin'
admin.site.index_title = 'Business Intelligence Dashboard'