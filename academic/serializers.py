from rest_framework import serializers

from .models import Course, Student, StudentCourse, Teacher


# Convierte docentes en JSON y valida los datos recibidos por la API.
class TeacherSerializer(serializers.ModelSerializer):
	class Meta:
		model = Teacher
		fields = ('id', 'first_name', 'last_name')


class CourseSerializer(serializers.ModelSerializer):
	# Incluye los datos del docente en las respuestas de asignaturas.
	teacher = TeacherSerializer(read_only=True)
	# Permite enviar solo el ID del docente al crear o editar.
	teacher_id = serializers.PrimaryKeyRelatedField(
		queryset=Teacher.objects.all(), source='teacher', write_only=True
	)

	class Meta:
		model = Course
		fields = ('id', 'name', 'teacher', 'teacher_id')


# Convierte estudiantes en JSON para las operaciones del CRUD.
class StudentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Student
		fields = ('id', 'first_name', 'last_name')


class StudentCourseSerializer(serializers.ModelSerializer):
	# Serializa la inscripción y sus datos relacionados para la tabla.
	# La API usa una clave textual porque la inscripción tiene PK compuesta.
	id = serializers.SerializerMethodField()
	student = StudentSerializer(read_only=True)
	course = CourseSerializer(read_only=True)
	student_id = serializers.PrimaryKeyRelatedField(
		queryset=Student.objects.all(), source='student', write_only=True
	)
	course_id = serializers.PrimaryKeyRelatedField(
		queryset=Course.objects.all(), source='course', write_only=True
	)

	class Meta:
		model = StudentCourse
		fields = ('id', 'student_id', 'course_id', 'student', 'course')

	def get_id(self, instance):
		# Formato usado por la interfaz: "id_estudiante-id_asignatura".
		return f'{instance.student_id}-{instance.course_id}'