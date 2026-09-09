from django.db import models


class Teacher(models.Model):
    """Docente responsable de una o varias asignaturas."""
    # Datos básicos que identifican al docente.
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Course(models.Model):
    """Asignatura académica asociada a un docente."""
    # Nombre de la asignatura y relación obligatoria con Teacher.
    name = models.CharField(max_length=150)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')

    def __str__(self):
        return self.name


class Student(models.Model):
    """Estudiante registrado en el sistema académico."""
    # Datos básicos que identifican al estudiante.
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class StudentCourse(models.Model):
    """Tabla intermedia que representa una inscripción."""
    # La combinación estudiante-asignatura identifica cada inscripción.
    pk = models.CompositePrimaryKey('student_id', 'course_id')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')