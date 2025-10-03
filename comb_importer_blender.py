# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
# Expect this to be buggy, try the single mesh option if it doesn't work first time

import sys
import bmesh
import os
import io
import struct
import math
import mathutils
from pathlib import Path

from bpy_extras.io_utils import ImportHelper
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty, CollectionProperty
from bpy.types import Operator
import bpy
from array import array
from mathutils import Vector

class ChoroQCombImporter(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "choroq_importer.comb"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "ChoroQ Importer (.comb)"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".comb"
    
    filter_glob: StringProperty(default="*.comb;", options={'HIDDEN'})

    directory : StringProperty(subtype='DIR_PATH')
    filepath: StringProperty(subtype='FILE_PATH',)
    files: CollectionProperty(type=bpy.types.PropertyGroup)

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    single_mesh: BoolProperty(
        name="Single mesh",
        description="Combine all meshes into one",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "single_mesh")

    def execute(self, context):
        base = Path(self.directory)                
        MaterialName = "mat0"
        for f in self.files:
            MeshMat = bpy.data.materials.new(MaterialName)
            ChoroQCombImporter.parse_comb(context, f.name, base / f.name, base, self.single_mesh, MeshMat)
            
        return {"FINISHED"}
            
        
    
    def parse_comb(context, filename, filepath, base, single_mesh, mat = None):
        print(base)
        print(filepath)
        print(filename)
        coord = filename[1:3]
        
        try:
            coord = filename[1:4]
            print(F"coord is {coord}")
            posc = int(coord[0])
            posb = int(coord[1])
            posa = int(coord[2])
            print(F"coord is {posc}{posb}{posa}")
        except:
            posc = posb = posa = None
        
        
        if mat == None:
            MaterialName = "mat0"
            MeshMat = bpy.data.materials.new(MaterialName)
        else:
            MaterialName = "shared"
            MeshMat = mat
        
        mesh1 = bpy.data.meshes.new(f"Mesh")
#        mesh1.use_auto_smooth = True
        
        if posc != None:
            CurCollection = bpy.data.collections.new(F"{posc}{posb}{posa}")#Make Collection per comb loaded
        else:
            CurCollection = bpy.data.collections.new(filename[0:3]) #Make Collection per comb loaded
        bpy.context.scene.collection.children.link(CurCollection)


        # comb - mesh data format
        # meshes 262
        # type field
        # s z8-x0-0
        # vertex_count 6
        # face_count 4
        # texture texturex
        # end_header

        simple_format = False
        f = open(filepath, 'r', encoding='utf-8')
        magic = f.readline()
        if not magic.startswith("comb"):
            print(f"magic wrong {magic}")
            # Simple file format
            meshCount = 1
            simple_format = True
            combType = "1"
            f.seek(0, os.SEEK_SET)
        else:
            meshCount = int(f.readline().split(' ')[1])
            combType = f.readline().split(' ')[1].strip()
        
        print(f"meshCount {meshCount} combType #{combType}#")
#        return {'FINISHED'}

        #mesh1 = bpy.data.meshes.new(f"Mesh")
        
        #mesh = mesh1
        #bm = bmesh.new()

        Normals = []
        vertList = []
        normalList = []
        faceList = []
        colorList = []
        ncolorList = [] # night colors
        uvList = []
        
        vertsRead = 0
        facesRead = 0
        hasMaterialSetup = False

        for i in range(meshCount):
#            if not single_mesh:
#                mesh1 = bpy.data.meshes.new(f"Mesh {i}")
#                mesh1.use_auto_smooth = True
#                obj = bpy.data.objects.new(MaterialName, mesh1)
#                CurCollection.objects.link(obj)
#                bpy.context.view_layer.objects.active = obj
#                obj.select_set(True)
#                mesh = bpy.context.object.data
#                bm = bmesh.new()
#                Normals = []
#                vertList = []
#                normalList = []
#                faceList = []
#                colorList = []
#                uvList = []

            if not simple_format:
                start, name = f.readline().split(' ')
                start = ""
                name = filename[0:3]

            vertCount = int(f.readline().split(' ')[1])
            faceCount = int(f.readline().split(' ')[1])
            textureAttempt = f.readline().split(' ')
            textureName = ""
            if len(textureAttempt) > 0:
                if len(textureAttempt[1]) > 0:
                    textureName = textureAttempt[1][0:-1]
            
            
            # Setup material info
            if not hasMaterialSetup:
                try:
                    texPath = str(base / textureName)
                    img = bpy.data.images.load(texPath, check_existing=True)
                    #img = bpy.data.images.load(f"//{textureName}", check_existing=False)
                    mat.use_nodes=True 
                    material_output = mat.node_tree.nodes.get('Material Output')
                    principled_BSDF = mat.node_tree.nodes.get('Principled BSDF')

                    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_node.image = img
                    mat.node_tree.links.new(tex_node.outputs[0], principled_BSDF.inputs[0])
                    hasMaterialSetup = True
                
                except RuntimeError as e:
                    print(f"Failed to load texture {e}")
                except Exception as e:
                    raise e

            #print(f"verts {vert_count} faces {faceCount}")
            f.readline() # End header
            
            for vert in range(vertCount):
                v, n, c, nightc, uv, e = ChoroQCombImporter.read_point(f, combType)
                vertList.append(Vector(v))
                normalList.append(n)
                colorList.append(c)
                ncolorList.append(nightc)
                uvList.append(uv)
            for face in range(faceCount):
                face = ChoroQCombImporter.read_face(f, combType)
                faceList.append([face[0] + vertsRead, face[1] + vertsRead, face[2] + vertsRead])
                
            vertsRead += vertCount
            
            if not simple_format:
                end, name = f.readline().split(' ')
        #print(vertList)
        mesh1.from_pydata(vertList, [], faceList)
#        mesh1.vertex_colors.new(
        color_attri = mesh1.color_attributes.new('day', 'FLOAT_COLOR', 'POINT')
        night_color_attri = mesh1.color_attributes.new('night', 'FLOAT_COLOR', 'POINT')
        
        #mesh1.faces.ensure_lookup_table()
        #bpy.ops.uv.unwrap()
        uv_layer = mesh1.uv_layers.new()
        
        mesh1.uv_layers.active = uv_layer
        
#        v_index = 0
        #for v_index in range(len(mesh1.vertices)):
        for face in mesh1.polygons:
            for v_index, loop_idx in zip(face.vertices, face.loop_indices):
#        for v in mesh1.verts:
                c = colorList[v_index]
                nc = ncolorList[v_index]
                uv = uvList[v_index]
                color_attri.data[v_index].color = [float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0, float(c[3]) / 255.0]
                night_color_attri.data[v_index].color = [float(nc[0]) / 255.0, float(nc[1]) / 255.0, float(nc[2]) / 255.0, float(nc[3]) / 255.0]
                uv_layer.data[loop_idx].uv = [uv[0], uv[1]]
            

            
        
#        for c in colorList:
#            print(f"{color_attri.data[i].color[0]}")
#            color_attri.data[i].color[0] = float(c[0]) / 255.0
#            color_attri.data[i].color[1] = float(c[1]) / 255.0
#            color_attri.data[i].color[2] = float(c[2]) / 255.0
#            color_attri.data[i].color[3] = float(c[3]) / 255.0
##            color_attri.data[i].color = [int(c[0]), int(c[1]), int(c[2]), int(c[3])]
#            print(f"{color_attri.data[i].color[0]} {float(c[0]) / 255.0}")
#        for c in ncolorList:
#            print(f"{night_color_attri.data[i].color[0]}")
#            night_color_attri.data[i].color[0] = float(c[0]) / 255.0
#            night_color_attri.data[i].color[1] = float(c[1]) / 255.0
#            night_color_attri.data[i].color[2] = float(c[2]) / 255.0
#            night_color_attri.data[i].color[3] = float(c[3]) / 255.0
##            color_attri.data[i].color = [int(c[0]), int(c[1]), int(c[2]), int(c[3])]
#            print(f"{night_color_attri.data[i].color[0]} {float(c[0]) / 255.0}")
        mesh1.update()
#        for v in vertList:
#            bm.verts.new(v)
#        bm.to_mesh(mesh)

#        for face in faceList:
#            try:
#                bm.faces.new((list[face[0]],list[face[1]],list[face[2]]))
#            except:
#                continue
#        bm.to_mesh(mesh)
#        
#        uv_layer = bm.loops.layers.uv.verify()
#        color_layer = bm.loops.layers.color.new("Color")
#        for f in bm.faces:
#            f.smooth=True
#            for l in f.loops:
#                if normalList != []:
#                    Normals.append(normalList[l.vert.index])
#                l[color_layer]= colorList[l.vert.index]
#                luv = l[uv_layer]
#                try:
#                    luv.uv = uvList[l.vert.index]
#                except:
#                    continue
#        bm.to_mesh(mesh)    
#        bm.free()
#        mesh1.normals_split_custom_set(Normals)

        localXOffset = 0
        localZOffset = 0
        if posc != None:
            localXOffset = posb * 3200 + (posa % 2) * 1600
            localZOffset = posc * 3200

            if posa > 1:
                localXOffset = localXOffset + 800
                localZOffset = localZOffset + 1600
        obj = bpy.data.objects.new("Mesh", mesh1)
        obj.location = (localXOffset, localZOffset, 0)
        obj.data.materials.append(MeshMat)
#        bpy.context.scene.collection.children.link(CurCollection)
        CurCollection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
#            if not single_mesh:
#                bm.free()
#                mesh1.normals_split_custom_set(Normals)

#            if len(obj.data.materials)>0:
#                obj.data.materials[0]=MeshMat
#            else:
#                obj.data.materials.append(MeshMat)
            

#        if single_mesh:
#            bm.to_mesh(mesh)
#            bm.free()
#            mesh1.normals_split_custom_set(Normals)
        f.close()

        return {'FINISHED'}

    def read_point(file, combType):
        line = file.readline().split(' ')
        x = y = z = nx = ny = nz = 0
        r = g = b = a = s = t = 0
        nr = ng = nb = 0
        fx = fy = fz = 0
        data = map(lambda x: float(x), line)
        if combType == "1":
            # "Normal" mesh
            x,y,z,nx,ny,nz,r,g,b,a,s,t = data
        elif combType == "2":
            # Collider
            x,y,z,nx,ny,nz = data
        elif combType == "field":
            # "Field" mesh
            x,y,z,fx,fy,fz,nx,ny,nz,r,g,b,a,nr,ng,nb,na,s,t = data
        elif combType == "4":
            # Post collider
            x,y,z,nx,ny,nz = data
        else:
            print(f"UNKNOW MESH TYPE {combType}")
        return (x, z, y), (nx, ny, nz), (r, g, b, a), (nr, ng, nb, na), (s, t), (fx, fy, fz)

    def read_face(file, combType):
        line = file.readline().split(' ')
        f, v0, v1, v2 = map(lambda x: int(x), line)
        return v0, v1, v2


# Only needed if you want to add into a dynamic menu.
def menu_func_import(self, context):
    self.layout.operator(ChoroQCombImporter.bl_idname, text="ChoroQ Importer (.comb)")


# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(ChoroQCombImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ChoroQCombImporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.import_test.ChoroQCombImporter.parse_comb('INVOKE_DEFAULT')
