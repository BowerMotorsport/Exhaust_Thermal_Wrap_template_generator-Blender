"""
Pipe Flat Pattern Template Generator - Blender Addon
Generates exhaust wrap cutting templates from pipe specifications
"""

bl_info = {
    "name": "Pipe Flat Pattern Generator",
    "author": "Bower Motorsport",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Pipe Templates",
    "description": "Generate flat pattern templates for exhaust wrap from pipe specifications",
    "category": "Object",
}

import sys
import os

_addon_dir = os.path.dirname(os.path.abspath(__file__))
_lib_path = os.path.join(_addon_dir, "lib")
if _lib_path not in sys.path:
    sys.path.insert(0, _lib_path)

import bpy
import bmesh
import math
import json
import os
from bpy.props import FloatProperty, IntProperty, StringProperty, EnumProperty
from bpy.types import Panel, Operator, PropertyGroup

# ============================================================================
# Property Group - Stores user inputs
# ============================================================================


class PipeTemplateProperties(PropertyGroup):
    pipe_od: FloatProperty(
        name="Pipe OD",
        description="Pipe outer diameter in mm",
        default=76.2,
        min=10.0,
        max=500.0,
        unit="LENGTH",
    )

    bend_radius_multiplier: FloatProperty(
        name="Bend Radius (×D)",
        description="Bend centerline radius as multiple of diameter",
        default=1.5,
        min=0.5,
        max=10.0,
    )

    bend_angle: FloatProperty(
        name="Total Bend Angle (°)",
        description="Total bend angle in degrees",
        default=90.0,
        min=1.0,
        max=360.0,
    )

    num_segments: IntProperty(
        name="Number of Segments",
        description="How many segments to split the bend into",
        default=5,
        min=1,
        max=20,
    )

    wrap_thickness: FloatProperty(
        name="Wrap Thickness",
        description="Thickness of the wrap material in mm (fiberglass + stainless)",
        default=6.15,
        min=0.1,
        max=50.0,
    )

    overlap: FloatProperty(
        name="Tail Overlap",
        description="Overlap for seam and segment joins in mm",
        default=10.0,
        min=0.0,
        max=50.0,
    )

    output_folder: StringProperty(
        name="Output Folder",
        description="Folder to save generated PDF",
        default="./Pipe flat templates",
        subtype="DIR_PATH",
        maxlen=1024,
    )


# ============================================================================
# Operators
# ============================================================================


class PIPE_OT_GenerateTemplate(Operator):
    """Generate pipe flat pattern template"""

    bl_idname = "pipe.generate_template"
    bl_label = "Generate Template"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.pipe_template_props

        try:
            # Early validation - check output folder before expensive computations
            try:
                validated_path = self._validate_output_folder(props.output_folder)
                self.report({"INFO"}, f"Output directory: {validated_path}")
            except Exception as e:
                self.report({"ERROR"}, f"Output folder validation failed: {str(e)}")
                return {"CANCELLED"}

            # Step 1: Create 3D pipe segment in Blender
            self.report({"INFO"}, "Creating 3D pipe segment...")
            segment_obj = self.create_pipe_segment(props)

            # Step 2: UV unwrap
            self.report({"INFO"}, "UV unwrapping...")
            self.unwrap_pipe_segment(segment_obj, props)

            # Step 3: Export UV data
            self.report({"INFO"}, "Extracting UV data...")
            uv_data, boundary_data = self.extract_uv_data(segment_obj, props)

            # Step 4: Generate PDF
            self.report({"INFO"}, "Generating PDF...")
            self.generate_pdf(props, uv_data, boundary_data)

            self.report({"INFO"}, f"Template generated successfully!")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to generate template: {str(e)}")
            return {"CANCELLED"}

    def create_pipe_segment(self, props):
        """Create a 3D curved pipe segment"""
        # Ensure we're in object mode
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Clear existing PipeSegment objects using direct API
        for obj in list(bpy.data.objects):
            if obj.name == "PipeSegment" or obj.name.startswith("PipeSegment."):
                bpy.data.objects.remove(obj, do_unlink=True)

        # Calculate parameters
        bend_centerline_radius = props.pipe_od * props.bend_radius_multiplier
        pipe_radius = props.pipe_od / 2
        segment_angle = props.bend_angle / props.num_segments

        # Create one segment (0 to segment_angle degrees)
        start_rad = 0
        end_rad = math.radians(segment_angle)

        # Create mesh
        mesh = bpy.data.meshes.new("PipeSegment_mesh")
        obj = bpy.data.objects.new("PipeSegment", mesh)
        bpy.context.collection.objects.link(obj)

        bm = bmesh.new()

        # Resolution
        angular_resolution = 12  # Cross-sections along the curve
        radial_resolution = 32  # Vertices around the circle

        angle_step = (end_rad - start_rad) / angular_resolution
        all_rings = []

        for i in range(angular_resolution + 1):
            current_angle = start_rad + (i * angle_step)

            # Position along bend centerline
            center_x = bend_centerline_radius * math.cos(current_angle)
            center_y = bend_centerline_radius * math.sin(current_angle)

            # Tangent direction
            normal_x = math.cos(current_angle)
            normal_y = math.sin(current_angle)

            # Create circular cross-section
            ring_verts = []
            for j in range(radial_resolution):
                theta = (j / radial_resolution) * 2 * math.pi

                offset_normal = pipe_radius * math.cos(theta)
                offset_binormal = pipe_radius * math.sin(theta)

                vert_x = center_x + offset_normal * normal_x
                vert_y = center_y + offset_normal * normal_y
                vert_z = offset_binormal

                v = bm.verts.new((vert_x, vert_y, vert_z))
                ring_verts.append(v)

            all_rings.append(ring_verts)

        # Create faces
        for i in range(len(all_rings) - 1):
            ring1 = all_rings[i]
            ring2 = all_rings[i + 1]

            for j in range(radial_resolution):
                next_j = (j + 1) % radial_resolution
                v1 = ring1[j]
                v2 = ring1[next_j]
                v3 = ring2[next_j]
                v4 = ring2[j]
                bm.faces.new([v1, v2, v3, v4])

        bm.to_mesh(mesh)
        bm.free()

        # Smooth shading
        for face in mesh.polygons:
            face.use_smooth = True

        return obj

    def unwrap_pipe_segment(self, obj, props):
        """UV unwrap the pipe segment with seam on inside radius"""
        # Ensure we're in object mode first
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Deselect all objects using direct API
        for o in bpy.context.scene.objects:
            o.select_set(False)

        # Make active and select
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        mesh = obj.data

        # Find innermost angle (inside of bend)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.edges.ensure_lookup_table()

        # Clear seams
        for edge in bm.edges:
            edge.seam = False

        # Find minimum radius (closest to origin in XY plane)
        min_radius = float("inf")
        for v in bm.verts:
            radius = math.sqrt(v.co.x**2 + v.co.y**2)
            if radius < min_radius:
                min_radius = radius

        # Mark seam along ground plane (Z≈0) at minimum radius (closest to origin)
        z_tolerance = 0.5  # Tolerance for ground plane
        radius_tolerance = 1.0  # Tolerance for minimum radius

        for edge in bm.edges:
            v1, v2 = edge.verts

            # Check if both vertices are on ground plane (Z ≈ 0)
            if abs(v1.co.z) < z_tolerance and abs(v2.co.z) < z_tolerance:
                # Calculate radii (distance from origin in XY plane)
                r1 = math.sqrt(v1.co.x**2 + v1.co.y**2)
                r2 = math.sqrt(v2.co.x**2 + v2.co.y**2)

                # Check if both vertices are at minimum radius
                if (
                    abs(r1 - min_radius) < radius_tolerance
                    and abs(r2 - min_radius) < radius_tolerance
                ):
                    edge.seam = True

        bm.to_mesh(mesh)
        bm.free()

        # Unwrap
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)
        bpy.ops.object.mode_set(mode="OBJECT")

    def _validate_output_folder(self, folder_path):
        """Validate output folder path early to avoid wasting computation.

        Args:
            folder_path: Path string from StringProperty

        Returns:
            Normalized absolute path

        Raises:
            Exception: With descriptive error message if path invalid
        """
        import os
        import errno

        if not folder_path or folder_path.strip() == "":
            raise Exception("Output folder path is empty. Please select a folder.")

        # Normalize path
        normalized = os.path.normpath(folder_path)
        abs_path = os.path.abspath(normalized)

        # Check if parent directory exists (for creation)
        parent_dir = os.path.dirname(abs_path)
        if parent_dir and not os.path.exists(parent_dir):
            raise Exception(f"Parent directory does not exist: {parent_dir}")

        # Check if path is a file (not directory)
        if os.path.isfile(abs_path):
            raise Exception(f"Path is a file, not a directory: {abs_path}")

        # Check permissions (if directory exists)
        if os.path.exists(abs_path):
            if not os.access(abs_path, os.W_OK):
                raise Exception(f"Directory is not writable: {abs_path}")
        else:
            # Check if we can create directory (check parent permissions)
            if parent_dir and not os.access(parent_dir, os.W_OK):
                raise Exception(
                    f"Cannot create directory - parent is not writable: {parent_dir}"
                )

        return abs_path

    def extract_uv_data(self, obj, props):
        """Extract UV unwrap data for PDF generation"""
        mesh = obj.data
        uv_layer = mesh.uv_layers.active

        if not uv_layer:
            raise Exception("No UV layer found")

        # Collect UV coordinates
        polygons = []
        for poly in mesh.polygons:
            poly_uvs = []
            for loop_index in poly.loop_indices:
                uv = uv_layer.data[loop_index].uv
                poly_uvs.append([uv.x, uv.y])
            polygons.append(poly_uvs)

        # Find bounds
        all_uvs = [uv for poly in polygons for uv in poly]
        min_u = min(uv[0] for uv in all_uvs)
        max_u = max(uv[0] for uv in all_uvs)
        min_v = min(uv[1] for uv in all_uvs)
        max_v = max(uv[1] for uv in all_uvs)

        # Find boundary edges - keep track of both directions
        edge_count = {}
        edge_order = {}  # Keep original order
        for poly_uvs in polygons:
            num_verts = len(poly_uvs)
            for i in range(num_verts):
                v1 = tuple(poly_uvs[i])
                v2 = tuple(poly_uvs[(i + 1) % num_verts])
                edge_sorted = tuple(sorted([v1, v2]))
                edge_count[edge_sorted] = edge_count.get(edge_sorted, 0) + 1
                if edge_sorted not in edge_order:
                    edge_order[edge_sorted] = (v1, v2)  # Keep original direction

        # Get boundary edges with original direction
        boundary_edges = [
            [list(edge_order[edge][0]), list(edge_order[edge][1])]
            for edge, count in edge_count.items()
            if count == 1
        ]

        # Calculate dimensions
        bend_centerline_radius = props.pipe_od * props.bend_radius_multiplier
        segment_angle_rad = math.radians(props.bend_angle / props.num_segments)

        base_circ = math.pi * props.pipe_od
        base_arc = bend_centerline_radius * segment_angle_rad

        # Calculate wrap radius from pipe radius + wrap thickness
        pipe_radius = props.pipe_od / 2
        wrap_radius = pipe_radius + props.wrap_thickness

        wrap_circ = 2 * math.pi * wrap_radius
        wrap_width = wrap_circ + props.overlap
        wrap_distance = bend_centerline_radius + props.wrap_thickness
        wrap_arc = wrap_distance * segment_angle_rad

        uv_data = {
            "polygons": polygons,
            "min_u": min_u,
            "max_u": max_u,
            "min_v": min_v,
            "max_v": max_v,
            "pipe_circ_mm": base_circ,
            "pipe_arc_mm": base_arc,
            "wrap_width": wrap_width,
            "wrap_arc_length": wrap_arc,
            "overlap": props.overlap,
        }

        boundary_data = {
            "boundary_edges": boundary_edges,
            "min_u": min_u,
            "max_u": max_u,
            "min_v": min_v,
            "max_v": max_v,
        }

        return uv_data, boundary_data

    def _ensure_output_directory(self, folder_path):
        """Ensure output directory exists and is writable.

        Args:
            folder_path: Path to directory as string

        Returns:
            Normalized absolute path to directory

        Raises:
            Exception: If directory cannot be created or is not writable
        """
        import os
        import errno

        # Normalize path (handle ~, relative paths, etc.)
        normalized = os.path.normpath(folder_path)
        # Convert to absolute path relative to current working directory
        abs_path = os.path.abspath(normalized)

        # Check if it exists
        if not os.path.exists(abs_path):
            try:
                os.makedirs(abs_path, exist_ok=True)
                self.report({"INFO"}, f"Created output directory: {abs_path}")
            except OSError as e:
                if e.errno == errno.EACCES:
                    raise Exception(f"Permission denied creating directory: {abs_path}")
                elif e.errno == errno.ENOSPC:
                    raise Exception(f"Disk full creating directory: {abs_path}")
                else:
                    raise Exception(f"Failed to create directory {abs_path}: {str(e)}")

        # Check if directory is writable
        if not os.access(abs_path, os.W_OK):
            raise Exception(f"Directory is not writable: {abs_path}")

        return abs_path

    def generate_pdf(self, props, uv_data, boundary_data):
        """Generate PDF using reportlab"""
        import sys
        import site

        # Add user site-packages to path for reportlab
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.append(user_site)

        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.colors import HexColor, black, blue, red
        except ImportError:
            raise Exception("reportlab not installed. Run: pip install reportlab")

        # Extract data
        boundary_edges = boundary_data["boundary_edges"]
        min_u = boundary_data["min_u"]
        max_u = boundary_data["max_u"]
        min_v = boundary_data["min_v"]
        max_v = boundary_data["max_v"]

        base_w = uv_data["pipe_circ_mm"]
        base_h = uv_data["pipe_arc_mm"]
        wrap_w = uv_data["wrap_width"]
        wrap_h = uv_data["wrap_arc_length"]
        overlap = uv_data["overlap"]

        segment_angle = props.bend_angle / props.num_segments

        # PDF setup
        page_w, page_h = landscape(A4)
        margin = 6 * mm

        # Calculate available space
        # Reserve space for: title (30mm), legend (varies), scale bar (20mm), margins
        title_space = 30 * mm
        scale_space = 20 * mm
        legend_space = 30 * mm  # Minimum legend space
        available_width = page_w - 2 * margin
        available_height = page_h - title_space - scale_space - 2 * margin

        split_overlap = 20  # mm overlap for joining pages when splitting horizontally

        # Check if template needs to be split horizontally (too wide)
        needs_width_split = wrap_w > (available_width / mm)

        # Extract values
        od = props.pipe_od
        clr = props.bend_radius_multiplier  # centerline radius in mm
        segments = props.num_segments
        overlap = props.overlap
        mat_thickness = props.wrap_thickness

        # Build filename
        filename = (
            f"exhaust_wrap_OD{od:.1f}_CLR{clr:.1f}_S{segments}"
            f"_O{overlap:.1f}_MT{mat_thickness:.2f}.pdf"
        )

        # Ensure output directory exists and is writable
        output_dir = self._ensure_output_directory(props.output_folder)

        # Full path
        pdf_path = os.path.join(output_dir, filename)
        c = pdf_canvas.Canvas(pdf_path, pagesize=landscape(A4))

        if needs_width_split:
            # Template too wide - need to split into left/right halves
            # Try to fit both halves on same page vertically
            half_width = wrap_w / 2 + split_overlap
            template_spacing = 15 * mm
            total_height_needed = 2 * wrap_h * mm + template_spacing

            if total_height_needed <= available_height:
                # Both halves fit on same page
                self._generate_split_same_page(
                    c,
                    props,
                    boundary_edges,
                    min_u,
                    max_u,
                    min_v,
                    max_v,
                    base_w,
                    base_h,
                    wrap_w,
                    wrap_h,
                    overlap,
                    segment_angle,
                    split_overlap,
                    page_w,
                    page_h,
                    margin,
                    blue,
                    red,
                    black,
                )
            else:
                # Halves don't fit vertically - use separate pages
                self._generate_split_separate_pages(
                    c,
                    props,
                    boundary_edges,
                    min_u,
                    max_u,
                    min_v,
                    max_v,
                    base_w,
                    base_h,
                    wrap_w,
                    wrap_h,
                    overlap,
                    segment_angle,
                    split_overlap,
                    page_w,
                    page_h,
                    margin,
                    blue,
                    red,
                    black,
                )
        else:
            # Template fits width - check vertical space for two templates
            template_spacing = 15 * mm
            total_height_needed = 2 * wrap_h * mm + template_spacing

            if total_height_needed <= available_height:
                # Both templates fit on single page
                self._generate_single_page(
                    c,
                    props,
                    boundary_edges,
                    min_u,
                    max_u,
                    min_v,
                    max_v,
                    base_w,
                    base_h,
                    wrap_w,
                    wrap_h,
                    overlap,
                    segment_angle,
                    page_w,
                    page_h,
                    margin,
                    blue,
                    red,
                    black,
                )
            else:
                # Templates don't fit vertically - one per page
                self._generate_single_multipage(
                    c,
                    props,
                    boundary_edges,
                    min_u,
                    max_u,
                    min_v,
                    max_v,
                    base_w,
                    base_h,
                    wrap_w,
                    wrap_h,
                    overlap,
                    segment_angle,
                    page_w,
                    page_h,
                    margin,
                    blue,
                    red,
                    black,
                )

        c.save()
        self.report({"INFO"}, f"PDF saved to: {pdf_path}")

    def _generate_single_page(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        overlap,
        segment_angle,
        page_w,
        page_h,
        margin,
        blue,
        red,
        black,
    ):
        """Generate single page with two templates"""
        from reportlab.lib.units import mm

        # Two templates per page (top and bottom)
        template_positions = [
            (margin + 40 * mm, "TEMPLATE 1"),
            (margin + 40 * mm + wrap_h * mm + 15 * mm, "TEMPLATE 2"),
        ]

        # Title at top
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(
            page_w / 2, page_h - 15 * mm, "EXHAUST WRAP CUTTING TEMPLATE"
        )

        c.setFont("Helvetica", 10)
        c.drawCentredString(
            page_w / 2,
            page_h - 25 * mm,
            f"{props.pipe_od:.1f}mm OD | {props.bend_radius_multiplier:.1f}D {props.bend_angle:.0f}° Bend | {segment_angle:.1f}° per segment",
        )

        # Template Outlines legend - TOP LEFT
        legend_x = margin
        legend_y = page_h - 40 * mm

        c.setFont("Helvetica-Bold", 9)
        c.drawString(legend_x, legend_y, "TEMPLATE OUTLINES:")

        c.setStrokeColor(blue)
        c.setLineWidth(2)
        c.line(legend_x, legend_y - 10 * mm, legend_x + 20 * mm, legend_y - 10 * mm)
        c.setStrokeColor(black)
        c.setFont("Helvetica", 7)
        c.drawString(
            legend_x + 22 * mm,
            legend_y - 12 * mm,
            f"Base pipe: {base_w:.0f}×{base_h:.0f}mm",
        )

        c.setStrokeColor(red)
        c.setLineWidth(2)
        c.line(legend_x, legend_y - 20 * mm, legend_x + 20 * mm, legend_y - 20 * mm)
        c.setStrokeColor(black)
        c.drawString(
            legend_x + 22 * mm, legend_y - 22 * mm, f"Wrap: {wrap_w:.0f}×{wrap_h:.0f}mm"
        )

        c.setFont("Helvetica-Bold", 7)
        c.drawString(legend_x, legend_y - 33 * mm, "CUT TO RED OUTLINE:")
        c.setFont("Helvetica", 7)
        c.drawString(legend_x, legend_y - 41 * mm, f"{wrap_w:.0f} × {wrap_h:.0f} mm")
        c.drawString(legend_x, legend_y - 49 * mm, f"Qty: {props.num_segments} pieces")

        # Draw two templates
        for template_y, label in template_positions:
            template_x = (page_w - wrap_w * mm) / 2
            base_offset_x = (wrap_w - base_w) / 2
            base_offset_y = (wrap_h - base_h) / 2

            # Draw base pipe outline (blue)
            c.setStrokeColor(blue)
            c.setLineWidth(1.0)
            for edge in boundary_edges:
                v1, v2 = edge
                u1, v1_coord = v1
                u2, v2_coord = v2

                u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
                v1_norm = (
                    (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
                )
                u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
                v2_norm = (
                    (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
                )

                x1_mm = v1_norm * base_w
                y1_mm = u1_norm * base_h
                x2_mm = v2_norm * base_w
                y2_mm = u2_norm * base_h

                x1_pt = template_x + (base_offset_x + x1_mm) * mm
                y1_pt = template_y + (base_offset_y + y1_mm) * mm
                x2_pt = template_x + (base_offset_x + x2_mm) * mm
                y2_pt = template_y + (base_offset_y + y2_mm) * mm

                c.line(x1_pt, y1_pt, x2_pt, y2_pt)

            # Draw wrap layer outline (red)
            c.setStrokeColor(red)
            c.setLineWidth(2.0)
            for edge in boundary_edges:
                v1, v2 = edge
                u1, v1_coord = v1
                u2, v2_coord = v2

                u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
                v1_norm = (
                    (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
                )
                u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
                v2_norm = (
                    (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
                )

                x1_mm = v1_norm * wrap_w
                y1_mm = u1_norm * wrap_h
                x2_mm = v2_norm * wrap_w
                y2_mm = u2_norm * wrap_h

                x1_pt = template_x + x1_mm * mm
                y1_pt = template_y + y1_mm * mm
                x2_pt = template_x + x2_mm * mm
                y2_pt = template_y + y2_mm * mm

                c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        c.setStrokeColor(black)

        # Scale bar at bottom
        scale_x = margin
        scale_y = margin
        scale_len = 100 * mm

        c.setLineWidth(1.5)
        c.rect(scale_x, scale_y, scale_len, 10 * mm)
        c.setFillColor(black)
        c.rect(scale_x, scale_y, scale_len / 2, 10 * mm, fill=1, stroke=0)

        c.setLineWidth(1)
        c.line(scale_x, scale_y, scale_x, scale_y - 5 * mm)
        c.line(
            scale_x + scale_len / 2, scale_y, scale_x + scale_len / 2, scale_y - 5 * mm
        )
        c.line(scale_x + scale_len, scale_y, scale_x + scale_len, scale_y - 5 * mm)

        c.setFont("Helvetica", 8)
        c.drawString(scale_x, scale_y - 10 * mm, "0")
        c.drawString(scale_x + scale_len / 2 - 10 * mm, scale_y - 10 * mm, "50mm")
        c.drawString(scale_x + scale_len - 18 * mm, scale_y - 10 * mm, "100mm")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            scale_x + scale_len + 5 * mm,
            scale_y + 3 * mm,
            "← MUST MEASURE 100mm EXACTLY",
        )

        # Footer
        c.setFont("Helvetica", 7)
        c.drawString(
            margin,
            5 * mm,
            "Print: 100% scale | Landscape | A4 | Verify scale bar | Cut along RED outline",
        )

        c.showPage()

    def _generate_split_same_page(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        overlap,
        segment_angle,
        split_overlap,
        page_w,
        page_h,
        margin,
        blue,
        red,
        black,
    ):
        """Generate single page with both left and right halves"""
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor

        # Calculate split dimensions
        center_w = wrap_w / 2
        half_width = center_w + split_overlap

        # Position both halves vertically on the same page
        template_spacing = 15 * mm
        # Start lower to maximize space (user note: bottom wrap outline can sit lower)
        start_y = margin + 20 * mm  # Scale bar space

        half_positions = [
            (start_y, "LEFT HALF"),
            (start_y + wrap_h * mm + template_spacing, "RIGHT HALF"),
        ]

        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(
            page_w / 2, page_h - 15 * mm, "EXHAUST WRAP CUTTING TEMPLATE"
        )

        c.setFont("Helvetica", 10)
        c.drawCentredString(
            page_w / 2,
            page_h - 25 * mm,
            f"{props.pipe_od:.1f}mm OD | {props.bend_radius_multiplier:.1f}D {props.bend_angle:.0f}° Bend | {segment_angle:.1f}° per segment",
        )

        # Instructions
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(HexColor("#CC0000"))
        c.drawCentredString(
            page_w / 2,
            page_h - 35 * mm,
            "JOIN LEFT AND RIGHT HALVES AT GREEN CENTERLINE",
        )
        c.setFillColor(black)

        # Legend - compact version
        legend_x = margin
        legend_y = page_h - 50 * mm

        c.setFont("Helvetica-Bold", 8)
        c.drawString(legend_x, legend_y, f"FULL SIZE: {wrap_w:.0f}mm × {wrap_h:.0f}mm")
        c.setFont("Helvetica", 7)
        c.drawString(
            legend_x,
            legend_y - 8 * mm,
            f"Each half: {half_width:.0f}mm × {wrap_h:.0f}mm",
        )

        # Draw both halves
        for template_y, label in half_positions:
            is_left = label == "LEFT HALF"
            x_start = 0 if is_left else (center_w - split_overlap)
            x_end = (center_w + split_overlap) if is_left else wrap_w

            self._draw_split_half(
                c,
                props,
                boundary_edges,
                min_u,
                max_u,
                min_v,
                max_v,
                base_w,
                base_h,
                wrap_w,
                wrap_h,
                x_start,
                x_end,
                center_w,
                split_overlap,
                template_y,
                label,
                page_w,
                half_width,
                margin,
                blue,
                red,
                black,
                is_left,
            )

        # Scale bar
        scale_x = margin
        scale_y = margin
        scale_len = 100 * mm

        c.setStrokeColor(black)
        c.setLineWidth(1.5)
        c.rect(scale_x, scale_y, scale_len, 10 * mm)
        c.setFillColor(black)
        c.rect(scale_x, scale_y, scale_len / 2, 10 * mm, fill=1, stroke=0)

        c.setLineWidth(1)
        c.line(scale_x, scale_y, scale_x, scale_y - 5 * mm)
        c.line(
            scale_x + scale_len / 2, scale_y, scale_x + scale_len / 2, scale_y - 5 * mm
        )
        c.line(scale_x + scale_len, scale_y, scale_x + scale_len, scale_y - 5 * mm)

        c.setFont("Helvetica", 8)
        c.drawString(scale_x, scale_y - 10 * mm, "0")
        c.drawString(scale_x + scale_len / 2 - 10 * mm, scale_y - 10 * mm, "50mm")
        c.drawString(scale_x + scale_len - 18 * mm, scale_y - 10 * mm, "100mm")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            scale_x + scale_len + 5 * mm,
            scale_y + 3 * mm,
            "← MUST MEASURE 100mm EXACTLY",
        )

        # Footer
        c.setFont("Helvetica", 7)
        c.drawString(
            margin,
            5 * mm,
            "Print: 100% scale | Landscape | A4 | Join halves at GREEN centerline | Cut RED outline",
        )

        c.showPage()

    def _generate_split_separate_pages(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        overlap,
        segment_angle,
        split_overlap,
        page_w,
        page_h,
        margin,
        blue,
        red,
        black,
    ):
        """Generate separate pages when template is too wide and too tall"""
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor

        # Calculate split point and widths
        center_w = wrap_w / 2
        left_width = center_w + split_overlap
        right_width = center_w + split_overlap

        # PAGE 1: Left half (0 to center + overlap)
        self._draw_split_page(
            c,
            props,
            boundary_edges,
            min_u,
            max_u,
            min_v,
            max_v,
            base_w,
            base_h,
            wrap_w,
            wrap_h,
            overlap,
            segment_angle,
            0,
            left_width,
            center_w,
            split_overlap,
            "LEFT HALF (1 of 2)",
            page_w,
            page_h,
            margin,
            blue,
            red,
            black,
            True,
        )

        # PAGE 2: Right half (center - overlap to end)
        self._draw_split_page(
            c,
            props,
            boundary_edges,
            min_u,
            max_u,
            min_v,
            max_v,
            base_w,
            base_h,
            wrap_w,
            wrap_h,
            overlap,
            segment_angle,
            center_w - split_overlap,
            wrap_w,
            center_w,
            split_overlap,
            "RIGHT HALF (2 of 2)",
            page_w,
            page_h,
            margin,
            blue,
            red,
            black,
            False,
        )

    def _draw_split_half(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        x_start,
        x_end,
        center_w,
        split_overlap,
        template_y,
        label,
        page_w,
        half_width,
        margin,
        blue,
        red,
        black,
        is_left,
    ):
        """Draw one half of a split template"""
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor

        # Calculate template position (centered horizontally)
        template_x = (page_w - half_width * mm) / 2
        base_offset_x = (wrap_w - base_w) / 2
        base_offset_y = (wrap_h - base_h) / 2

        # Draw label
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(HexColor("#666666"))
        c.drawString(template_x, template_y + wrap_h * mm + 2 * mm, label)
        c.setFillColor(black)

        # Draw base pipe outline (blue) - clipped to section
        c.setStrokeColor(blue)
        c.setLineWidth(1.0)

        for edge in boundary_edges:
            v1, v2 = edge
            u1, v1_coord = v1
            u2, v2_coord = v2

            u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v1_norm = (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
            u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v2_norm = (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0

            x1_mm = v1_norm * base_w + base_offset_x
            y1_mm = u1_norm * base_h + base_offset_y
            x2_mm = v2_norm * base_w + base_offset_x
            y2_mm = u2_norm * base_h + base_offset_y

            # Clip to section
            if (
                x_start <= x1_mm <= x_end
                or x_start <= x2_mm <= x_end
                or (x1_mm < x_start and x2_mm > x_end)
                or (x2_mm < x_start and x1_mm > x_end)
            ):
                x1_pt = template_x + (x1_mm - x_start) * mm
                y1_pt = template_y + y1_mm * mm
                x2_pt = template_x + (x2_mm - x_start) * mm
                y2_pt = template_y + y2_mm * mm
                c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        # Draw wrap layer outline (red) - clipped to section
        c.setStrokeColor(red)
        c.setLineWidth(2.0)

        for edge in boundary_edges:
            v1, v2 = edge
            u1, v1_coord = v1
            u2, v2_coord = v2

            u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v1_norm = (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
            u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v2_norm = (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0

            x1_mm = v1_norm * wrap_w
            y1_mm = u1_norm * wrap_h
            x2_mm = v2_norm * wrap_w
            y2_mm = u2_norm * wrap_h

            # Clip to section
            if (
                x_start <= x1_mm <= x_end
                or x_start <= x2_mm <= x_end
                or (x1_mm < x_start and x2_mm > x_end)
                or (x2_mm < x_start and x1_mm > x_end)
            ):
                x1_pt = template_x + (x1_mm - x_start) * mm
                y1_pt = template_y + y1_mm * mm
                x2_pt = template_x + (x2_mm - x_start) * mm
                y2_pt = template_y + y2_mm * mm
                c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        # Draw centerline (green dashed)
        centerline_x = template_x + (center_w - x_start) * mm
        c.setStrokeColor(HexColor("#00AA00"))
        c.setLineWidth(1.5)
        c.setDash(5, 3)
        c.line(centerline_x, template_y, centerline_x, template_y + wrap_h * mm)
        c.setDash()  # Reset to solid

        # Draw overlap zone marker
        c.setStrokeColor(HexColor("#FFA500"))
        c.setLineWidth(0.5)
        if is_left:
            # Mark right edge overlap zone
            overlap_x = template_x + (center_w + split_overlap - x_start) * mm
            c.rect(
                overlap_x - split_overlap * mm,
                template_y,
                split_overlap * mm,
                wrap_h * mm,
            )
        else:
            # Mark left edge overlap zone
            overlap_x = template_x
            c.rect(overlap_x, template_y, split_overlap * mm, wrap_h * mm)

        c.setStrokeColor(black)

    def _generate_single_multipage(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        overlap,
        segment_angle,
        page_w,
        page_h,
        margin,
        blue,
        red,
        black,
    ):
        """Generate multiple pages when single template is too tall vertically"""
        from reportlab.lib.units import mm

        # One template per page
        self._draw_single_template_page(
            c,
            props,
            boundary_edges,
            min_u,
            max_u,
            min_v,
            max_v,
            base_w,
            base_h,
            wrap_w,
            wrap_h,
            overlap,
            segment_angle,
            page_w,
            page_h,
            margin,
            blue,
            red,
            black,
            "TEMPLATE 1/2",
        )

        self._draw_single_template_page(
            c,
            props,
            boundary_edges,
            min_u,
            max_u,
            min_v,
            max_v,
            base_w,
            base_h,
            wrap_w,
            wrap_h,
            overlap,
            segment_angle,
            page_w,
            page_h,
            margin,
            blue,
            red,
            black,
            "TEMPLATE 2/2",
        )

    def _draw_single_template_page(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        overlap,
        segment_angle,
        page_w,
        page_h,
        margin,
        blue,
        red,
        black,
        page_label,
    ):
        """Draw a single template on its own page"""
        from reportlab.lib.units import mm

        # Center template vertically with more space at bottom
        template_y = (page_h - wrap_h * mm) / 2 - 10 * mm  # Shift down slightly
        template_x = (page_w - wrap_w * mm) / 2
        base_offset_x = (wrap_w - base_w) / 2
        base_offset_y = (wrap_h - base_h) / 2

        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(
            page_w / 2, page_h - 15 * mm, "EXHAUST WRAP CUTTING TEMPLATE"
        )

        c.setFont("Helvetica", 10)
        c.drawCentredString(
            page_w / 2,
            page_h - 25 * mm,
            f"{props.pipe_od:.1f}mm OD | {props.bend_radius_multiplier:.1f}D {props.bend_angle:.0f}° Bend | {segment_angle:.1f}° per segment",
        )

        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(page_w / 2, page_h - 35 * mm, page_label)

        # Legend
        legend_x = margin
        legend_y = page_h - 50 * mm

        c.setFont("Helvetica-Bold", 9)
        c.drawString(legend_x, legend_y, "TEMPLATE OUTLINES:")

        c.setStrokeColor(blue)
        c.setLineWidth(2)
        c.line(legend_x, legend_y - 10 * mm, legend_x + 20 * mm, legend_y - 10 * mm)
        c.setStrokeColor(black)
        c.setFont("Helvetica", 7)
        c.drawString(
            legend_x + 22 * mm,
            legend_y - 12 * mm,
            f"Base pipe: {base_w:.0f}×{base_h:.0f}mm",
        )

        c.setStrokeColor(red)
        c.setLineWidth(2)
        c.line(legend_x, legend_y - 20 * mm, legend_x + 20 * mm, legend_y - 20 * mm)
        c.setStrokeColor(black)
        c.drawString(
            legend_x + 22 * mm, legend_y - 22 * mm, f"Wrap: {wrap_w:.0f}×{wrap_h:.0f}mm"
        )

        c.setFont("Helvetica-Bold", 7)
        c.drawString(legend_x, legend_y - 33 * mm, "CUT TO RED OUTLINE:")
        c.setFont("Helvetica", 7)
        c.drawString(legend_x, legend_y - 41 * mm, f"{wrap_w:.0f} × {wrap_h:.0f} mm")
        c.drawString(legend_x, legend_y - 49 * mm, f"Qty: {props.num_segments} pieces")

        # Draw base pipe outline (blue)
        c.setStrokeColor(blue)
        c.setLineWidth(1.0)
        for edge in boundary_edges:
            v1, v2 = edge
            u1, v1_coord = v1
            u2, v2_coord = v2

            u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v1_norm = (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
            u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v2_norm = (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0

            x1_mm = v1_norm * base_w
            y1_mm = u1_norm * base_h
            x2_mm = v2_norm * base_w
            y2_mm = u2_norm * base_h

            x1_pt = template_x + (base_offset_x + x1_mm) * mm
            y1_pt = template_y + (base_offset_y + y1_mm) * mm
            x2_pt = template_x + (base_offset_x + x2_mm) * mm
            y2_pt = template_y + (base_offset_y + y2_mm) * mm

            c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        # Draw wrap layer outline (red)
        c.setStrokeColor(red)
        c.setLineWidth(2.0)
        for edge in boundary_edges:
            v1, v2 = edge
            u1, v1_coord = v1
            u2, v2_coord = v2

            u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v1_norm = (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
            u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v2_norm = (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0

            x1_mm = v1_norm * wrap_w
            y1_mm = u1_norm * wrap_h
            x2_mm = v2_norm * wrap_w
            y2_mm = u2_norm * wrap_h

            x1_pt = template_x + x1_mm * mm
            y1_pt = template_y + y1_mm * mm
            x2_pt = template_x + x2_mm * mm
            y2_pt = template_y + y2_mm * mm

            c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        c.setStrokeColor(black)

        # Scale bar
        scale_x = margin
        scale_y = margin
        scale_len = 100 * mm

        c.setLineWidth(1.5)
        c.rect(scale_x, scale_y, scale_len, 10 * mm)
        c.setFillColor(black)
        c.rect(scale_x, scale_y, scale_len / 2, 10 * mm, fill=1, stroke=0)

        c.setLineWidth(1)
        c.line(scale_x, scale_y, scale_x, scale_y - 5 * mm)
        c.line(
            scale_x + scale_len / 2, scale_y, scale_x + scale_len / 2, scale_y - 5 * mm
        )
        c.line(scale_x + scale_len, scale_y, scale_x + scale_len, scale_y - 5 * mm)

        c.setFont("Helvetica", 8)
        c.drawString(scale_x, scale_y - 10 * mm, "0")
        c.drawString(scale_x + scale_len / 2 - 10 * mm, scale_y - 10 * mm, "50mm")
        c.drawString(scale_x + scale_len - 18 * mm, scale_y - 10 * mm, "100mm")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            scale_x + scale_len + 5 * mm,
            scale_y + 3 * mm,
            "← MUST MEASURE 100mm EXACTLY",
        )

        # Footer
        c.setFont("Helvetica", 7)
        c.drawString(
            margin,
            5 * mm,
            "Print: 100% scale | Landscape | A4 | Verify scale bar | Cut along RED outline",
        )

        c.showPage()

    def _draw_split_page(
        self,
        c,
        props,
        boundary_edges,
        min_u,
        max_u,
        min_v,
        max_v,
        base_w,
        base_h,
        wrap_w,
        wrap_h,
        overlap,
        segment_angle,
        x_start,
        x_end,
        center_w,
        split_overlap,
        page_label,
        page_w,
        page_h,
        margin,
        blue,
        red,
        black,
        is_left,
    ):
        """Draw one page of a split template"""
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor

        section_width = x_end - x_start
        template_y = page_h / 2 - (wrap_h * mm) / 2

        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(
            page_w / 2, page_h - 15 * mm, "EXHAUST WRAP CUTTING TEMPLATE"
        )

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(HexColor("#CC0000"))
        c.drawCentredString(page_w / 2, page_h - 28 * mm, page_label)
        c.setFillColor(black)

        c.setFont("Helvetica", 10)
        c.drawCentredString(
            page_w / 2,
            page_h - 40 * mm,
            f"{props.pipe_od:.1f}mm OD | {props.bend_radius_multiplier:.1f}D {props.bend_angle:.0f}° Bend | {segment_angle:.1f}° per segment",
        )

        # Legend
        legend_x = margin
        legend_y = page_h - 55 * mm

        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            legend_x, legend_y, f"TEMPLATE SIZE: {wrap_w:.0f}mm × {wrap_h:.0f}mm (FULL)"
        )
        c.setFont("Helvetica", 8)
        c.drawString(
            legend_x,
            legend_y - 10 * mm,
            f"This section: {section_width:.0f}mm × {wrap_h:.0f}mm",
        )
        c.drawString(legend_x, legend_y - 18 * mm, f"Overlap zone: {split_overlap}mm")

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(HexColor("#CC0000"))
        c.drawString(
            legend_x, legend_y - 30 * mm, "JOIN PAGES AT CENTERLINE (dashed green)"
        )
        c.setFillColor(black)

        # Calculate template position (centered)
        template_x = (page_w - section_width * mm) / 2

        # Draw base pipe outline (blue) - clipped to section
        c.setStrokeColor(blue)
        c.setLineWidth(1.0)
        base_offset_x = (wrap_w - base_w) / 2
        base_offset_y = (wrap_h - base_h) / 2

        for edge in boundary_edges:
            v1, v2 = edge
            u1, v1_coord = v1
            u2, v2_coord = v2

            u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v1_norm = (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
            u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v2_norm = (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0

            x1_mm = v1_norm * base_w + base_offset_x
            y1_mm = u1_norm * base_h + base_offset_y
            x2_mm = v2_norm * base_w + base_offset_x
            y2_mm = u2_norm * base_h + base_offset_y

            # Clip to section
            if (
                x_start <= x1_mm <= x_end
                or x_start <= x2_mm <= x_end
                or (x1_mm < x_start and x2_mm > x_end)
                or (x2_mm < x_start and x1_mm > x_end)
            ):
                x1_pt = template_x + (x1_mm - x_start) * mm
                y1_pt = template_y + y1_mm * mm
                x2_pt = template_x + (x2_mm - x_start) * mm
                y2_pt = template_y + y2_mm * mm
                c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        # Draw wrap layer outline (red) - clipped to section
        c.setStrokeColor(red)
        c.setLineWidth(2.0)

        for edge in boundary_edges:
            v1, v2 = edge
            u1, v1_coord = v1
            u2, v2_coord = v2

            u1_norm = (u1 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v1_norm = (v1_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0
            u2_norm = (u2 - min_u) / (max_u - min_u) if (max_u - min_u) > 0 else 0
            v2_norm = (v2_coord - min_v) / (max_v - min_v) if (max_v - min_v) > 0 else 0

            x1_mm = v1_norm * wrap_w
            y1_mm = u1_norm * wrap_h
            x2_mm = v2_norm * wrap_w
            y2_mm = u2_norm * wrap_h

            # Clip to section
            if (
                x_start <= x1_mm <= x_end
                or x_start <= x2_mm <= x_end
                or (x1_mm < x_start and x2_mm > x_end)
                or (x2_mm < x_start and x1_mm > x_end)
            ):
                x1_pt = template_x + (x1_mm - x_start) * mm
                y1_pt = template_y + y1_mm * mm
                x2_pt = template_x + (x2_mm - x_start) * mm
                y2_pt = template_y + y2_mm * mm
                c.line(x1_pt, y1_pt, x2_pt, y2_pt)

        # Draw centerline (green dashed)
        centerline_x = template_x + (center_w - x_start) * mm
        c.setStrokeColor(HexColor("#00AA00"))
        c.setLineWidth(1.5)
        c.setDash(5, 3)
        c.line(centerline_x, template_y, centerline_x, template_y + wrap_h * mm)
        c.setDash()  # Reset to solid

        # Centerline label
        c.setFillColor(HexColor("#00AA00"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(
            centerline_x + 2 * mm, template_y + wrap_h * mm + 2 * mm, "CENTERLINE"
        )
        c.setFillColor(black)

        # Draw overlap zone markers
        c.setStrokeColor(HexColor("#FFA500"))
        c.setLineWidth(0.5)
        if is_left:
            # Mark right edge overlap zone
            overlap_x = template_x + (center_w + split_overlap - x_start) * mm
            c.rect(
                overlap_x - split_overlap * mm,
                template_y,
                split_overlap * mm,
                wrap_h * mm,
            )
            c.setFont("Helvetica", 6)
            c.drawString(
                overlap_x - split_overlap * mm / 2 - 8 * mm,
                template_y - 5 * mm,
                f"{split_overlap}mm overlap",
            )
        else:
            # Mark left edge overlap zone
            overlap_x = template_x
            c.rect(overlap_x, template_y, split_overlap * mm, wrap_h * mm)
            c.setFont("Helvetica", 6)
            c.drawString(
                overlap_x + split_overlap * mm / 2 - 8 * mm,
                template_y - 5 * mm,
                f"{split_overlap}mm overlap",
            )

        c.setStrokeColor(black)

        # Scale bar
        scale_x = margin
        scale_y = margin
        scale_len = 100 * mm

        c.setLineWidth(1.5)
        c.rect(scale_x, scale_y, scale_len, 10 * mm)
        c.setFillColor(black)
        c.rect(scale_x, scale_y, scale_len / 2, 10 * mm, fill=1, stroke=0)

        c.setLineWidth(1)
        c.line(scale_x, scale_y, scale_x, scale_y - 5 * mm)
        c.line(
            scale_x + scale_len / 2, scale_y, scale_x + scale_len / 2, scale_y - 5 * mm
        )
        c.line(scale_x + scale_len, scale_y, scale_x + scale_len, scale_y - 5 * mm)

        c.setFont("Helvetica", 8)
        c.drawString(scale_x, scale_y - 10 * mm, "0")
        c.drawString(scale_x + scale_len / 2 - 10 * mm, scale_y - 10 * mm, "50mm")
        c.drawString(scale_x + scale_len - 18 * mm, scale_y - 10 * mm, "100mm")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            scale_x + scale_len + 5 * mm,
            scale_y + 3 * mm,
            "← MUST MEASURE 100mm EXACTLY",
        )

        # Footer
        c.setFont("Helvetica", 7)
        c.drawString(
            margin,
            5 * mm,
            f"Print: 100% scale | Landscape | A4 | {page_label} | Join at GREEN centerline",
        )

        c.showPage()


# ============================================================================
# Panel
# ============================================================================


class PIPE_PT_TemplatePanel(Panel):
    """Panel in 3D viewport sidebar"""

    bl_label = "Pipe Template Generator"
    bl_idname = "PIPE_PT_template_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pipe Templates"

    def draw(self, context):
        layout = self.layout
        props = context.scene.pipe_template_props

        # Pipe specifications
        box = layout.box()
        box.label(text="Pipe Specifications:", icon="MESH_CYLINDER")
        box.prop(props, "pipe_od")
        box.prop(props, "bend_radius_multiplier")
        box.prop(props, "bend_angle")
        box.prop(props, "num_segments")

        # Wrap layer
        box = layout.box()
        box.label(text="Wrap Layer:", icon="MOD_CLOTH")
        box.prop(props, "wrap_thickness")
        box.prop(props, "overlap")

        # Output
        box = layout.box()
        box.label(text="Output:", icon="FILE_FOLDER")
        box.prop(props, "output_folder")

        # Generate button
        layout.separator()
        layout.operator(
            "pipe.generate_template", text="Generate Template", icon="FILE_NEW"
        )


# ============================================================================
# Registration
# ============================================================================

classes = (
    PipeTemplateProperties,
    PIPE_OT_GenerateTemplate,
    PIPE_PT_TemplatePanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pipe_template_props = bpy.props.PointerProperty(
        type=PipeTemplateProperties
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.pipe_template_props


if __name__ == "__main__":
    register()
