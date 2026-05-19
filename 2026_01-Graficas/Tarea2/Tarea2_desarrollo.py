#LIBRERIAS
from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.window import Window, key
from pyglet.gl import *
from pyglet.app import run
from pyglet import math
from pyglet import clock

import sys, os
import numpy as np

#MODULOS (cuidado con las rutas)
sys.path.append(os.path.dirname(os.path.dirname((os.path.dirname(__file__)))))
from utils.helpers import init_axis, mesh_from_file
from utils.camera import FreeCamera
from utils.scene_graph import SceneGraph
from utils import shapes
from utils.drawables import Texture, Model

#Controla la ventana
class Controller(Window):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.time = 0
        self.light_mode = False


#CAMARA definida en una clase
# class MyCam(OrbitCamera):
class MyCam(FreeCamera):
    def __init__(self, position=np.array([0, 0, 0]), camera_type='perspective'):
        super().__init__(position, camera_type)
        self.direction = np.array([0,0,0])
        self.speed = 2

    def time_update(self, dt):
        self.update()
        dir = self.direction[0]*self.forward + self.direction[1]*self.right
        dir_norm = np.linalg.norm(dir)
        if dir_norm:
            dir /= dir_norm
        self.position += dir*self.speed*dt
        self.focus = self.position + self.forward

class Personaje:
    def __init__(self, position, velocity):
        self.pos = np.array(position, dtype=np.float32)
        self.vel = np.array(velocity, dtype=np.float32)

#funcion para tener coordenadas uv a partir de pos en img
# indicar izq inferior, asume sectores de 16x16 pixeles
def get_atlas_uv(xOffset, yOffset, atlas):
    size = 16
    deltaX = size / atlas.width                                                 # porcentaje del ancho total
    deltaY = size / atlas.height

    res = [
        deltaX * xOffset,       deltaY * yOffset,
        deltaX * (xOffset+1),   deltaY * yOffset,
        deltaX * (xOffset+1),   deltaY * (yOffset+1),
        deltaX * xOffset,       deltaY * (yOffset+1)
    ]

    return res


if __name__ == "__main__":

    controller = Controller(800,600,"Tarea 2")
    controller.set_exclusive_mouse(True)

# Cambio de color a textura
    vert_source = """
#version 330

in vec3 position;
in vec2 texCoord; 

out vec2 fragTexCoord; 

uniform mat4 u_model = mat4(1.0);
uniform mat4 u_view = mat4(1.0);
uniform mat4 u_projection = mat4(1.0);

void main() {
    fragTexCoord = texCoord;
    gl_Position = u_projection * u_view * u_model * vec4(position, 1.0f);
}
    """
    frag_source = """
#version 330
in vec2 fragTexCoord;

uniform sampler2D u_texture;

out vec4 outColor;

void main() {
    outColor = texture(u_texture, fragTexCoord);
}
    """

# parte A
    pipeline = ShaderProgram(Shader(vert_source, "vertex"), Shader(frag_source, "fragment"))
    root = os.path.dirname(__file__)

    # Movimiento/ camara
    posIni = np.array([0.0, 0.0, 0.0])
    velIni = np.array([0.0, 0.0, 0.0])
    prota = Personaje(posIni, velIni)                                           # pos inicial: Origen, vel ini: Reposo

    cam_z = 0.2                                                                 # distancia inicial de la camara
    zoom =  0.1                                                                 # esto se le modificara a z de cam

    cam = MyCam([0,0,cam_z])                                                    # camara inicia en z=1

    world = SceneGraph(cam)                                                     # inicio grafo con camara anterior

    # importado de texturas
    atlas = Texture(root + "/imgs/TileSet.png",sWrapMode=GL_REPEAT, tWrapMode=GL_REPEAT, minFilterMode=GL_NEAREST, maxFilterMode=GL_NEAREST)    # nearest para evitar bordes borrosos
    Fondo = Texture(root + '/imgs/fondo1.png',sWrapMode=GL_REPEAT, tWrapMode=GL_REPEAT, minFilterMode=GL_NEAREST, maxFilterMode=GL_NEAREST)
    
    # Definicion de UVs

    ##UVs 'manuales'
    uv_fondo = [
        0.0, 0.0,
        20.0, 0.0,
        20.0, 10.0,
        0.0, 10.0
    ]
    
    uv_head = [
        0.655, 0.0,
        0.790, 0.0,
        0.790, 0.201,
        0.655, 0.201
    ]
    uv_torso = [
        0.790,  0.0,
        1.0,    0.0,
        1.0,    0.201,
        0.790,  0.201
    ]

    ## uso de get_atlas_uv para texturas en Tileset
    uv_roof = [*get_atlas_uv(7, 4, atlas)]

    uv_platfm_bot = [*get_atlas_uv(2,11, atlas)]
    uv_platfm_izq = [*get_atlas_uv(13,8, atlas)]
    uv_platfm_der = [*get_atlas_uv(7,3, atlas)]

    uv_front = [*get_atlas_uv(7,6,atlas)]
    
    # Instanciacion cuadrados
    ## fondo
    square_fondo = Model(shapes.Square["position"],uv_fondo, index_data=shapes.Square["indices"])

    ## personaje
    square_head = Model(shapes.Square["position"], uv_head, index_data=shapes.Square["indices"])
    square_torso = Model(shapes.Square["position"], uv_torso, index_data=shapes.Square["indices"])

    ## techo
    square_roof = Model(shapes.Square['position'], uv_roof, index_data=shapes.Square['indices'])
    
    ## plataformas: 3 sub-secciones
    square_platf_bot = Model(shapes.Square['position'], uv_platfm_bot, index_data=shapes.Square['indices']) # inferior
    square_platf_izq = Model(shapes.Square['position'], uv_platfm_izq, index_data=shapes.Square['indices']) # izquierda
    square_platf_der = Model(shapes.Square['position'], uv_platfm_der, index_data=shapes.Square['indices']) # derecha

    ## front
    square_front = Model(shapes.Square['position'], uv_front, index_data=shapes.Square['indices'])


    ### Grafo ###
    #definir profundidades para cada nivel
    z_fondo=-1.0
    z_pj=   z_fondo + 0.2
    z_med=  z_pj + 0.2
    z_near= z_med + 0.2

    # Campo Lejano
    world.add_node('Campo Lejano')
    ## Fondo
    world.add_node('fondo',
        attach_to=  'Campo Lejano',
        mesh=       square_fondo,
        pipeline=   pipeline,
        texture=    Fondo,
        position=   [0.0, 0.0, z_fondo],
        scale=      [5.0, 2.5, 0.0])

    # Campo Personaje
    world.add_node('Campo PJ')
    world.add_node('pj',
        attach_to=  'Campo PJ',
        position=   [0.0,0.0,z_pj],
        scale=      [0.1,0.1,0.0])

    world.add_node("head",
        attach_to=  'pj',
        mesh=       square_head,
        pipeline=   pipeline,
        texture=    atlas,
        position=   [0.0, 0.45, 0.0])
    world.add_node('torso',
        attach_to=  'pj',
        mesh=       square_torso,
        pipeline=   pipeline,
        texture=    atlas,
        position=   [0.0, -0.45, 0.0])


    #Campo medio: roof y plataformas
    world.add_node('Campo Medio',
        position=[0.0, 0.0, z_med])

    ## techo
    world.add_node('roof',
        attach_to=  'Campo Medio')

    for x in range (-15,15, 1):
        name = f'roof_{x}'                                                      #cada nodo es un cuadrado del techo
        world.add_node(name,
            attach_to=  'roof',
            mesh =      square_roof,
            pipeline=   pipeline,
            texture=    atlas,
            position=   [x*0.1, 0.8, 0.0],
            scale=      [0.1, 0.35, 0])

    ## Plataformas
    world.add_node('plataforma',
        attach_to='Campo Medio')

    ### plataforma izq
    world.add_node('izq',
        attach_to=  'plataforma',
        position=   [-0.5, 0.0, 0.0])

    for x in range(-3, 3, 1):                                                   # se usa la misma lógica que en roof
        name = f'izq_{x}'
        world.add_node(name,
            attach_to=  'izq',
            mesh=       square_platf_izq,
            pipeline=   pipeline,
            texture=    atlas,
            position=   [x*0.1, 0.0, 0.0],
            scale=      [0.1,0.1,0]
            )

    ### platform der
    world.add_node('der',
        attach_to=  'plataforma',
        position=   [1.5, 0.25, 0.0])

    for x in range(-3, 3, 1):
        name = f'der_{x}'
        world.add_node(name,
            attach_to=  'der',
            mesh=       square_platf_der,
            pipeline=   pipeline,
            texture=    atlas,
            position=   [x*0.1, 0.0, 0.0],
            scale=      [0.1,0.1,0.0])

    ### platform bottom
    world.add_node('bottom',
        attach_to=  'plataforma',
        position=   [0.2, -0.5, 0.0])

    for x in range(-5, 5, 1):
        name = f'bot_{x}'
        world.add_node(name,
            attach_to=  'bottom',
            mesh=       square_platf_bot,
            pipeline=   pipeline,
            texture=    atlas,
            position=   [x*0.1, 0.0, 0.0],
            scale=      [0.1,0.1,0.0])

    # Campo cercano
    world.add_node('Campo Near',
        position=   [0.0, 0.0, z_near])

    world.add_node('Plants',
        attach_to=  'Campo Near')
    
    for x in range(-3, 3, 1):
        name = f'plant_{x}'
        world.add_node(name,
            attach_to=  'Plants',
            mesh=       square_front,
            pipeline=   pipeline,
            texture=    atlas,
            position=   [x*0.5, -0.4, 0.0],
            scale=      [0.25, 0.5, 0.0])


    @controller.event
    def on_draw():
        controller.clear()
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        world.draw()
        

    #CAMARA vista en aux5
    @controller.event
    def on_key_press(symbol, modifiers):
        global cam_z

        # W,S modifican pos en z de cam
        if symbol == key.W:
            cam_z -= zoom
        if symbol == key.S:
            cam_z += zoom

        # A,S cambian la direccion de mov del pj
        if symbol == key.A:
            prota.vel[0] = -1
        if symbol == key.D:
            prota.vel[0] = +1

        # salto con space
        if symbol == key.SPACE:
            if (prota.pos[1] == 0.0):                                           # impulso solo una vez (cuando esta en medio)
                    prota.vel[1] = 2.5

    @controller.event
    def on_key_release(symbol, modifiers):
        # soltar las teclas devuelve al reposo al pj
        if (symbol==key.A or symbol==key.D):
            prota.vel[0] = 0

    #Informacion que se actualiza con el tiempo
    def update(dt):
        global cam_z

        world.update()
        cam.time_update(dt)

        # Bonus: agregar salto
        if (prota.pos[1] > 0.0):                                                #vuelve solo si esta sobre horizonte
            prota.vel[1] += -5.0*dt

        if (prota.pos[1] < 0):                                                  #al volver, se reinicia su pos y vel
            prota.pos[1] = 0.0
            prota.vel[1] = 0.0

        prota.pos += prota.vel * dt                                             #actualizacion usual de cinematica

        # se entrega cambio a instancia de pj
        world['pj']['position'][0] = prota.pos[0]
        world['pj']['position'][1] = prota.pos[1]

        # actualizar pos de cam, solo seguir en eje X
        cam.position = [prota.pos[0], 0.0, cam_z]

        c_pos = cam.position.copy()
        c_pos[1] = 0

        controller.time += dt

    clock.schedule_interval(update,1/60)
    run()