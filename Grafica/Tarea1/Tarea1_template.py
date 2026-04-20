# LIBRERIAS externas
import pyglet
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.window import Window, key
from pyglet.gl import *
from pyglet.app import run
from pyglet import clock

from OpenGL import GL

import sys, os
import numpy as np
# la siguiente linea le dice a python que cuando busque librerías, busque en la carpeta actual
sys.path.append(os.path.dirname(os.path.dirname((os.path.dirname(__file__)))))

# Revise lo que es un queue, le será útil para entender por qué es conveniente usarlo
# https://en.wikipedia.org/wiki/Queue_(abstract_data_type)
from collections import deque

## Variables Globales ##
#  acel de gravedad
G = -1
# tiempo
TIME = 0


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
    ## Cañones ##
    # Vertex Shd
    vert_source_cannon = """
    #version 330

    in vec3 position;
    in vec3 colors;
    in float intensity;
    in float ttl;

    out vec3 fragColor;
    out float fragIntensity;
    out float alpha;

    void main()
    {
        alpha = 1.0;
        gl_PointSize = 15.0 * (ttl / 3.0);
        fragColor = colors;
        fragIntensity = intensity;
        gl_Position = vec4(position, 1.0f);
    }
    """

    # Fragment Shd
    frag_source_cannon = """
    #version 330

    in vec3 fragColor;
    in float fragIntensity;
    in float alpha;

    out vec4 outColor;

    void main()
    {
        outColor = fragIntensity * vec4(fragColor, alpha);
    }
    """

    # Dos pipelines
    pipelineIzq = ShaderProgram(Shader(vert_source_cannon, "vertex"), Shader(frag_source_cannon, "fragment"))
    
    pipelineDer = ShaderProgram(Shader(vert_source_cannon, "vertex"), Shader(frag_source_cannon, "fragment"))

    ### Definiciones de Figuras ###
    # Vertices
    # Cañon Izquierdo
    positionsIzq = np.array([
        -1, -1, 0,
        -1, -0.8, 0,
        -0.8, -0.8, 0,
        -0.8, -1, 0
    ], dtype = np.float32)
    # Cañon derecho
    positionsDer = np.array([
        1, -1, 0,
        0.8, -1, 0,
        0.8, -0.8, 0,
        1, -0.8 ,0
    ], dtype= np.float32)


    # Indices
    indexIzq = np.array([
        0, 1, 2,
        2, 3, 0
    ], dtype = np.uint32)

    indexDer = np.array([
        0, 1, 2,
        2, 3, 0
    ], dtype = np.uint32)

    # Colores
    colors = np.array([
        1,1,1,
        1,1,1,
        1,1,1,
        1,1,1
    ], dtype = np.float32)

    # Intensidad vértices
    intensities = np.array([
        1,
        1,
        1,
        1
    ], dtype = np.float32)

    # Definicion de las figuras
    # Cañones
    gpu_cannonIzq = pipelineIzq.vertex_list_indexed(4, GL.GL_TRIANGLES, indexIzq)
    gpu_cannonIzq.position = positionsIzq
    gpu_cannonIzq.colors = colors
    gpu_cannonIzq.intensity = intensities

    gpu_cannonDer = pipelineDer.vertex_list_indexed(4, GL.GL_TRIANGLES, indexDer)
    gpu_cannonDer.position = positionsDer
    gpu_cannonDer.colors = colors
    gpu_cannonDer.intensity = intensities

    # Municion
    

    @controller.event
    def on_draw():
        # Limpia pantalla y la coloca en el color determinado (no la modifico)
        glClearColor(0.8,0.9,1,1)
        controller.clear()

        # Flags de OpenGL para dibujar puntos y usar transparencia
        glEnable(GL_PROGRAM_POINT_SIZE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        

        # Seleccionar pipeline y dibujar
        pipelineIzq.use()
        gpu_cannonIzq.draw(GL.GL_TRIANGLES)

        pipelineDer.use()
        gpu_cannonDer.draw(GL.GL_TRIANGLES)

        if controller.particles_gpu_object is not None:
            controller.particles_gpu_object.draw(GL_POINTS)


    @controller.event
    def on_key_press(symbol, modifiers):
        if symbol == key.A:
            print("Presionaste A!")
            # Generar particula Izq
            controller.particles.append(Particle(
                np.array([-0.9,-0.9,0]),                                        # PosInicial
                np.array([0.1,0.1,0]),                                          # VelInicial
                1.0                                                             # TTL
            ))
        
        elif symbol == key.D:
            print('Presionaste D :(')
            # Generar particula Der
            controller.particles.append(Particle(
                np.array([0.9, -0.9, 0]),
                np.array([-0.1,0.1,0]),
                1.0
            ))

    # Aquí se actualiza todo el sistema de partículas
    def update_particle_system(dt, controller):

        # Sacar particulas no 'vivas'
        to_remove = 0
        for i in range(len(controller.particles)):
            p = controller.particles[i]
            p.step(dt)
            if not p.alive():
                to_remove += 1

        for i in range(to_remove):
            controller.particles.popleft()

        if controller.particles_gpu_object is not None:
            controller.particles_gpu_object.delete()
            controller.particles_gpu_object = None

        # si hay partículas vivas, hay que copiarlas a la GPU
        if len(controller.particles) > 0:
            controller.particles_gpu_object = pipelineIzq.vertex_list(
                len(controller.particles),
                GL_POINTS
                )
            
            pos = []
            ttls = []
            for p in controller.particles:
                pos += p.position.tolist()
                ttls.append(p.ttl)

            controller.particles_gpu_object.position[:] = np.array(pos)
            controller.particles_gpu_object.ttl[:] = np.array(ttls)
            
        pos = []
        ttls = []        

    clock.schedule(update_particle_system, controller)
    run()