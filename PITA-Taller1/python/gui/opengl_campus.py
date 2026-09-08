from math import sin

from PySide6.QtCore import QTimer
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_MODELVIEW,
    GL_PROJECTION,
    GL_QUADS,
    GL_TRIANGLES,
    glBegin,
    glClear,
    glClearColor,
    glColor3f,
    glEnable,
    glEnd,
    glLoadIdentity,
    glMatrixMode,
    glPopMatrix,
    glPushMatrix,
    glRotatef,
    glTranslatef,
    glVertex3f,
    glViewport,
)


class CampusOpenGLWidget(QOpenGLWidget):
    """Escena 3D ligera y tolerante para el dashboard PITA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self._ready = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(40)

    @staticmethod
    def configure_format():
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setRenderableType(QSurfaceFormat.OpenGL)
        fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

    def initializeGL(self):
        try:
            glClearColor(0.027, 0.067, 0.12, 1.0)
            glEnable(GL_DEPTH_TEST)
            self._ready = True
        except Exception:
            self._ready = False

    def resizeGL(self, width, height):
        glViewport(0, 0, max(width, 1), max(height, 1))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = width / max(height, 1)
        if aspect >= 1:
            self._ortho(-aspect * 5, aspect * 5, -5, 5, -20, 20)
        else:
            self._ortho(-5, 5, -5 / aspect, 5 / aspect, -20, 20)
        glMatrixMode(GL_MODELVIEW)

    def _ortho(self, left, right, bottom, top, near, far):
        # Matriz ortografica suficiente para una escena estilizada sin shaders.
        glLoadIdentity()
        from OpenGL.GL import glOrtho
        glOrtho(left, right, bottom, top, near, far)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if not self._ready:
            return
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0.0, -0.5, -7.0)
        glRotatef(18.0, 1.0, 0.0, 0.0)
        glRotatef(self._angle, 0.0, 1.0, 0.0)
        self._draw_ground()
        self._draw_building(-2.6, 0.2, 1.2, 1.7, 1.8, (0.12, 0.45, 0.75))
        self._draw_building(0.0, 0.3, 1.6, 2.0, 2.5, (0.48, 0.25, 0.72))
        self._draw_building(2.5, 0.15, 1.0, 1.5, 1.3, (0.15, 0.65, 0.52))
        for x, z in [(-3.8, -1.8), (3.7, -1.4), (-3.5, 2.0), (3.4, 2.1)]:
            self._draw_tree(x, z)

    def _draw_ground(self):
        glColor3f(0.08, 0.25, 0.22)
        glBegin(GL_QUADS)
        glVertex3f(-6, 0, -4); glVertex3f(6, 0, -4); glVertex3f(6, 0, 4); glVertex3f(-6, 0, 4)
        glEnd()
        glColor3f(0.18, 0.22, 0.28)
        glBegin(GL_QUADS)
        glVertex3f(-0.35, 0.02, -4); glVertex3f(0.35, 0.02, -4); glVertex3f(0.35, 0.02, 4); glVertex3f(-0.35, 0.02, 4)
        glEnd()

    def _draw_building(self, x, y, width, depth, height, color):
        glPushMatrix()
        glTranslatef(x, y + height / 2, 0.3)
        glColor3f(*color)
        vertices = [(-width, -height / 2, -depth), (width, -height / 2, -depth), (width, height / 2, -depth), (-width, height / 2, -depth),
                    (-width, -height / 2, depth), (width, -height / 2, depth), (width, height / 2, depth), (-width, height / 2, depth)]
        faces = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 4, 7, 3), (1, 5, 6, 2), (3, 2, 6, 7), (0, 1, 5, 4))
        glBegin(GL_QUADS)
        for face in faces:
            for index in face:
                glVertex3f(*vertices[index])
        glEnd()
        glPopMatrix()

    def _draw_tree(self, x, z):
        glPushMatrix()
        glTranslatef(x, 0.35, z)
        glColor3f(0.35, 0.18, 0.08)
        glBegin(GL_QUADS)
        glVertex3f(-0.08, 0, -0.08); glVertex3f(0.08, 0, -0.08); glVertex3f(0.08, 0.7, -0.08); glVertex3f(-0.08, 0.7, -0.08)
        glEnd()
        glColor3f(0.15, 0.55, 0.32)
        glBegin(GL_TRIANGLES)
        for offset in (0.0, 0.35):
            glVertex3f(0, 1.5 + offset, 0); glVertex3f(-0.55, 0.5 + offset, 0); glVertex3f(0.55, 0.5 + offset, 0)
        glEnd()
        glPopMatrix()

    def _animate(self):
        self._angle = (self._angle + 0.25) % 360
        self.update()
