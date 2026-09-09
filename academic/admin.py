from django.contrib import admin

from .models import Course, Student, Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    # Columnas y búsqueda disponibles en el panel de administración.
    list_display = ('id', 'first_name', 'last_name')
    search_fields = ('first_name', 'last_name')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    # Permite administrar asignaturas junto con su docente responsable.
    list_display = ('id', 'name', 'teacher')
    search_fields = ('name', 'teacher__first_name', 'teacher__last_name')
    list_select_related = ('teacher',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    # Permite buscar y administrar estudiantes desde Django Admin.
    list_display = ('id', 'first_name', 'last_name')
    search_fields = ('first_name', 'last_name')
