#--------------------------------Librerias-------------------------------------#
#para usar funciones de trimesh de colisiones, es necesario instalar la librería 'rtree'

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
    ('Madera', 0.01, Material(
        ambient=[0.6, 0.3, 0.1],
        diffuse=[0.6, 0.3, 0.1],
        specular=[0.1, 0.1, 0.1],
        shininess=0
    )),
    ('Goma', 0.8, Material(
        ambient=[0.8, 0.1, 0.1],
        diffuse=[0.8, 0.1, 0.1],
        specular=[0.1, 0.1, 0.1],
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
        self.light_mode = False
        self.light_dir = np.zeros(2)
        self.light_color = np.ones(3)
        self.light_distance = 1
        self.wireframe = False

        self.pelotas = deque()                                                  #pelotas que ya estan cayendo
        self.cant_pelotas = 0                                                   #contador de pelotas
        self.spawnPos_index = 1                                                 #para alternar pos de spawn
        self.material_index = 0                                                 #indice para material seleccionado

class MyCam(FreeCamera):
    def __init__(self, position=np.array([0, 0, 0]), camera_type="perspective"):
        super().__init__(position, camera_type)
        self.direction = np.zeros(3)
        self.speed = 10

    def time_update(self, dt):
        self.update()
        dir = self.direction[0]*self.forward + self.direction[1]*self.right
        dir_norm = np.linalg.norm(dir)
        if dir_norm:
            dir /= dir_norm
        self.position += dir*self.speed*dt
        self.focus = self.position + self.forward

#----------------------------------Clases Propias---------------------------------------#
#Pelota bajo gravedad, rebota con plataforma
class Pelota:
    def __init__(self, node_name, pos, restitution, ttl=7.0):
        self.node_name = node_name                                              #nombre en nodo de grafo
        self.ttl = ttl #[s]
        #props
        self.restitution = restitution                                          #depende de material: [0,1]
        self.radio = RADIO_PELOTAS
        #cinematica
        self.pos = np.array(pos, dtype=np.float32)
        self.vel = np.zeros(3, dtype=np.float32)                                # pelota 'flotando' inicialmente
        self.is_dropped = False                                                 #flota hasta apretar espacio

    #para actualizar cinematica
    def step(self, dt):
        if not self.is_dropped:                                                 #si aun no se suelta, hacer nada
            return
                
        #cinematica
        self.vel += G*dt
        self.pos += self.vel*dt

        self.ttl -= dt

        #----------------Colision con malla de plataforma-----------------------#
        #tener pto mas cercano a malla: fn devuelve punto, distancia, triangulo de pto
        closest_point, distance, face_id = tri_world.nearest.on_surface([self.pos]) 
        closest_point = closest_point[0]
        distance = distance[0]

        if face_id[0] is not None:                                              #si pto esta en triangulo (existe cara)
            normal = tri_world.face_normals[face_id[0]]                         #se toma su vector normal
            if np.dot(normal, self.pos - closest_point) < 0:                    #si normal apunta en dirección opuesta
                normal = -normal                                                #   invertir
        else:                                                                   #caso borde: pto en vértice o arista
            normal = np.array([0, 1, 0], dtype=np.float32)

        if distance < self.radio:                                               #condicion de colision (dist menor al radio)
            #se desplaza fuera de la superficie
            correction = (self.radio - distance) * normal
            self.pos += correction

            #tener comp normal de vel
            vn = np.dot(self.vel, normal)
            if vn < 0:                                                          #si se mueve hacia superficie (vector <0)
                self.vel -= (1 + self.restitution) * vn * normal                #   aplicar rebote en direccion de normal

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

#--------------------------------Principal--------------------------------------#
if __name__ == "__main__":
    #ventana
    controller = Controller(1000,1000,"Tarea 3")
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

    # mesh de pelotas usan la misma geometría, material se asigna en el nodo del grafo
    mesh_ball = Model(
        sphere_verts,
        normal_data=sphere_normals,
        index_data=sphere_faces,
        uv_data=sphere_uvs
        )

    #----------------------------Posiciones de Spawn----------------------------#
    # Y,Z ctes; varía solo a lo largo de X
    SPAWN_Y = 0.5
    SPAWN_Z = -5

    spawn_positions = [
        np.array([-8, SPAWN_Y, SPAWN_Z], dtype=np.float32),
        np.array([0, SPAWN_Y, SPAWN_Z], dtype=np.float32),
        np.array([10, SPAWN_Y, SPAWN_Z], dtype=np.float32)
    ]

    #--------------------------------Grafo de Escena----------------------------#
    #plataforma
    world.add_node(
        "Plataforma",
        mesh=mesh_Plat,
        mode=GL_TRIANGLES,
        pipeline=flat_pipeline,
        position=[-10, 0, -10],
        scale=[0.5, 0.5, 0.5],
        rotation=[np.radians(30), 0, 0],
        material=Material(
            ambient=[0.8, 0.8, 0.8],
            diffuse=[0.8, 0.8, 0.8]
            )
    )

    #llevar malla de plataforma a 'espacio' de escena: Necesario para distancias en el mismo 'contexto' de escena
    matrix = world.get_transform('Plataforma')                                  #obtener matriz de transfm 4x4 del nodo en el grafo
    tri_world = tri.copy()                                                      #guardar malla en coordenadas de la escena
    tri_world.apply_transform(matrix)                                           #aplicar transfm a malla
    
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

        # alternar material de próxima pelota
        elif symbol == key.UP:
            controller.material_index = (controller.material_index + 1) % len(MATERIALES)
        elif symbol == key.DOWN:
            controller.material_index = (controller.material_index - 1) % len(MATERIALES)

        # Soltar pelota desde la posición seleccionada
        elif symbol == key.SPACE:
            # Soltar la pelota flotante actual
            pelota_flotante.drop()
            controller.pelotas.append(pelota_flotante)

            # Dejar nueva pelota flotante
            pelota_flotante = make_floating_ball()

        #movimiento de camara
        if symbol == key.W:
            cam.direction[0] = 1
        if symbol == key.S:
            cam.direction[0] = -1
        if symbol == key.A:
            cam.direction[1] = 1
        if symbol == key.D:
            cam.direction[1] = -1

    @controller.event
    def on_mouse_motion(x, y, dx, dy):
        cam.yaw += dx * .001
        cam.pitch += dy * .001
        cam.pitch = math.clamp(cam.pitch, -(np.pi/2 - 0.01), np.pi/2 - 0.01)

    @controller.event
    def on_key_release(symbol, modifiers):
        if symbol == key.W or symbol == key.S:
            cam.direction[0] = 0
        if symbol == key.A or symbol == key.D:
            cam.direction[1] = 0

#----------------------------------update---------------------------------------#
    def update(dt):
        controller.time += dt                                                   #paso del tiempo

        to_remove = []
        for pelota in controller.pelotas:
            pelota.step(dt)                                                     #actualizar pos de pelota viva

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