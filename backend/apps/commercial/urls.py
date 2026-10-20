from rest_framework.routers import SimpleRouter
from .views import CommercialViewSet

router = SimpleRouter()
router.register('documents', CommercialViewSet, basename='commercial-document')
urlpatterns = router.urls
