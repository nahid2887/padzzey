from django.apps import AppConfig


class SellerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seller'
    verbose_name = 'Seller Management'    
    def ready(self):
        """Import signals when app is ready"""
        import seller.signals