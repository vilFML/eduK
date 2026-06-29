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

        self.pelotas = deque()                                                  #para contar pelotas actuales
        self.pelota_count = 0                                                   #contador de pelotas
        self.spawn_index = 1                                                    #para alternar pos de spawn

class MyCam(FreeCamera):
    def __init__(self, position=np.array([0, 0, 0]), camera_type="perspective"):
        super().__init__(position, camera_type)
        self.direction = np.zeros(3)
        self.speed = 0                                                          #camara fija

    def time_update(self, dt):
        self.update()
        self.focus = self.position + self.forward

#----------------------------------Clases Propias---------------------------------------#
#Pelota bajo gravedad
class Pelota:
    def __init__(self, node_name, pos, vel, ttl, material_name):
        self.node_name = node_name                                              #nombre en nodo de grafo
        
        self.ttl = ttl #[s]        

        #cinematica
        self.pos = np.array(pos, dtype=np.float32)
        self.vel = np.array(vel, dtype=np.float32)

        self.material_name = material_name                                      #ej: 'madera','goma'


    #para actualizar cinematica
    def step(self, dt):
        self.ttl -= dt

        self.vel += G*dt
        self.pos += self.vel*dt

    #para ver si pelota esta viva
    def alive(self):
        return bool(self.ttl>0)

#--------------------------------Funciones-------------------------------------#
def spawn_ball(world, controller, spawn_positions, ball_mesh_rubber, ball_mesh_metal):
    """
    Crea una nueva pelota en la posición de spawn seleccionada y la agrega
    al SceneGraph y a la lista de pelotas activas del controller.
    """
    idx = controller.spawn_index
    pos = spawn_positions[idx]["pos"].copy()
    material_name = spawn_positions[idx]["material"]

    # Alternamos material entre las dos opciones para variedad
    # (en esta versión, cada posición tiene un material fijo asignado)
    if material_name == "rubber":
        mat = Material(ambient=[0.8, 0.1, 0.1], diffuse=[0.8, 0.1, 0.1])   # rojo
        ball_mesh = ball_mesh_rubber
    else:
        mat = Material(ambient=[0.6, 0.6, 0.7], diffuse=[0.6, 0.6, 0.7])   # gris metálico
        ball_mesh = ball_mesh_metal

    # Velocidad inicial: cae directo hacia abajo
    vel = [0.0, -0.5, 0.0]

    name = f"ball-{controller.pelota_count}"
    controller.pelota_count += 1

    world.add_node(
        name,
        mesh=ball_mesh,
        mode=GL_TRIANGLES,
        pipeline=flat_pipeline,
        position=list(pos),
        scale=[BALL_RADIUS, BALL_RADIUS, BALL_RADIUS],
        material=mat,
    )

    pelota = Pelota(
        node_name=name,
        pos=pos,
        vel=vel,
        ttl=10.0,           # 10 segundos de vida
        material_name=material_name,
    )
    controller.pelotas.append(pelota)
    print(f"[Spawn] {name} en posición {pos} | material: {material_name}")
    



#--------------------------------Constantes-------------------------------------#
G = np.array([0.0, -1, 0.0])                                                              #Y>0 es hacia arriba
BALL_RADIUS = 0.05                  # radio visual de la esfera en escena

#--------------------------------Principal--------------------------------------#
if __name__ == "__main__":

    #controller/window
    controller = Controller(1000,1000,"Auxiliar 8")
    controller.set_exclusive_mouse(True)

    root = os.path.dirname(__file__)

    flat_pipeline = init_pipeline(root + "/flat.vert", root + "/flat.frag")     #pipeline con un flat shader

    cam = MyCam([0,1,0])                                                        #camara

    axis = init_axis(cam)                                                       #axis para mayor claridad

    world = SceneGraph(cam)



#--------------------------------Mallas-----------------------------------------#
    #Plataforma
    n = 50
    vertices = []
    normals = []
    #generar vertices y normales
    for i in range(n):
        for j in range(n):
            vertices += [j, 0, i]
            normals += [0, 1, 0]
    indices = []                                                                #generar indices: dos triangulos por cuadrado
    for i in range(n-1):
        for j in range(n-1):
            indices += [n*(i+1) + j + 1, n*i + j + 1, n * i + j]
            indices += [n*(i+1) + j, n*(i+1) + j + 1, n * i + j]
    #hacer ruido random
    for i in range(n*n*2):
        vertices[np.random.randint(0, n*n) * 3 + 1] += 1
    #mas ruido
    for i in range(n*n):
        vertices[np.random.randint(0, n*n) * 3 + 1] += 2
    # Creamos un trimesh object con la geometria
    tri = tm.Trimesh(vertices=np.array(vertices).reshape(len(vertices)//3, 3), faces=np.array(indices).reshape(len(indices)//3, 3), process=False)
    # Sacamos las normales
    betterNormals = np.array(tm.smoothing.get_vertices_normals(tri)).flatten()
    # Filtro para el ruido
    tri = tm.smoothing.filter_humphrey(tri)
    #Necesario transformar esto
    verticesT = np.array(tri.vertices, dtype=np.float32).flatten()
    facesT = np.array(tri.faces, dtype=np.float32).flatten()
    normalT = np.array(tri.vertex_normals, dtype=np.float32).flatten()
    uvs = []
    for i in range(n):
        for j in range(n):
            uvs += [0.0, 0.0]             
    #hacemos el mesh como siempre
    mesh_Plat = Model(verticesT, normal_data=normalT, index_data=facesT, uv_data=uvs)


    # Esfera desde .obj
    sphere_tm = tm.load(root+"/assets/sphere.obj")

    #almacenar vertices, caras y vectores normales de malla de esfera (vienen en .obj)
    sphere_verts = np.array(sphere_tm.vertices, dtype=np.float32).flatten()
    sphere_faces = np.array(sphere_tm.faces, dtype=np.float32).flatten()
    sphere_normals = np.array(sphere_tm.vertex_normals, dtype=np.float32).flatten()
    sphere_uvs = [0.0, 0.0] *len(sphere_tm.vertices)

    # Ambos meshes usan la misma geometría; el material se setea en el nodo del grafo
    ball_mesh_rubber = Model(sphere_verts, normal_data=sphere_normals,
                             index_data=sphere_faces, uv_data=sphere_uvs)
    ball_mesh_metal  = Model(sphere_verts, normal_data=sphere_normals,
                             index_data=sphere_faces, uv_data=sphere_uvs)

#----------------------------Posiciones de Spawn----------------------------#
    # La plataforma está escalada a 0.1 y centrada en [0,0,0].
    # El borde superior (y más alto del terreno suavizado) queda aprox. en y≈0.3
    # Las tres posiciones cubren izquierda, centro y derecha del eje X de la plataforma.
    SPAWN_Y = 2.5       # altura desde la que caen (por encima de la plataforma)
    SPAWN_Z = 0.25      # profundidad central de la plataforma (escala 0.1 * n/2 * 0.1)

    spawn_positions = [
        {"label": "Izquierda", "pos": np.array([-0.5, SPAWN_Y, SPAWN_Z]), "material": "rubber"},
        {"label": "Centro",    "pos": np.array([ 0.25, SPAWN_Y, SPAWN_Z]), "material": "metal"},
        {"label": "Derecha",   "pos": np.array([ 1.0,  SPAWN_Y, SPAWN_Z]), "material": "rubber"},
    ]


#--------------------------------Grafo de Escena-------------------------------------#
    #plataforma
    world.add_node("Plataforma",
                mesh=mesh_Plat,
                mode=GL_TRIANGLES,
                pipeline=flat_pipeline,
                position=[0, 0, 0],
                scale=[0.1, 0.1, 0.1],
                rotation=[0, 0, np.radians(15)],
                material=Material(ambient=[0.54, 0.27, 0.07],
                                diffuse=[0.54, 0.27, 0.07])
                )

    #luz
    world.add_node("dirLight",
                light=DirectionalLight(ambient=[.6, .6, .6],
                                        diffuse=[.6, .6, .6]
                                        ),
                pipeline=flat_pipeline
#                rotation=[-np.pi/4, 0, 0]
                )

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
        # Ciclar posición de spawn con flechas izquierda/derecha
        if symbol == key.LEFT:
            controller.spawn_index = (controller.spawn_index - 1) % len(spawn_positions)

        elif symbol == key.RIGHT:
            controller.spawn_index = (controller.spawn_index + 1) % len(spawn_positions)

        # Lanzar pelota desde la posición seleccionada
        elif symbol == key.SPACE:
            spawn_ball(world, controller, spawn_positions,
                       ball_mesh_rubber, ball_mesh_metal)

    @controller.event
    def on_mouse_motion(x, y, dx, dy):
        cam.yaw += dx * .001
        cam.pitch += dy * .001
        cam.pitch = math.clamp(cam.pitch, -(np.pi/2 - 0.01), np.pi/2 - 0.01)


#----------------------------------update---------------------------------------#
    def update(dt):
        controller.time += dt

        to_remove = []
        for pelota in controller.pelotas:
            pelota.step(dt)                                                     #actualizar pos de toda pelota

            if not pelota.alive():
                to_remove.append(pelota)
            else:
                world[pelota.node_name]['position'] = list(pelota.pos)

        for pelota in to_remove:
            world.remove_node(pelota.node_name)
            controller.pelotas.remove(pelota)

        world.update()
        axis.update()
        cam.time_update(dt)

    clock.schedule_interval(update,1/60)
    run()