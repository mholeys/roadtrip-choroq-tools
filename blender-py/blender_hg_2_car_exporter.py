import bpy
import bmesh
import struct

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

def write_some_data(context, filepath, export_format):
    #export format: OPT_EXPORT_WHOLE or OPT_EXPORT_SUBPART
    #print("running write_some_data...")
    

    
    
    
    if export_format == "OPT_EXPORT_SUBPART":
        if len(bpy.context.selected_objects) > 3:
            raise Exception("Cannot export, subsection must have at max 3 parts")
        f = open(filepath, "wb")
        # Loop through selected objects as parts
        part_index = 0
        section_index = 0
        sizes = [0]
        paddings = []
        # Work through each selected object, convert to triangles and calculate size
        for obj in bpy.context.selected_objects:
            print(f"[{obj.name}] as Section: {section_index} Part: {part_index}")
            #dump(obj)
            #print(".data:")
            #dump(obj.data)

            if obj.id_type != 'OBJECT' or obj.data.id_type != 'MESH':
                print("Skipping obj as not mesh")
                continue
            mesh = obj.data
            triangulate_object(obj)    
            
            # Estimate size of object
            # Each subsection will have parts
            # Each subsection will have a offset table (16 bytes, 2 longs, 2 shorts)
            # Each object will be 1 part
            # Each part will have DMa tag + zero word, with VIF setup tags (STCYCL) and VIF copy tag (16 bytes)
            # Each face will have a VIF expand tag
            # Each face will also have GIF tag (16 bytes)
            # Each face will have x/y/z*3 nx/ny/z*3 r/g/b*3 uv.u/uv.v/0*3 (144 bytes)
            # Each face will also have Exec call (4 bytes)
            # Each Part will have a end dma tag (16 bytes)
            
            dma_tag_size = 4
            zero_pad_dma_size = 4
            vif_tag_size = 4
            gif_tag_size = 16 # for cars
            # coords * 3 for each triangle * 4 = bytes
            verts_bytes_face = 12 * 3 * 4
            vif_exec_size = 4
            end_dma_tag_size = 16
            
            face_count = len(mesh.polygons)
            
            part_header_size = dma_tag_size + zero_pad_dma_size + vif_tag_size
            mesh_size = face_count * (vif_tag_size + gif_tag_size + vif_tag_size + verts_bytes_face + vif_exec_size)
            # VIF here is set cycle tag
            total_size = part_header_size + mesh_size
            
            # Total size of this part (1 part of subsection)
            # Fix size to be padded to end on 16 boundary, to align dma tags (end dma tag)
            padding = 0
            if total_size % 16 != 0:
                padding = 16 - (total_size % 16)
            total_size += end_dma_tag_size
            sizes.append(total_size)
            paddings.append(padding)
            part_index += 1
            
        # Write offset table for subsection
        # offset 0 = 16 is implicit
        print(sizes)
        sizes[0] = 16
        # Force alignment to 16byte boundary (needed for dma I think)
        positions = [16, 16+sizes[1]+paddings[0], 16+sizes[1]+sizes[2]+paddings[0]+paddings[1]]
        
        f.write(positions[1].to_bytes(4, byteorder='little'))
        f.write(positions[2].to_bytes(4, byteorder='little'))
        
        value1 = 0
        value2 = 0
        f.write(value1.to_bytes(4, byteorder='little')) # Unsure on this value so far, some parts are 0
        f.write(value2.to_bytes(4, byteorder='little')) # Unsure on this value so far, others are not
        
        # Now loop back over each part, to export the data
        part_index = 0
        section_index = 0
        positions[0] = 16
         # For checking position
        for obj in bpy.context.selected_objects:
            
            print(f"[{obj.name}] as Section: {section_index} Part: {part_index}")
            #dump(obj)
            #print(".data:")
            #dump(obj.data)

            if obj.id_type != 'OBJECT' or obj.data.id_type != 'MESH':
                print("Skipping obj as not mesh")
                continue
            mesh = obj.data
            
            # Check position in file, we should know where we are at all points
            if f.tell() != positions[part_index]:
                print(f"File position incorrect {f.tell()} vs positions[{part_index}] = {positions[part_index]}")
                break
            
            # Check if the mesh has valid color and uv arrays
            # if not create them, and populate with 0s

            #bpy.ops.uv.unwrap()
            #uv_layer = mesh1.uv_layers.new()        
            #mesh1.uv_layers.active = uv_layer
            
            # Check for colour attibutes
            if not mesh.color_attributes or len(mesh.color_attributes) == 0:
                mesh.color_attributes.new("Color", 'BYTE_COLOR', 'CORNER')
            #dump(mesh.attributes.active_color)
            
            print(mesh.uv_layers)
            if not mesh.uv_layers or len(mesh.uv_layers) == 0:
                mesh.uv_layers.active = mesh.uv_layers.new()
            #dump(mesh.uv_layers.active)
            
            # Now we know the mesh has x/y/z nx/ny/nz r/g/b/a and uv

            # Write DMA tag
            dma_tag_suffix = [0x00, 0x10]
            size_padding = 16 - (sizes[part_index+1] % 16)
            if size_padding == 16:
                size_padding = 0
            dma_tag_size = int((sizes[part_index+1] - 16) / 16) 
            #print(sizes[part_index+1])
            #print(size_padding)
            #print(dma_tag_size)
            f.write(dma_tag_size.to_bytes(2, 'little'))
            f.write(bytes(dma_tag_suffix))
            
            # Write zero word
            f.write(bytes([0x00, 0x00, 0x00, 0x00]))
            
            # Write STCYCL VIF tag
            f.write(bytes([0x01, 0x01, 0x00, 0x01]))
                        
            # Write mesh data
            # Loop over all faces to extract data in face groups
            for face in mesh.polygons:
                #print('face')
                #dump(face)
                
                # Write VIF V4-32 tag, this just copies the GIF tag to the VIF for later use, so is always this
                f.write(bytes([0x00, 0x80, 0x01, 0x6C]))
                
                # Write GIF tag (to say what we are sending) (always same for cars AFAIK)
                # e.g 3 verts = 03 80 00 00 00 40 36 31 12 04 00 00 00 00 00 00
                vert_count = 3
                gif_tag = [vert_count, 0x80, 0x00, 0x00,
                            0x02, 0x40, 0x36, 0x31, # First byte on this row, changes 0 for first 2 for rest
                            0x12, 0x04, 0x00, 0x00, 
                            0x01, 0x00, 0x00, 0x00] # First byte on this row, changes 0 or 1 or 2 ? 
                f.write(bytes(gif_tag))
                
                # Write VIF expand tag
                vif_expand_count = 12
                vif_tag = [0x01, 0x80, vif_expand_count, 0x68]
                f.write(bytes(vif_tag))
                
                for vert_index in face.vertices:
                    x, y, z = mesh.vertices[vert_index].co
                    nx, ny, nz = mesh.vertices[vert_index].normal
                    r,g,b,a = mesh.attributes.active_color.data[vert_index].color
                    u, v = mesh.uv_layers.active.data[vert_index].uv
                    #dump(mesh.vertices[vert_index])
                    
                    #print(f"x {x} y {y} z {z}")
                    #print(f"nx {nx} ny {ny} nz {nz}")
                    #print(f"r {r} g {g} b {b} a {a}")
                    #print(f"u {u} v {v}")
                    
                    vert_out = struct.pack('ffffffffffff', x, y, z, nx, ny, nz, r*255, g*255, b*255, u, 1-v, 280.5)
                    f.write(vert_out)
                    
                    # Create tags, and data for this face, and write
            
                # Write Exec VIF tag
                if part_index == 0:                
                    exec_call = [0x04, 0x00, 0x00, 0x15]
                else:
                    exec_call = [0x0A, 0x00, 0x00, 0x15]
                f.write(bytes(exec_call))
            
            
            # Pad file so end dma is 16 aligned
            print(paddings[part_index])
            print(paddings)
            for i in range(paddings[part_index]):
                f.write(bytes([0x00]))
            
            # Write end dma tag, for this part
            end_dma_tag = bytes([00, 00, 00, 0x60, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00, 00])
            f.write(end_dma_tag)
            
            part_index += 1
                    
                    


                    
                    
        # Close file
        f.close()
                    
#            float = "Opacity"
#            obj[float] = (1.0)
#            obj.id_properties_ensure()
#            property_manager = obj.id_properties_ui(float)
#            property_manager.update( 
#            default=1.0,
#                min=0.0,
#                max=1.0,
#                subtype="FACTOR",
#                precision=2
#            )

    if export_format == "OPT_EXPORT_SUBPART":
        pass



    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_choroq.hg2"  # Important since its how bpy.ops.import_test.some_data is constructed.
    bl_label = "Export CHOROQ HG2"

    # ExportHelper mix-in class uses this.
    filename_ext = ".BIN"

    filter_glob: StringProperty(
        default="*.BIN",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    type: EnumProperty(
        name="Export type",
        description="Whole car would use selected for all parts (not working). Subsection will use selected as one part, with 3 subparts",
        items=(
            ('OPT_EXPORT_WHOLE', "Whole Car", "Creates whole car BIN (future)"),
            ('OPT_EXPORT_SUBPART', "1 Part", "Uses selected for car parts, multiple sections"),
        ),
        default='OPT_EXPORT_SUBPART',
    )

    def execute(self, context):
        return write_some_data(context, self.filepath, self.type)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportSomeData.bl_idname, text="Choroq Car exporter (HG2)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # Test call.
    bpy.ops.export_choroq.hg2('INVOKE_DEFAULT')
