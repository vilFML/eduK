#--------------------------------Librerias-------------------------------------#

from pyglet.graphics.shader import Shader, ShaderProgram
from pyglet.window import Window, key
from pyglet.gl import *
from pyglet.app import run
from pyglet import math
from pyglet import clock
import sys, os
import numpy as np
import trimesh as tm

sys.path.append(os.path.dirname(os.path.dirname((os.path.dirname(__file__)))))
from utils.helpers import init_axis, init_pipeline
from utils.camera import FreeCamera
from utils.scene_graph import SceneGraph
from utils.drawables import Model, DirectionalLight, Material

from collections import deque

#--------------------------------Constantes-------------------------------------#

G = np.array([0.0, -9.8, 0.0], dtype=np.float32)                                #Y>0 es hacia arriba
RADIO_PELOTAS = 0.2                                                             # radio visual de la esfera en escena

MATERIALES = [                                                                  #array almacena materiales y props
    #Material, bounciness, propVisuales
    ('Madera', 0.25, Material(
        ambient=[0.6, 0.3, 0.1],
        diffuse=[0.6, 0.3, 0.1],
        specular=[0.1, 0.1, 0.1],
        shininess=2.0
    )),
    ('Goma', 0.75, Material(
        ambient=[0.1, 0.8, 0.1],
        diffuse=[0.1, 0.8, 0.1],
        specular=[0.8, 0.8, 0.8],
        shininess=32.0
    ))
]

#--------------------------------Clases Sistema---------------------------------#

class Controller(Window):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.time = 0
        self.sky_color = np.array([0.2, 0.3, 0.5])
        self.intensity = 0.1
        self.wireframe = False

        self.pelotas = deque()                                                  #pelotas que ya estan cayendo
        self.cant_pelotas = 0                                                   #contador de pelotas
        self.spawnPos_index = 1                                                 #para alternar pos de spawn
        self.material_index = 0                                                 #indice para material seleccionado

class MyCam(FreeCamera):
    def __init__(self, position=np.array([0, 0, 0]), camera_type="perspective"):
        super().__init__(position, camera_type)
        self.direction = np.zeros(3)
        self.speed = 0                                                          #camara fija

    def time_update(self, dt):
        self.update()
        self.focus = self.position + self.forward

#----------------------------------Clases Propias---------------------------------------#
#Pelota bajo gravedad, rebota con plataforma
class Pelota:
    def __init__(self, node_name, pos, restitution, ttl=5.0):
        self.node_name = node_name                                              #nombre en nodo de grafo
        self.ttl = ttl #[s]

        #prop geom
        self.restitution = restitution                                          #depende de material: [0,1]
        self.radio = RADIO_PELOTAS


        #cinematica
        self.pos = np.array(pos, dtype=np.float32)
        self.vel = np.zeros(3, dtype=np.float32)                                # pelota 'flotando' inicialmente
        self.is_dropped = False                                                 #flota hasta apretar espacio

    #para actualizar cinematica
    def step(self, dt, plane_point, plane_normal):
        if not self.is_dropped:                                                 #si aun no se suelta, hacer nada
            return
                
        #cinematica
        self.vel += G*dt
        self.pos += self.vel*dt

        self.ttl -= dt

        #colision con plataforma
        d = np.dot(self.pos - plane_point, plane_normal)                        #dist centro-plano
        if d<self.radio:                                                        #contacto con platfm
            self.pos += plane_normal*(self.radio-d)                             #rebote

            vn = np.dot(self.vel, plane_normal)                                 #componente normal de vel

            if vn<0:
                self.vel -= (1+self.restitution) * vn * plane_normal            #reflejar con restitucion en direccion respectiva

    #fn activa caida
    def drop(self):
        self.is_dropped = True

    #fn ver si pelota esta viva
    def alive(self):
        return bool(self.ttl>0)



#----------------------------------Funciones---------------------------------------#
#fn crea pelota flotante en pos de spawn actual y la retorna
def make_floating_ball():
    pos = spawn_positions[controller.spawnPos_index].copy()
    mat_name, restitution, mat = MATERIALES[controller.material_index]          #se crea con material asignado
    name = "pelota_" + str(controller.cant_pelotas)

    world.add_node(
        name,
        attach_to='Pelotas',
        mesh=mesh_ball,
        pipeline=flat_pipeline,
        mode=GL_TRIANGLES,
        position=list(pos),
        scale=[RADIO_PELOTAS, RADIO_PELOTAS, RADIO_PELOTAS],
        material=mat,
        )
    pelota = Pelota(node_name=name, pos=pos, restitution=restitution)
    controller.cant_pelotas += 1
    return pelota

#fn para tener centro de plano y normal del nodo
def get_platform_transform(world):
    node = world['Plataforma']
    center = np.array(node.get('position', [0,0,0]), dtype=np.float32)          # pos del centro de platfm en escena

    theta = np.radians(30)                                                      #rotacion c/r eje X en 30°
    c, s = np.cos(theta), np.sin(theta)                                         #para simplificar notacion
    
    # Rotacion de matriz en X
    R = np.array([
        [1, 0, 0],
        [0, c, -s],
        [0, s, c]
    ])
    #normal local (0,1,0) rotada a escena
    local_normal = np.array([0.0, 1.0, 0.0])
    world_normal = R @ local_normal
    world_normal = world_normal / np.linalg.norm(world_normal)

    return center, world_normal


#--------------------------------Principal--------------------------------------#
if __name__ == "__main__":
    #ventana
    controller = Controller(1000,1000,"Auxiliar 8")
    controller.set_exclusive_mouse(True)

    root = os.path.dirname(__file__)
    flat_pipeline = init_pipeline(root + "/flat.vert", root + "/flat.frag")     #pipeline

    cam = MyCam([0,1,0])                                                        #camara
    axis = init_axis(cam)                                                       #axis para mayor claridad
    world = SceneGraph(cam)                                                     #inicio de escena

    #--------------------------------Mallas-------------------------------------#
    #Creacion de plataforma
    n = 50
    vertices, normals = [], []
    for i in range(n):                                                          #generar vertices y normales
        for j in range(n):
            vertices += [j, 0, i]
            normals += [0, 1, 0]
    indices = []                                                                #generar indices: dos triangulos por cuadrado
    for i in range(n-1):
        for j in range(n-1):
            indices += [n*(i+1) + j + 1, n*i + j + 1, n * i + j]
            indices += [n*(i+1) + j, n*(i+1) + j + 1, n * i + j]
    #generar ruidos
    for i in range(n*n*2):
        vertices[np.random.randint(0, n*n) * 3 + 1] += 1
    for i in range(n*n):
        vertices[np.random.randint(0, n*n) * 3 + 1] += 2
    
    # Creamos un trimesh object con la geometria
    tri = tm.Trimesh(vertices=np.array(vertices).reshape(len(vertices)//3, 3), faces=np.array(indices).reshape(len(indices)//3, 3), process=False)
    betterNormals = np.array(tm.smoothing.get_vertices_normals(tri)).flatten()  # sacar normales    
    tri = tm.smoothing.filter_humphrey(tri)                                     # Filtro para el ruido
    verticesT = np.array(tri.vertices, dtype=np.float32).flatten()              #extraer elementos
    facesT = np.array(tri.faces, dtype=np.float32).flatten()
    normalT = np.array(tri.vertex_normals, dtype=np.float32).flatten()
    uvs = []
    for i in range(n):
        for j in range(n):
            uvs += [0.0, 0.0]             
    mesh_Plat = Model(verticesT, normal_data=normalT, index_data=facesT, uv_data=uvs)   #malla de plataforma


    #Esfera desde .obj
    sphere_tm = tm.load(root+"/assets/sphere.obj")
    #almacenar vertices, caras y vectores normales de malla de esfera (vienen en .obj)
    sphere_verts = np.array(sphere_tm.vertices, dtype=np.float32).flatten()
    sphere_faces = np.array(sphere_tm.faces, dtype=np.float32).flatten()
    sphere_normals = np.array(sphere_tm.vertex_normals, dtype=np.float32).flatten()
    sphere_uvs = [0.0, 0.0] *len(sphere_tm.vertices)

    # Ambos meshes usan la misma geometría; el material se setea en el nodo del grafo
    mesh_ball = Model(
        sphere_verts,
        normal_data=sphere_normals,
        index_data=sphere_faces,
        uv_data=sphere_uvs
        )

    #----------------------------Posiciones de Spawn----------------------------#
    # Y,Z ctes; varía solo a lo largo de X
    SPAWN_Y = 1.5
    SPAWN_Z = -10

    spawn_positions = [
        np.array([-2, SPAWN_Y, SPAWN_Z], dtype=np.float32),
        np.array([0, SPAWN_Y, SPAWN_Z], dtype=np.float32),
        np.array([2, SPAWN_Y, SPAWN_Z], dtype=np.float32)
    ]

    #--------------------------------Grafo de Escena----------------------------#
    #plataforma
    world.add_node(
        "Plataforma",
        mesh=mesh_Plat,
        mode=GL_TRIANGLES,
        pipeline=flat_pipeline,
        position=[-5, 0, -15],
        scale=[0.25, 0.25, 0.25],
        rotation=[np.radians(30), 0, 0],
        material=Material(
            ambient=[0.54, 0.27, 0.07],
            diffuse=[0.54, 0.27, 0.07]
            )
    )
    
    #luz
    world.add_node(
        'dirLight',
        light=DirectionalLight(),
        pipeline=flat_pipeline
    )

    #Nodo contenedor de pelotas
    world.add_node('Pelotas')

    #crear pelota inicial
    pelota_flotante = make_floating_ball()

    #-----------------------------------Eventos---------------------------------#

    @controller.event
    def on_draw():
        controller.clear()
        glClearColor(*(controller.sky_color * controller.intensity),1)
        glEnable(GL_DEPTH_TEST)
        if controller.wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        axis.draw()
        world.draw()

    @controller.event
    def on_key_press(symbol, modifiers):
        global pelota_flotante

        # recorrer posiciones de spawn con flechas izquierda/derecha
        if symbol == key.LEFT:
            controller.spawnPos_index = (controller.spawnPos_index - 1) % len(spawn_positions)
            # Mover la pelota flotante a nueva pos
            nueva_pos = spawn_positions[controller.spawnPos_index].copy()
            pelota_flotante.pos = nueva_pos
            world[pelota_flotante.node_name]['position'] = list(nueva_pos)

        elif symbol == key.RIGHT:
            controller.spawnPos_index = (controller.spawnPos_index + 1) % len(spawn_positions)
            nueva_pos = spawn_positions[controller.spawnPos_index].copy()
            pelota_flotante.pos = nueva_pos
            world[pelota_flotante.node_name]['position'] = list(nueva_pos)

        elif symbol == key.UP:                                                  # alternar material de próxima pelota
            controller.material_index = (controller.material_index + 1) % len(MATERIALES)

        elif symbol == key.DOWN:
            controller.material_index = (controller.material_index - 1) % len(MATERIALES)

        # Soltar pelota desde la posición seleccionada
        elif symbol == key.SPACE:
            # Soltar la pelota flotante actual
            pelota_flotante.drop()
            controller.pelotas.append(pelota_flotante)
            #DEBUG
#            print(f"[Drop] {pelota_flotante.node_name} | material: {pelota_flotante.material_name}")#DEBUG

            # Dejar nueva pelota flotante
            pelota_flotante = make_floating_ball()

    @controller.event
    def on_mouse_motion(x, y, dx, dy):
        cam.yaw += dx * .001
        cam.pitch += dy * .001
        cam.pitch = math.clamp(cam.pitch, -(np.pi/2 - 0.01), np.pi/2 - 0.01)

#----------------------------------update---------------------------------------#
    def update(dt):
#        global pelota_flotante
        controller.time += dt                                                   #paso del tiempo

        #tener plano de platfm
        plane_point, plane_normal = get_platform_transform(world)

        to_remove = []
        for pelota in controller.pelotas:
            pelota.step(dt, plane_point, plane_normal)                          #actualizar pos de toda pelota

            if not pelota.alive():
                to_remove.append(pelota)
            else:
                world[pelota.node_name]['position'] = list(pelota.pos)

        for pelota in to_remove:                                                #eliminar pelotas muertas
            world.remove_node(pelota.node_name)
            controller.pelotas.remove(pelota)

        world[pelota_flotante.node_name]['position'] = list(pelota_flotante.pos)#actualizar nodo de flotante

        world.update()
        axis.update()
        cam.time_update(dt)

    clock.schedule_interval(update,1/60)
    run()