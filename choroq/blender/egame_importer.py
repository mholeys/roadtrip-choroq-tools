import bpy
import bmesh
import os
import struct

from pyffi.utils.trianglemesh import Mesh
from pyffi.utils.trianglestripifier import TriangleStrip, TriangleStripifier

from bpy_extras.io_utils import ImportHelper

from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from choroq.egame.car import CarModel
from choroq.egame.course import CourseModel

from mathutils import Vector

from pathlib import Path

class HG2FieldImporter(Operator, ImportHelper):
    bl_idname = "choroq_hg2.field_importer"
    bl_label = "Import Field (Choro Q HG2/HG3)"

    # ImportHelper mix-in class uses this.
    filename_ext = ".BIN"
    filepath: StringProperty(subtype='FILE_PATH',)

    filter_glob: StringProperty(
        default="*.BIN",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        issue = False
        with open(self.file, "rb") as f:
            course = CourseModel.read_course(f)
            # Convert course to blender data

        if issue:
            return {"CANCELLED"}
        return {"FINISHED"}

class HG2CarImporter(Operator, ImportHelper):
    bl_idname = "choroq_hg2.car_importer"
    bl_label = "Import Car (Choro Q HG2/HG3)"

    # ImportHelper mix-in class uses this.
    filename_ext = ".BIN"
    filepath: StringProperty(subtype='FILE_PATH',)

    filter_glob: StringProperty(
        default="*.BIN",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        issue = False
        path = Path(self.filepath)
        filename = path.name
        car_name = path.stem
        with open(self.filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)
            car = CarModel.read_car(f, 0, file_size)
            # Convert car to blender data
            part_names = [
                ["Body", "Lights", "Brake lights"],
                ["Low-Poly Body", "Low-Poly Lights", "None"],
                ["Spoiler Default", "Spoiler1-1", "Spoiler1-2"],
                ["Spoiler2", "Spoiler2-Brake", "Spoiler2-2"],
                ["Jet", "Jet-1", "Jet-2"],
                ["Sticker", "Sticker-1", "Sticker-2"],
            ]
            # TODO: handle HG3 part/names. detect or have option
            # Create collection for each car. TODO: add option to do this/not
            collection = bpy.data.collections.new(car_name)
            bpy.context.scene.collection.children.link(collection)
            # Create blender object for each part
            body_mat = bpy.data.materials.new(f"{car_name}")

            # This is used for jets as I do not know which texture it uses
            unknown_mat = bpy.data.materials.new(f"{car_name}")

            for i, subfile in enumerate(car.meshes):
                vertList = []

                for mi, mesh in enumerate(subfile):
                    if i < len(part_names) and mi < len(part_names[i]):
                        mesh_path = part_names[i][mi]
                    else:
                        mesh_path = f"{i}-{mi}"
                    blen_mesh = bpy.data.meshes.new(mesh_path)

                    for vi in range(mesh.mesh_vert_count):
                        vertList.append(Vector(mesh.mesh_verts[vi]))

                    face_list = []
                    for face in mesh.mesh_faces:
                        face_list.append([face[0]-1, face[1]-1, face[2]-1])

                    blen_mesh.from_pydata(vertList, [], face_list)
                    blen_mesh.update()

                    uv_layer = blen_mesh.uv_layers.new(name="UVMap")
                    colour_layer = blen_mesh.color_attributes.new(
                        name="vert_colours",
                        type='BYTE_COLOR',
                        domain='CORNER'
                    )

                    for face in blen_mesh.polygons:
                        for v_index, loop_idx in zip(face.vertices, face.loop_indices):
                            #        for v in mesh1.verts:
                            r, g, b, a = mesh.mesh_colours[v_index]
                            uv = mesh.mesh_uvs[v_index]
                            colour_layer.data[v_index].color = [int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF, int(a) & 0xFF]
                            uv_layer.data[loop_idx].uv = [uv[0], uv[1]]

                    blen_mesh.update()
                    blen_obj = bpy.data.objects.new(mesh_path, blen_mesh)
                    bpy.context.scene.collection.objects.link(blen_obj)
                    collection.objects.link(blen_obj)

                    if i == 0 or i == 1:
                        blen_obj.data.materials.append(body_mat)
                    else:
                        blen_obj.data.materials.append(unknown_mat)


        if issue:
            return {"CANCELLED"}
        return {"FINISHED"}

def menu_hg2_field_import(self, context):
    self.layout.operator(HG2FieldImporter.bl_idname, text="Import Field (Choro Q HG2/HG3)")

def menu_hg2_car_import(self, context):
    self.layout.operator(HG2CarImporter.bl_idname, text="Import Car (Choro Q HG2/HG3)")

# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(HG2FieldImporter)
    bpy.utils.register_class(HG2CarImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_hg2_field_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_hg2_car_import)


def unregister():
    bpy.utils.unregister_class(HG2FieldImporter)
    bpy.utils.unregister_class(HG2CarImporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_hg2_field_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_hg2_car_import)

if __name__ == "__main__":
    register()