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
# TTL particulas
ttl_light = 0.7
ttl_heavy = 3.0

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
        self.particlesLight = deque()
        self.particlesLight_gpu_object = None

        self.particlesHeavy = deque()
        self.particlesHeavy_gpu_object = None



# Objeto particula
class Particle():

    def __init__(self, position, velocity, masa, ttl):

        self.position = np.array(position, dtype=np.float32)

        self.velocity = np.array(velocity, dtype = np.float32)

        self.masa = masa
        
        self.ttl = ttl

    # Cada frame se actualiza la posicion, velocidad (si tiene masa) y tu ttl
    def step(self, dt):
        # se reduce el ttl
        self.ttl -= dt

        # actualiza la pos
        self.position += self.velocity * dt

        # actualizar vel si tiene masa, si no: cte
        if self.masa == 1:
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

    ## Municion ##
    # Vertex Shd
    vert_source_ammo = """
    #version 330

    uniform float u_ttl_max;

    in vec3 position;
    in float ttl;

    vec4 colorA = vec4(0.0, 0.0, 1.0, 1.0);
    vec4 colorB = vec4(1.0, 0.0, 0.0, 1.0);

    out vec4 fragColor;

    void main()
    {
        float pct = 1.0 - (ttl / u_ttl_max);
        vec4 color = mix(colorA, colorB, pct);

        gl_PointSize = (1/u_ttl_max) * 50;
        fragColor = color;
        gl_Position = vec4(position, 1.0f);
    }
    """

    # Fragment Shd
    frag_source_ammo = """
    #version 330

    in vec4 fragColor;
    out vec4 outColor;

    void main()
    {
        outColor = fragColor;
    }
    """

    # Dos pipelines
    pipelineCannon = ShaderProgram(Shader(vert_source_cannon, "vertex"), Shader(frag_source_cannon, "fragment"))
    
    pipelineAmmo = ShaderProgram(Shader(vert_source_ammo, "vertex"), Shader(frag_source_ammo, "fragment"))

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
    # Cañon izq
    gpu_cannonIzq = pipelineCannon.vertex_list_indexed(4, GL.GL_TRIANGLES, indexIzq)
    gpu_cannonIzq.position = positionsIzq
    gpu_cannonIzq.colors = colors
    gpu_cannonIzq.intensity = intensities

    # Cañon der
    gpu_cannonDer = pipelineCannon.vertex_list_indexed(4, GL.GL_TRIANGLES, indexDer)
    gpu_cannonDer.position = positionsDer
    gpu_cannonDer.colors = colors
    gpu_cannonDer.intensity = intensities

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
        if controller.particlesLight_gpu_object is not None:
            pipelineAmmo.use()
            pipelineAmmo['u_ttl_max'] = ttl_light
            controller.particlesLight_gpu_object.draw(GL_POINTS)
        if controller.particlesHeavy_gpu_object is not None:
            pipelineAmmo.use()
            pipelineAmmo['u_ttl_max'] = ttl_heavy
            controller.particlesHeavy_gpu_object.draw(GL_POINTS)

        pipelineCannon.use()
        gpu_cannonIzq.draw(GL.GL_TRIANGLES)
        gpu_cannonDer.draw(GL.GL_TRIANGLES)



    @controller.event
    def on_key_press(symbol, modifiers):
        if symbol == key.A:
            print("Presionaste A!")
            # Generar particula Izq
            controller.particlesHeavy.append(Particle(
                np.array([-0.9,-0.9,0]),                                        # PosInicial
                np.array([np.random.uniform(0.8,1.0),np.random.uniform(0.8,1.0),0]),# VelInicial
                1,                                                              # si tiene masa o no
                ttl_heavy
            ))
        
        elif symbol == key.D:
            print('Presionaste D :(')
            # Generar particula Der
            controller.particlesLight.append(Particle(
                np.array([0.9, -0.9, 0]),
                np.array([np.random.uniform(-0.8,-1.0),np.random.uniform(0.8,1.0),0]),
                0,
                ttl_light
            ))

    # Aquí se actualiza todo el sistema de partículas
    def update_particle_system(dt, controller):

        # Sacar particulas 'no vivas'
        to_removeHeavy = 0
        to_removeLight = 0
        
        # con masa
        for i in range(len(controller.particlesHeavy)):
            p = controller.particlesHeavy[i]
            p.step(dt)
            if not p.alive():
                to_removeHeavy += 1

        for i in range(to_removeHeavy):
            controller.particlesHeavy.popleft()
        
        if controller.particlesHeavy_gpu_object is not None:
            controller.particlesHeavy_gpu_object.delete()
            controller.particlesHeavy_gpu_object = None

        # sin masa
        for i in range(len(controller.particlesLight)):
            p = controller.particlesLight[i]
            p.step(dt)
            if not p.alive():
                to_removeLight += 1

        for i in range(to_removeLight):
            controller.particlesLight.popleft()

        if controller.particlesLight_gpu_object is not None:
            controller.particlesLight_gpu_object.delete()
            controller.particlesLight_gpu_object = None

        

        # si hay partículas vivas, hay que copiarlas a la GPU
        # mnunición con masa
        if len(controller.particlesHeavy) > 0:
            controller.particlesHeavy_gpu_object = pipelineAmmo.vertex_list(
                len(controller.particlesHeavy),
                GL_POINTS
                )

            posHeavy = []
            ttlsHeavy = []
            for p in controller.particlesHeavy:
                posHeavy += p.position.tolist()
                ttlsHeavy.append(p.ttl)

            controller.particlesHeavy_gpu_object.position[:] = np.array(posHeavy, dtype=np.float32)
            controller.particlesHeavy_gpu_object.ttl[:] = np.array(ttlsHeavy, dtype=np.float32)


        # municion sin masa
        if len(controller.particlesLight) > 0:
            controller.particlesLight_gpu_object = pipelineAmmo.vertex_list(
                len(controller.particlesLight),
                GL_POINTS)
            
            posLight = []
            ttlsLight = []
            for p in controller.particlesLight:
                posLight += p.position.tolist()
                ttlsLight.append(p.ttl)

            controller.particlesLight_gpu_object.position[:] = np.array(posLight, dtype=np.float32)
            controller.particlesLight_gpu_object.ttl[:] = np.array(ttlsLight, dtype=np.float32)

    clock.schedule(update_particle_system, controller)
    run()