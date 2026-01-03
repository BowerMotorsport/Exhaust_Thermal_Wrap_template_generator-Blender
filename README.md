![BowerMotorsport Logo](Readme_Images/LogoV1_White_Backed_150dpi.png)
<div style="display:flex; gap:10px; align-items:flex-start;">
  <img src="Readme_Images/Demo_Images_1.png" height="400">
  <img src="Readme_Images/Example_Template.png" height="400">
</div>

## 🏁 Connect With Me

[![Facebook](https://img.shields.io/badge/Facebook-1877F2?style=for-the-badge&logo=facebook&logoColor=white)](https://www.facebook.com/BowerMotorsport)
[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/bower_motorsport/)

*Educational content about motorsport topics, with a focus on the niche and technical side of motorsport engineering.

---
# Exhaust Thermal Wrap Template Generator | Blender

A Blender addon that generates accurate flat pattern cutting templates for pipe wrapping materials. Create professional PDF templates for any pipe specification with a simple GUI interface.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Blender](https://img.shields.io/badge/blender-3.0%2B-orange)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🎯 **Any Pipe Specification**: Works with any pipe diameter, bend radius, angle, and segment count
- 🖱️ **Easy GUI Interface**: Simple sidebar panel in Blender - no scripting required
- 📐 **Accurate UV Unwrapping**: Uses Blender's 3D geometry for precise flat patterns
- 📄 **Professional PDFs**: Generates print-ready templates with scale bars and dimensions
- ⚡ **Fast Generation**: Creates templates in seconds
- ✂️ **Two Templates Per Page**: Efficient printing with dual templates (when template fits)
- 🔄 **Smart Page Splitting**: Automatically splits oversized templates across multiple A4 pages with overlap zones
- 📏 **Alignment Guides**: Green dashed centerlines and orange overlap markers for easy assembly of split templates

## Use Cases

Perfect for:
- Exhaust system heat wrapping (ceramic fibre, stainless steel, inconel sheet)
- Pipe insulation fabrication
- Custom pipe covering materials such as clamp on heatshields

## Installation

### Prerequisites

1. **Blender 3.0 or higher** - [Download Blender](https://www.blender.org/download/)

### Install the Addon

1. Download `pipe_template_generator.zip` from this repository **(No not unzip)**
2. Open Blender
3. Go to: **Edit > Preferences > Add-ons**
4. Click **Install...** button (top right)
5. Select the downloaded `pipe_template_generator.zip` file
6. Enable the addon by checking the box next to **"Object: Pipe Flat Pattern Generator"**

## Quick Start

1. Open Blender and press **N** to open the sidebar
2. Click the **"Pipe Templates"** tab
3. Enter your pipe specifications:
   - Pipe OD: 76.2mm (for 3" pipe)
   - Bend Radius: 1.5 (for 1.5D radius)
   - Bend Angle: 90° (for 90-degree bend)
   - Number of Segments: 5
   - Wrap Thickness: 6.15mm (6mm ceramic fibre + 0.15mm stainless)
   - Overlap: 10mm
4. Select an output folder
5. Click **"Generate Template"**
6. Open the generated PDF from the output folder
7. Print at **100% scale** (Actual Size)
8. Verify the 100mm scale bar measures exactly 100mm
9. Cut along the **RED outline**

## Template Output

The generated PDF automatically adapts based on template size:

### Single-Page Layout (templates ≤247mm wide)
- **Two identical templates per page** for efficient printing
- **Blue outline**: Base pipe shape (reference)
- **Red outline**: Cutting line for wrap materials
- **100mm scale bar**: For print verification
- **Dimensions**: Width and height annotations
- **Legend**: Clear identification of outlines
- **Title**: Shows pipe specs and degrees per segment

### Split-Page Layout (templates >247mm wide)
When the template is too wide for a single A4 sheet, it automatically splits into two pieces on the same page - should they be too tall and not fit vertically they will instead split across 2 pages:
- **Page 1**: LEFT HALF (1 of 2) - Left side with overlap zone
- **Page 2**: RIGHT HALF (2 of 2) - Right side with overlap zone
- **Green dashed centerline**: Alignment guide for joining pages
- **Orange overlap zone** (20mm): Marked on each page for gluing/taping
- **Full dimensions shown**: Total template size displayed on both pages
- **Scale bar on each page**: Independent verification per sheet

### Example Templates

**Small Template (40mm OD pipe):**
- Template dimensions: 155mm × 22mm
- Fits on single page with two templates

**Standard Template (3" / 76mm OD pipe):**
- Template dimensions: 288mm × 38mm
- Automatically splits across 2 pages with 20mm overlap

**Large Template (6" / 150mm OD pipe):**
- Template dimensions: 520mm × 48mm
- Splits across 2 pages, each showing ~280mm width

## Parameters Explained

### Pipe OD (mm)
Outer diameter of the pipe in millimeters
- Default: 76.2mm (3 inches)
- Range: 10mm to 500mm

### Bend Radius (×D)
Centerline radius as a multiple of the pipe diameter
- Default: 1.5 (means 1.5 × diameter)
- Range: 0.5 to 10.0
- Example: 1.5D for 3"(76.2mm) pipe = 4.5"(114.3mm) centerline radius

### Bend Angle (°)
Total angle of the bend in degrees
- Default: 90°
- Range: 1° to 360°
- Enter the value directly (e.g., 90 for 90 degrees)

### Number of Segments
How many pieces to split the bend into
- Default: 5
- Range: 1 to 20
- More segments = + smoother curvature, + easier install, - more joints to make, - more time cutting and fitting.

### Wrap Thickness (mm)
Thickness of the wrap material in millimeters
- Default: 6.15mm (6mm ceramic fibre + 0.15mm stainless) Note: Often stainless layer needs to be calcualted as much thicker due to embossing. 
- Range: 0.1mm to 50mm
- Automatically calculates wrap radius

### Tail Overlap (mm)
Overlap for the narrow ends of the templates to allow for joining. 
- Default: 10mm
- Range: 0mm to 50mm

## Example Configurations

### Example 1: 3" Exhaust with 90° Bend (Default)
```
Pipe OD: 76.2mm
Bend Radius: 1.5×D
Bend Angle: 90°
Segments: 5
Wrap Thickness: 6.15mm
Result: 5 pieces @ 18° each
```

### Example 2: 2" Pipe with Tight 45° Bend
```
Pipe OD: 50.8mm
Bend Radius: 1.0×D
Bend Angle: 45°
Segments: 3
Wrap Thickness: 6.15mm
Result: 3 pieces @ 15° each
```

### Example 3: 4" Pipe with 180° U-Bend
```
Pipe OD: 101.6mm
Bend Radius: 2.0×D
Bend Angle: 180°
Segments: 6
Wrap Thickness: 6.15mm
Result: 6 pieces @ 30° each
```

## Printing Instructions

### Critical Settings

When printing the PDF template:

1. **Scale**: 100% (Actual Size / Do Not Scale)
2. **Orientation**: Landscape
3. **Paper**: A4 (297mm × 210mm)
4. **Margins**: None or Minimum

### Verification

**Always verify the scale before cutting:**
1. Measure the scale bar at the bottom of the page
2. It **must** measure exactly 100mm
3. If not 100mm, adjust printer settings and reprint

### Cutting

1. Cut along the **RED outline** (not the blue reference line)
2. Make the specified number of identical pieces
3. Example: For 5 segments, cut 5 pieces from ceramic fibre and 5 from stainless 
Note: Overlap between the pieces will need to be accounted for on a case by case basis.


### For Split-Page Templates

If your template was split across multiple pages:

1. **Print both pages** at 100% scale
2. **Verify scale bars** on each page (must measure exactly 100mm)
3. **Trim pages** leaving the overlap zone intact
4. **Align the green centerlines** - they should overlap perfectly
5. **Tape or glue** using ther overlap markers to get perfect alignment
6. You now have one complete template



## How It Works

1. **3D Geometry Creation**: Creates accurate curved pipe segment with proper cylindrical geometry
2. **Seam Marking for unwrap**: Marks seam along ground plane at minimum radius (closest to origin)
3. **UV Unwrapping**: Uses marked seam and Blender's UV unwrap to create flat pattern
4. **Boundary Extraction**: Finds outer edges of UV unwrap and extracts to use pdf generator
5. **PDF Generation**: Uses reportlab to create printable template with exacted UV unwrap boundry


## Troubleshooting

### "reportlab not installed" Error
Install reportlab using the pip command from the Installation section above.

### Template Dimensions Seem Wrong
Verify that wrap thickness is correct. Should be the total thickness of all wrap layers combined.

### Scale Bar Doesn't Measure 100mm
When printing, ensure "Scale" is set to "100%" or "Actual Size" in your print dialog. Do not use "Fit to page".

### Addon Panel Not Visible
Press 'N' key in the 3D viewport to open the sidebar, then look for the "Pipe Templates" tab.


## Version History

## Version 1.0.0 – Official Release (2025-12-11)

### Features
- Complete Blender addon with full GUI workflow
- Generates 3D curved pipe segments
- UV unwrapping with automatic seam detection
- PDF export
- Scale bar and dimension annotations
- Two templates per page by default
- Works reliably from any Blender mode

### Layout and Rendering
- Optimized vertical and horizontal space usage for all templates
- Intelligent layout selection based on both width and height constraints
- Four layout modes:
  - single-page dual
  - single-page individual
  - split-page combined
  - split-page separate
- Templates automatically positioned to avoid drawing outside page bounds

### Automatic Multi-Page and Split-Page Handling
- Automatic detection of oversized templates (>247 mm width)
- Templates automatically split across two A4 pages with:
  - 20 mm overlap zone
  - green dashed centerline
  - orange overlap markers
  - clear LEFT HALF / RIGHT HALF labeling
- Split-width templates can show both halves on one page when space allows
- Automatic vertical overflow detection with multi-page splitting




## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with Blender Python API and reportlab

## Support Development

Support ongoing development across all my projects:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-181717?logo=github)](https://github.com/sponsors/bowermotorsport)
[![Support Future Projects](https://img.shields.io/badge/Support%20Future%20Projects-Ko--fi-29ABE0?logo=ko-fi&logoColor=white)](https://ko-fi.com/bowermotorsport)


## Screenshots

### Blender Interface
The addon appears in the sidebar (press N) under "Pipe Templates":

![BowerMotorsport Logo](Readme_Images/Demo_Images_1.png)

### Generated PDF Template
![BowerMotorsport Logo](Readme_Images/Example_Template.png)

