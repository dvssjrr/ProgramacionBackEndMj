from django.urls import path

from . import views


urlpatterns = [
    # La raíz muestra directamente el CRUD de asignaturas.
    path('', views.courses_page, name='home'),
    # Páginas HTML del sistema académico.
    path('courses/', views.courses_page, name='academic_courses'),
    path('students/', views.students_page, name='academic_students'),
    path('teachers/', views.teachers_page, name='academic_teachers'),
    path('enrollments/', views.enrollments_page, name='academic_enrollments'),
    path('<path:unmatched_path>/', views.page_not_found, name='page_not_found'),
]