import bpy
import bmesh
import struct

from pyffi.utils.trianglemesh import Mesh
from pyffi.utils.trianglestripifier import TriangleStrip, TriangleStripifier

from bpy_extras.io_utils import ExportHelper

EXEC_ADDR_NORMAL = 32
EXEC_ADDR_TRANSPARENT = 80

unique_rbga = set()

def dump(obj):
   for attr in dir(obj):
       if hasattr( obj, attr ):
           print( "obj.%s = %s" % (attr, getattr(obj, attr)))


def triangulate_object(obj):
    me = obj.data
    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(me)

    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    # V2.79 : bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0)

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()


class HG2ExportHelperPanel(bpy.types.Panel):
    bl_idname = "hg2_export_helper_panel"
    bl_label = "HG2 Export Helper"

    instructions_panel_open_id = "hg2_export_helper_panel.instructions_open"
    object_panel_open_id = "hg2_export_helper_panel.object_open"
    object_index_panel_open_id = "hg2_export_helper_panel.object.index_open"
    object_colour_panel_open_id = "hg2_export_helper_panel.object.colour_open"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "HG2 Exporter"

    def draw(self, context):
        instructions = []
        layout_header, layout_body = self.layout.panel(self.instructions_panel_open_id, default_closed=False)
        layout_header.label(text='Verbose Instructions/actions')
        if layout_body is not None:
            instructions.append('Requirements:')
            instructions.append('For car body:')
            instructions.append('- [0] Main body')
            instructions.append('- [1] Lights (front+back)')
            instructions.append('- [2] Brake Lights')
            instructions.append('For other:')
            instructions.append('Look at the original')
            instructions.append('Copy the order of that [0/1/2]')
            instructions.append('Not all objects have 3 meshes')
            instructions.append('Just skip as needed')
            instructions.append('')
            instructions.append('It is recommended that all objects have')
            instructions.append('- The same texture, 128x128')
            instructions.append('- Colour attributes (vertex colours)')
            instructions.append('- [0] < 1500 triangles')
            instructions.append('- [1] < 200 triangles')
            instructions.append('- [2] < 200 triangles')
            instructions.append('Triangles make up the size')

            for line in instructions:
                layout_body.label(text=line)

        layout_header2, layout_body2 = self.layout.panel(self.object_panel_open_id, default_closed=False)
        layout_header2.label(text="Object config")
        if layout_body2 is not None:
            layout_body2.label(text='In Object mode')
            layout_body2.label(text='Select all objects you wish to use')
            layout_body2.label(text='then press configure attributes')
            layout_body2.operator(HG2SetupAttributesOperator.bl_idname, text="Configure attributes")

            layout_header3, layout_body3 = layout_body2.panel(self.object_index_panel_open_id, default_closed=False)
            layout_header3.label(text="Object assignment")
            if layout_body3 is not None:
                layout_body3.label(text='With all objects selected')
                layout_body3.label(text='switch to edit mode (Faces)')
                layout_body3.label(text='1 Go to Properties->Data->Attributes')
                layout_body3.label(text='2 Select \"ObjectIndex\"')
                layout_body3.label(text='3 Now select all faces for [1]')
                layout_body3.label(text='4 Then Mesh->Set Attribute -> 1')
                layout_body3.separator()
                layout_body3.label(text='Repeat for [2] setting to 2')

            layout_header3, layout_body3 = layout_body2.panel(self.object_colour_panel_open_id, default_closed=False)
            layout_header3.label(text="Object colour assignment")
            if layout_body3 is not None:
                layout_body3.label(text='In Object mode')
                layout_body3.label(text='Select all objects you wish to use')

                layout_body3.label(text='With all objects selected')
                layout_body3.label(text='switch to edit mode (Faces)')
                layout_body3.label(text='1 Go to Properties->Data->Attributes')
                layout_body3.label(text='2 Select \"ColourIndex\"')
                layout_body3.label(text='3 Select all faces for texturing')
                layout_body3.label(text='4 Then Mesh->Set Attribute -> 0')
                layout_body3.label(text='5 Select all faces for colour 1')
                layout_body3.label(text='6 Then Mesh->Set Attribute -> 1')
                layout_body3.label(text='5 Select all faces for colour 2')
                layout_body3.label(text='6 Then Mesh->Set Attribute -> 2')
                layout_body3.separator()

        self.layout.label(text='Once you have configure the ObjectIndex')
        self.layout.label(text='for all faces of your objects you can')
        self.layout.label(text='press export.')

        self.layout.separator()
        self.layout.label(text='Warning this may modify the model')
        #self.layout.prop(context.scene, "my_text_field")

        self.layout.operator(HG2Exporter.bl_idname, text="Export")


class HG2SetupAttributesOperator(bpy.types.Operator):
    bl_idname = "choroq_hg2.operator_setup_attributes"
    bl_label = "hg2 face attribute setter"

    def execute(self, context):
        select_objects = bpy.context.selected_objects
        objects = bpy.context.selected_objects
        for obj in objects:
            if obj.id_type != 'OBJECT' or obj.data.id_type != 'MESH':
                print(f"Skipping obj {obj} as not mesh")
                continue
            if 'ObjectIndex' not in obj.data.attributes:
                new_attribute = obj.data.attributes.new('ObjectIndex', 'INT', 'FACE')

                if new_attribute.name != 'ObjectIndex':
                    raise Exception(f"Failed to setup ObjectIndex face attribute, sorry this is still WIP. Error with: {obj}")
            if 'ColourIndex' not in obj.data.attributes:
                new_attribute = obj.data.attributes.new('ColourIndex', 'INT', 'FACE')

                if new_attribute.name != 'ColourIndex':
                    raise Exception(f"Failed to setup ColourIndex face attribute, sorry this is still WIP. Error with: {obj}")

        return {'FINISHED'}

def export_hg2(context, filepath):
    select_objects = bpy.context.selected_objects
    dump(select_objects)

    # Each of theses will contain a list, and that will contain lists of values, the inner list being a tristrip
    # 0 = Sub0 / Body
    # 1 = Sub1 / Lights
    # 2 = Sub2 / Brake lights
    vertices = [[[], []], [[], []], [[], []]]
    normals = [[[], []], [[], []], [[], []]]
    colours = [[[], []], [[], []], [[], []]]
    uvs = [[[], []], [[], []], [[], []]]
    colour_indices = [[[], []], [[], []], [[], []]]  # each inner will have 1 element of 0/1/2 to select which two-tone colour to use

    ever_textured = [False, False, False]
    ever_untextured = [False, False, False]

    for obj in bpy.context.selected_objects:
        print(f"processing [{obj.name}]")
        if obj.id_type != 'OBJECT' or obj.data.id_type != 'MESH':
            print("Skipping obj as not mesh")
            continue
        mesh = obj.data
        triangulate_object(obj)

        # Check if the mesh has valid color and uv arrays
        # if not create them, and populate with 0s

        # bpy.ops.uv.unwrap()
        # uv_layer = mesh1.uv_layers.new()
        # mesh1.uv_layers.active = uv_layer

        # Check for colour attributes
        #if not mesh.color_attributes or len(mesh.color_attributes) == 0:
        #    mesh.color_attributes.new("Color", 'BYTE_COLOR', 'CORNER')
        # dump(mesh.attributes.active_color)

        print(mesh.uv_layers)
        if not mesh.uv_layers or len(mesh.uv_layers) == 0:
            mesh.uv_layers.active = mesh.uv_layers.new()

        # Convert mesh into tristrips
        # Create pyffi mesh to convert to tristrips
        # On mesh for textured/untextured per colour index
        pyffi_mesh_0 = [[Mesh(), Mesh()], [Mesh(), Mesh()], [Mesh(), Mesh()]]
        pyffi_mesh_1 = [[Mesh(), Mesh()], [Mesh(), Mesh()], [Mesh(), Mesh()]]
        pyffi_mesh_2 = [[Mesh(), Mesh()], [Mesh(), Mesh()], [Mesh(), Mesh()]]
        pyffi_meshes = [pyffi_mesh_0, pyffi_mesh_1, pyffi_mesh_2]

        # Bad but possibly needed vertex -> face table. Probably bad
        face_dict = {}

        # We know they are triangles, as it's been force converted
        for face in mesh.polygons:
            # print('face')
            # print(face.vertices)
            # dump(face.vertices)

            # Get which object this face is for
            object_index = mesh.attributes['ObjectIndex'].data[face.index].value
            if object_index not in [0, 1, 2]:
                raise Exception("Invalid object index attribute, must be 0/1/2")
            colour_index = mesh.attributes['ColourIndex'].data[face.index].value
            if colour_index not in [0, 1, 2]:
                raise Exception("Invalid colour index attribute, must be 0/1/2")
            # Build up all faces into are temporary mesh, for tristripping

            # Check to see if any are textured, as we want to draw theses in a different strip
            v0_uv = mesh.uv_layers.active.data[face.loop_indices[0]].uv
            v1_uv = mesh.uv_layers.active.data[face.loop_indices[1]].uv
            v2_uv = mesh.uv_layers.active.data[face.loop_indices[2]].uv

            # print(f"v0_uv {v0_uv}")
            # print(f"v1_uv {v1_uv}")
            # print(f"v2_uv {v2_uv}")

            v0_textured = v0_uv[0] != 0 or v0_uv[1] != 0
            v1_textured = v1_uv[0] != 0 or v1_uv[1] != 0
            v2_textured = v2_uv[0] != 0 or v2_uv[1] != 0

            textured = 0
            if ((
                    v0_textured or v1_textured or v2_textured)
                    and
                    (v0_uv != v1_uv or v0_uv != v2_uv or v1_uv != v2_uv)):
                textured = 1
                ever_textured[object_index] = True
            else:
                ever_untextured[object_index] = True

            pyffi_meshes[object_index][colour_index][textured].add_face(face.vertices[0], face.vertices[1], face.vertices[2])
            face_dict[face.vertices[0]] = (face, face.loop_indices[0])
            face_dict[face.vertices[1]] = (face, face.loop_indices[1])
            face_dict[face.vertices[2]] = (face, face.loop_indices[2])

        print(f"Ever textured? {ever_textured[0]} {ever_textured[1]} {ever_textured[2]}")
        print(f"Ever untextured? {ever_untextured[0]} {ever_untextured[1]} {ever_untextured[2]}")

        # Calculate tristrips, per block of colour, as there is no way to reconstruct the original faces from verts
        for sub_obj_index in [0, 1, 2]:
            print(f"Tristripping {obj} for subj_obj [{sub_obj_index}]")
            for colour_index in [0, 1, 2]:
                for textured_index in [0, 1]:
                    pyffi_meshes[sub_obj_index][colour_index][textured_index].lock()
                    pyffi_stripper = TriangleStripifier(pyffi_meshes[sub_obj_index][colour_index][textured_index])

                    strips = pyffi_stripper.find_all_strips()

                    # Add the converted values to our lists
                    # strips_x = [[index,], [index,]], # sub list for each strip for obj x
                    for strip in strips:
                        new_verts = []
                        new_normals = []
                        new_colours = []
                        new_uv = []
                        new_colour_index = [colour_index]
                        for vert_index in strip:
                            # capture world position/rotation
                            x, y, z = obj.matrix_world @ mesh.vertices[vert_index].co
                            new_verts.append((x, y, z))
                            nx, nz, ny = mesh.vertices[vert_index].normal
                            new_normals.append((nx, ny, nz))
                            if mesh.attributes.active_color is not None:
                                r, g, b, a = mesh.attributes.active_color.data[vert_index].color_srgb
                            else:
                                r, g, b, a = 128.0, 128.0, 128.0, 128.0
                            new_colours.append((r, g, b, a))
                            unique_rbga.add((r * 256.0, g * 256.0, b * 256.0, a * 256.0))

                            # Have to access uvs via loop index
                            u, v = mesh.uv_layers.active.data[face_dict[vert_index][1]].uv
                            new_uv.append((u, v))
                        vertices[sub_obj_index][textured_index].append(new_verts)
                        normals[sub_obj_index][textured_index].append(new_normals)
                        colours[sub_obj_index][textured_index].append(new_colours)
                        uvs[sub_obj_index][textured_index].append(new_uv)
                        colour_indices[sub_obj_index][textured_index].append(new_colour_index)
        # for i in [0, 1, 2]:
        #     for textured_index in [0, 1]:
        #         print(f"For sub obj [{i}]")
        #         dim2 = len(vertices[i][textured_index])
        #         dim3 = None
        #         if dim2 != 0:
        #             dim3 = len(vertices[i][textured_index][0])
        #         print(f"Vertices length stripCount:[{dim2}] first:[{dim3}] ")
        #         print(vertices[i])
        #
        #         dim2 = len(normals[i][textured_index])
        #         dim3 = None
        #         if dim2 != 0:
        #             dim3 = len(normals[i][textured_index][0])
        #         print(f"Normals length stripCount:[{dim2}] first:[{dim3}] ")
        #
        #         dim2 = len(colours[i][textured_index])
        #         dim3 = None
        #         if dim2 != 0:
        #             dim3 = len(colours[i][textured_index][0])
        #         print(f"Colours length stripCount:[{dim2}] first:[{dim3}] ")
        #
        #         dim2 = len(uvs[i])
        #         dim3 = None
        #         if dim2 != 0:
        #             dim3 = len(uvs[i][textured_index][0])
        #         print(f"Uvs length stripCount:[{dim2}] first:[{dim3}] ")
        #
        #         dim2 = len(colour_indices[i][textured_index])
        #         print(f"colour_indices length stripCount:[{dim2}]")

    return save_mesh(filepath, vertices, normals, colours, uvs, colour_indices)


def save_mesh(filepath, vertices, normals, colours, uvs, colour_indices):
    exec_call_per_object = [EXEC_ADDR_NORMAL, EXEC_ADDR_TRANSPARENT, EXEC_ADDR_TRANSPARENT]
    # todo smoothness other than 280.5
    smoothness = 0  # 280.5
    with (open(filepath, "wb") as file):
        sizes = [16]
        paddings = []
        gif_counts = []
        for obj_index in [0, 1, 2]:
            # calculate/Estimate size of object
            # Each subsection will have parts
            # Each subsection will have an offset table (16 bytes, 2 longs, 2 shorts)
            # Each object will be 1 part
            # Each part will have DMa tag + zero word, with VIF setup tags (STCYCL) and VIF copy tag (16 bytes)
            # Each face will have a VIF expand tag
            # Each face will also have GIF tag (16 bytes)
            # Each face will have x/y/z*3 nx/ny/z*3 r/g/b*3 uv.u/uv.v/0*3 (144 bytes)
            # Each face will also have Exec call (4 bytes)
            # Each Part will have an end dma tag (16 bytes)
            exec_call = exec_call_per_object[obj_index]

            dma_tag_size = 4
            zero_pad_dma_size = 4
            vif_tag_size = 4
            gif_tag_size = 16  # for cars
            vif_exec_size = 4
            end_dma_tag_size = 16
            # Depends on exec call
            bytes_per_vertex = {EXEC_ADDR_NORMAL: 48, EXEC_ADDR_TRANSPARENT: 48}

            gif_count = 0

            # VIF here is set cycle tag, this is 3/4 of the dma tag
            part_header_size = dma_tag_size + zero_pad_dma_size + vif_tag_size

            mesh_size = 0
            # calculate byte length per strip
            for textured_index in [0, 1]:
                print(f"Object [{obj_index}]  has  {len(vertices[obj_index][textured_index])} strips")
                for strip_index in range(len(vertices[obj_index][textured_index])):
                    print(f"Object [{obj_index}] doing {strip_index} / {len(vertices[obj_index][textured_index])} strips {len(vertices[obj_index][textured_index][strip_index])}")
                    # copy gif tag (vif expand false), and expand tag with data
                    mesh_size += vif_tag_size + gif_tag_size + vif_tag_size

                    vert_count = len(vertices[obj_index][textured_index][strip_index])
                    if vert_count < 3:
                        raise Exception("Created a triangle strip, with no triangles")
                    mesh_size += vert_count * bytes_per_vertex[exec_call]

                    mesh_size += vif_exec_size  # call to run VU1 program
                    gif_count += 1

            total_size = part_header_size + mesh_size

            # Total size of this part (1 part of subsection)
            # Fix size to be padded to end on 16 boundary, to align dma tags (end dma tag)

            print(f"Padding required: total_size: {total_size} %16: {total_size % 16} + 16")

            padding = 0
            if total_size % 16 != 0:
                padding = 16 - (total_size % 16)
            print(f"Padding required: total_size: {total_size} %16: {total_size % 16} ({padding}) + {end_dma_tag_size}")
            total_size += padding + end_dma_tag_size
            sizes.append(total_size)
            paddings.append(padding)
            gif_counts.append(gif_count)

        # Write offset table for subsection
        # offset 0 = 16 is implicit
        print("Size table: ")
        print(sizes)
        print("Padding required: ")
        print(paddings)
        print("GifCounts: ")
        print(gif_counts)

        sizes[0] = 16
        # Force alignment to 16byte boundary (needed for dma I think)
        positions = [16, 16 + sizes[1], 16 + sizes[1] + sizes[2]]

        file.write(positions[1].to_bytes(4, byteorder='little'))
        file.write(positions[2].to_bytes(4, byteorder='little'))

        file.write(gif_counts[1].to_bytes(4, byteorder='little'))  # Unsure on this value so far, some parts are 0
        file.write(gif_counts[2].to_bytes(4, byteorder='little'))  # Unsure on this value so far, others are not

        # Now write out each part's mesh data in the HG2 format, from the assigned faces
        for obj_index in [0, 1, 2]:
            # Check position in file, we should know where we are at all points
            if file.tell() != positions[obj_index]:
                print(f"File position incorrect got {file.tell()} vs expected positions[{obj_index}] = {positions[obj_index]} obj: {obj_index}")
                raise Exception("Miscalculated size of object, bug in code, no solution in blender")

            # Write DMA tag
            dma_tag_suffix = [0x00, 0x10]
            # size_padding = 16 - ((sizes[obj_index + 1]) % 16)
            # if size_padding == 16:
            #     size_padding = 0
            # Take out length of the dma tag at the start, and end
            dma_tag_size = int((sizes[obj_index + 1] - 32) / 16)
            # print(sizes[part_index+1])
            # print(size_padding)
            # print(dma_tag_size)
            file.write(dma_tag_size.to_bytes(2, 'little'))
            file.write(bytes(dma_tag_suffix))

            # Write zero word
            file.write(bytes([0x00, 0x00, 0x00, 0x00]))

            # Write STCYCL VIF tag
            file.write(bytes([0x01, 0x01, 0x00, 0x01]))

            exec_call = exec_call_per_object[obj_index]
            for textured_index in [0, 1]:
                # Write mesh data
                # Loop over all strips and write out the data
                for strip_index in range(len(vertices[obj_index][textured_index])):
                    # Write VIF V4-32 tag, this just copies the GIF tag to the VIF for later use, so is always this
                    file.write(bytes([0x00, 0x80, 0x01, 0x6C]))

                    # Write GIF tag (to say what we are sending) (always same for cars AFAIK)
                    # e.g 3 verts = 03 80 00 00 00 40 36 31 12 04 00 00 00 00 00 00
                    vert_count = len(vertices[obj_index][textured_index][strip_index])
                    if vert_count > 255:
                        raise Exception(f"Strip too long, vert_count: {vert_count} max is 255 per strip.\n"
                                        f"No current fix sorry")
                    colour_group = colour_indices[obj_index][textured_index][strip_index][0]
                    texture_marker = 0

                    # check for texturing required primitive
                    textured = textured_index == 1

                    # # Check to see if any have texture coords
                    # for vertex_index in range(vert_count):
                    #     u, v = uvs[obj_index][textured_index][strip_index][vertex_index]
                    #     if u != 0 or v != 0:

                    #         # There might be other values, needs investigating
                    #         texture_marker = 0x00
                    #         textured = True
                    # 0x32 Tristrip flat shaded; not sure what this is used on
                    # 0x36 Tristrip Gouraud shaded
                    # 0x3A Tristrip flat shaded + textured; used on all textured surfaces afaik
                    # 0x3C Tristrip Gouraud shaded + textured; doesn't work
                    if textured:
                        if exec_call == EXEC_ADDR_TRANSPARENT:
                            prim = 0x3E
                            # Unsure what 2 means, but it is what is in the game
                            texture_marker = 0x02
                        else:
                            prim = 0x3A
                    else:
                        prim = 0x36

                    gif_tag = [vert_count, 0x80, 0x00, 0x00,
                               texture_marker, 0x40, prim, 0x31,  # First byte on this row, changes 0 or 1 or 2 ?
                               0x12, 0x04, 0x00, 0x00,
                               # First byte on this row v, sets the colour block I think, 0=texture, 1=colour1, 2=colour2
                               colour_group, 0x00, 0x00, 0x00]
                    file.write(bytes(gif_tag))

                    # Write VIF expand tag
                    vif_expand_count = vert_count * 4
                    vif_tag = [0x01, 0x80, vif_expand_count, 0x68]
                    file.write(bytes(vif_tag))

                    # Write out each vertex
                    for vertex_index in range(vert_count):
                        x, y, z = vertices[obj_index][textured_index][strip_index][vertex_index]
                        r, g, b, a = colours[obj_index][textured_index][strip_index][vertex_index]
                        u, v = uvs[obj_index][textured_index][strip_index][vertex_index]
                        # TODO: shiny/smoothness value
                        # dump(mesh.vertices[vert_index])

                        v = 1 - v

                        # print(f"x {x} y {y} z {z}")
                        # print(f"nx {nx} ny {ny} nz {nz}")
                        # print(f"r {r} g {g} b {b} a {a}")
                        # print(f"u {u} v {v}")

                        # round numbers to be the closest whole number, as the game seems to have an int in float
                        r = round(r * 256.0, 0)
                        g = round(g * 256.0, 0)
                        b = round(b * 256.0, 0)
                        rgba_allowed = [10, 30, 50, 60, 80, 128, 200, 230, 256]
                        tolerance = 1
                        # Only do this for numbers which are all the same. like 128/128/128 30/30/30
                        for close in rgba_allowed:
                            if abs(r - close) < tolerance:
                                if abs(g - close) < tolerance:
                                    if abs(b - close) < tolerance:
                                        r = close
                                        g = close
                                        b = close

                        # Guess smoothness
                        if textured:
                            smoothness = 51.0
                            if exec_call == EXEC_ADDR_TRANSPARENT:
                                smoothness = 1.0
                        else:
                            if colour_group == 0:
                                smoothness = 1.0
                            if colour_group == 1:
                                smoothness = 280.5

                            if 9 <= r <= 12 and 14 <= g <= 16 and 19 <= b <= 21:
                                # Windscreen og colour
                                # approx 0A0F14
                                smoothness = 357.0
                            elif 59 <= r <= 61 and 59 <= g <= 61 and 59 <= b <= 61:
                                # window trim
                                # approx 3C3C3C
                                smoothness = 0.0
                            # elif 0.0020 <= r <= 0.0039 and 0.0020 <= g <= 0.0039 and 0.0020 <= b <= 0.0039:
                            #     smoothness = 0
                            #elif body panels gaps:
                                # body panel gaps: #1E1E1E
                            #elif body:
                                # body E5E5E5

                        if exec_call == EXEC_ADDR_NORMAL or exec_call == EXEC_ADDR_TRANSPARENT:
                            nx, ny, nz = normals[obj_index][textured_index][strip_index][vertex_index]
                            vert_out = struct.pack('ffffffffffff',
                                                   x, z, y, # Tested this is correct (x , z, y)
                                                   -nx, nz, ny,  # Tested closest result is this (-nx, ny, nz)
                                                   r, g, b,
                                                   u, v, smoothness)
                        file.write(vert_out)
                    # Write Exec VIF tag
                    if exec_call == EXEC_ADDR_NORMAL:
                        exec_call_value = [0x04, 0x00, 0x00, 0x15]
                    elif exec_call == EXEC_ADDR_TRANSPARENT:
                        exec_call_value = [0x0A, 0x00, 0x00, 0x15]
                    else:
                        raise Exception("Invalid exec call, this is a bug")
                    file.write(bytes(exec_call_value))

            # Pad file so end dma is 16 aligned
            print(f"Padding required for obj {obj_index}: {paddings[obj_index]}")
            print(paddings)
            for i in range(paddings[obj_index]):
                file.write(bytes([0x00]))

            # Write end dma tag, for this part
            end_dma_tag = bytes([00, 00, 00, 0x60, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00])
            file.write(end_dma_tag)

    print(unique_rbga)
    return {"FINISHED"}


class HG2Exporter(bpy.types.Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "choroq_hg2.exporter"  # Important since its how bpy.ops.import_test.some_data is constructed.
    bl_label = "Export CHORO-Q HG2"

    # ExportHelper mix-in class uses this.
    filename_ext = ".BIN"

    filter_glob: bpy.props.StringProperty(
        default="*.BIN",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return export_hg2(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_file_export_hg2(self, context):
    self.layout.operator(HG2Exporter.bl_idname, text="Choro-Q Object exporter (HG2)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(HG2ExportHelperPanel)
    bpy.utils.register_class(HG2SetupAttributesOperator)
    bpy.utils.register_class(HG2Exporter)
    bpy.types.TOPBAR_MT_file_export.append(menu_file_export_hg2)

    # bpy.types.Scene.my_text_field = bpy.props.StringProperty(
    #     name="Custom Text",
    #     description="A custom text field",
    #     default=""
    # )


def unregister():
    bpy.utils.unregister_class(HG2ExportHelperPanel)
    bpy.utils.unregister_class(HG2SetupAttributesOperator)
    bpy.utils.unregister_class(HG2Exporter)
    bpy.types.TOPBAR_MT_file_export.remove(menu_file_export_hg2)

    # del bpy.types.Scene.my_text_props

if __name__ == "__main__":
    #unregister()
    register()

    # Test call.
    #bpy.ops.export_choroq.hg2('INVOKE_DEFAULT')


# Pseudo code to implement
# Take given objects
# For each object?
#   Create holders for mesh types
#   facesByColourGroup = {}
#   For each mesh do:
#    triangulate(mesh)
#    For each face do:
#      if face has attribute colourGroup
#        meshByColourGroup[face.attribytes[colourgroup]
#
#  for each in facesByColourGroup
#    Create pyffi mesh, adding all faces/points
#    Tristrip the mesh
#    store this for later use
#
#
#


# Set a face to be for a certain object
#bpy.ops.geometry.attribute_add(name="ObjectIndex", domain='FACE', data_type='INT') # for selected face
#bpy.ops.mesh.attribute_set(value_int=1) # For selected face and attribute

#bpy.context.selected_objects[0].data.attributes['ObjectIndex'].data.foreach_get('value', out)

