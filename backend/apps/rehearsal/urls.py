from rest_framework.routers import DefaultRouter
from .views import RehearsalViewSet

router = DefaultRouter()
router.register('jobs', RehearsalViewSet, basename='rehearsal-job')
urlpatterns = router.urls
