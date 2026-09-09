from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets

from .models import Course, Student, StudentCourse, Teacher
from .serializers import (
	CourseSerializer, StudentCourseSerializer, StudentSerializer, TeacherSerializer,
)


# Configuración que permite reutilizar una sola plantilla para los cuatro CRUD.
CRUD_PAGES = {
	'teachers': {
		'title': 'Docentes',
		'endpoint': 'teachers',
		'columns': [('id', 'ID'), ('first_name', 'Nombre'), ('last_name', 'Apellido')],
		'fields': [
			{'name': 'first_name', 'label': 'Nombre', 'type': 'text'},
			{'name': 'last_name', 'label': 'Apellido', 'type': 'text'},
		],
	},
	'courses': {
		'title': 'Asignaturas',
		'endpoint': 'courses',
		'columns': [('id', 'ID'), ('name', 'Asignatura'), ('teacher', 'Docente')],
		'fields': [
			{'name': 'name', 'label': 'Nombre de la asignatura', 'type': 'text'},
			{'name': 'teacher_id', 'label': 'Docente', 'type': 'select', 'source': 'teachers'},
		],
	},
	'students': {
		'title': 'Estudiantes',
		'endpoint': 'students',
		'columns': [('id', 'ID'), ('first_name', 'Nombre'), ('last_name', 'Apellido')],
		'fields': [
			{'name': 'first_name', 'label': 'Nombre', 'type': 'text'},
			{'name': 'last_name', 'label': 'Apellido', 'type': 'text'},
		],
	},
	'enrollments': {
		'title': 'Inscripciones',
		'endpoint': 'student-courses',
		'columns': [('student', 'Estudiante'), ('course', 'Asignatura')],
		'fields': [
			{'name': 'student_id', 'label': 'Estudiante', 'type': 'select', 'source': 'students'},
			{'name': 'course_id', 'label': 'Asignatura', 'type': 'select', 'source': 'courses'},
		],
	},
}


def courses_page(request):
	# Abre el CRUD de asignaturas.
	return crud_page(request, 'courses', 'academic/courses.html')


def students_page(request):
	# Abre el CRUD de estudiantes.
	return crud_page(request, 'students', 'academic/students.html')


def teachers_page(request):
	# Abre el CRUD de docentes.
	return crud_page(request, 'teachers')


def enrollments_page(request):
	# Abre el CRUD de inscripciones.
	return crud_page(request, 'enrollments')


def crud_page(request, entity, template='academic/crud.html'):
	# Envía a la plantilla el título, endpoint y campos del módulo elegido.
	return render(request, template, {'page_config': CRUD_PAGES[entity]})


def page_not_found(request, exception=None, unmatched_path=None):
	# Muestra una respuesta amigable cuando la URL no existe.
	return render(request, '404.html', status=404)


class TeacherViewSet(viewsets.ModelViewSet):
	# ModelViewSet proporciona listar, crear, consultar, editar y eliminar.
	queryset = Teacher.objects.all().order_by('last_name', 'first_name')
	serializer_class = TeacherSerializer


class CourseViewSet(viewsets.ModelViewSet):
	# select_related obtiene el docente junto con cada asignatura.
	queryset = Course.objects.select_related('teacher').all().order_by('name')
	serializer_class = CourseSerializer


class StudentViewSet(viewsets.ModelViewSet):
	# CRUD REST para los estudiantes ordenados alfabéticamente.
	queryset = Student.objects.all().order_by('last_name', 'first_name')
	serializer_class = StudentSerializer


class StudentCourseViewSet(viewsets.ModelViewSet):
	# CRUD REST para la tabla intermedia de inscripciones.
	queryset = StudentCourse.objects.select_related('student', 'course').all()
	serializer_class = StudentCourseSerializer

	def get_object(self):
		# DRF recibe la PK compuesta como "student_id-course_id" en la URL.
		student_id, course_id = self.kwargs['pk'].split('-', 1)
		return get_object_or_404(self.get_queryset(), student_id=student_id, course_id=course_id)
