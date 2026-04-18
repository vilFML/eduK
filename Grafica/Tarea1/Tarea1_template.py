# LIBRERIAS externas
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.window import Window, key
from pyglet.gl import *
from pyglet.app import run
from pyglet import clock

import sys, os
import numpy as np
# la siguiente linea le dice a python que cuando busque librerías, busque en la carpeta actual
sys.path.append(os.path.dirname(os.path.dirname((os.path.dirname(__file__)))))

# Revise lo que es un queue, le será útil para entender por qué es conveniente usarlo
# https://en.wikipedia.org/wiki/Queue_(abstract_data_type)
from collections import deque

# Global: acel de gravedad
G = -1

# Controla la ventana y el paso del tiempo
class Controller(Window):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        ### Variables globales ###
        # Tamaño ventana
        self.width = 600
        self.height = 600

        # Inicio de ventana temporal
        self.time = 0

        # aplicando el 'deque' para las particulas
        self.particles = deque()
        self.particles_gpu_object = None



# Se define el objeto particula
class Particle():

    # ¿Qué debe otros parámetros son necesarios para crear una partícula?
    def __init__(self, position, velocity, ttl):
        self.position = np.array(position, dtype=np.float32)

        #voy a usar vel cte por mientras
        self.velocity = np.array( [np.random.uniform(-1,1),
                                    np.random.uniform(-1,1),
                                    0], dtype = np.float32 )
        
        self.ttl = ttl

    # ¿Qué se debe actualizar en cada frame?
    def step(self, dt):
        # por un lado se reduce el tiempo de vida de la partícula
        self.ttl -= dt

        # se actualiza la posición de la partícula
        self.position += self.velocity * dt

        self.velocity[1] = self.velocity[1] + G * dt

    # Funcion que entrega si particula esta viva
    def alive(self):
        return bool(self.ttl > 0)

if __name__ == "__main__":

    controller = Controller(800, 800, "Tarea_1")

    vert_source = """
    #version 330

    in vec3 position;
    in float ttl;
    out float alpha;

    void main()
    {
        gl_PointSize = 15.0 * (ttl / 3.0);
        gl_Position = vec4(position, 1.0);
        alpha = ttl / 3.0;
    }
    """
    frag_source = """
    #version 330

    in float alpha;
    out vec4 outColor;

    void main()
    {
        outColor = vec4(1.0, 1.0, 1.0, alpha);
    }
    """

    # Dos pipelines
    pipelineIzq = pyglet.graphics.shader.ShaderProgram(vert_source, frag_source)

    pipelineDer = pyglet.graphics.shader.ShaderProgram(vert_source, frag_source)

    # Defina las figuras para los cañones
    

    @controller.event
    def on_draw():
        # Limpia pantalla y la coloca en el color determinado
        glClearColor(0.8,0.9,1,1)
        controller.clear()

        # Flags de OpenGL para dibujar puntos y usar transparencia
        glEnable(GL_PROGRAM_POINT_SIZE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        

        # Aquí debe selecicionar el pipeline que usara y luego dibujar sus cosas...




    # Esta función es importante, ya que le ayudará a interactuar con el teclado.
    # Actualmente, está programada para que cada vez que se presione "A", 
    # se imprima "Presionaste A!"
    @controller.event
    def on_key_press(symbol, modifiers):
        if symbol == key.A:
            print("Presionaste A!")

        # Use esta función de Pyglet para generar sus partículas.




    # Aquí se actualiza todo el sistema de partículas
    def update_particle_system(dt, controller):

        # Estudie el aux 3 para entender bien este paso.
        controller.particles_gpu_object = pipeline.vertex_list( len(controller.particles), GL_POINTS )
            
        pos = []
        ttls = []
        for p in controller.particles:
            pos += p.position.tolist()
            ttls.append(p.ttl)

        controller.particles_gpu_object.position[:] = np.array(pos)
        controller.particles_gpu_object.ttl[:] = np.array(ttls)

        

    clock.schedule(update_particle_system, controller)
    run()