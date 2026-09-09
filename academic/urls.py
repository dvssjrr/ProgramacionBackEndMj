from django.urls import include, path
from rest_framework import routers
from academic import views

# El router genera automáticamente las rutas CRUD de la API.
router = routers.DefaultRouter()
# Endpoints principales del sistema académico.
router.register(r'teachers', views.TeacherViewSet, basename='teacher')
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'students', views.StudentViewSet, basename='student')
router.register(r'student-courses', views.StudentCourseViewSet, basename='student-course')

urlpatterns = [
	# Incluye las rutas generadas por el router bajo /api/.
    path('', include(router.urls)),
]
