"""
Tyrannosaurus Rex — Blender Python Script
Compatible: Blender 3.6 / 4.x
Usage: Open Blender → Scripting workspace → paste or load this file → Run Script.
Output: TyrannosaurusRex.glb (same folder as the saved .blend, or system temp if unsaved).
"""

import bpy
import math
import os
import tempfile

BL4 = bpy.app.version >= (4, 0, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  SCENE UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in (bpy.data.meshes, bpy.data.materials,
                bpy.data.lights, bpy.data.cameras):
        for block in list(col):
            col.remove(block)


# ══════════════════════════════════════════════════════════════════════════════
#  GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _finalize(obj, name, scale, rx, ry, rz):
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.select_all(action='DESELECT')
    return obj


def iso(name, loc, scale=(1, 1, 1), rx=0, ry=0, rz=0, sd=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sd, location=loc)
    return _finalize(bpy.context.active_object, name, scale, rx, ry, rz)


def cyl(name, loc, scale=(1, 1, 1), rx=0, ry=0, rz=0, v=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, location=loc)
    return _finalize(bpy.context.active_object, name, scale, rx, ry, rz)


# ══════════════════════════════════════════════════════════════════════════════
#  T-REX BODY
#  Scale: 1 Blender unit ≈ 1 metre.  Adult T-Rex ~12 m nose-to-tail.
# ══════════════════════════════════════════════════════════════════════════════

def build_trex():
    parts = []

    # ── Core body ─────────────────────────────────────────────────────────
    parts += [
        iso("Torso",       ( 0.00,  0.00, 2.50), (1.20, 2.05, 1.00)),
        iso("Hips",        ( 0.00, -0.60, 2.20), (1.10, 0.90, 0.90)),
    ]

    # ── Neck ──────────────────────────────────────────────────────────────
    parts += [
        cyl("Neck",        ( 0.00,  1.40, 3.30), (0.42, 0.42, 0.70), rx=35),
    ]

    # ── Head ──────────────────────────────────────────────────────────────
    parts += [
        iso("Cranium",     ( 0.00,  2.45, 4.00), (0.72, 1.10, 0.65), sd=3),
        iso("UpperSnout",  ( 0.00,  3.30, 3.85), (0.45, 0.60, 0.28), sd=2),
        iso("LowerJaw",    ( 0.00,  2.90, 3.52), (0.60, 0.95, 0.22), sd=2),
    ]

    # ── Tail — 5 tapering segments ────────────────────────────────────────
    for i, (y, z, sx, sz) in enumerate([
        (-1.60, 2.15, 0.88, 0.78),
        (-2.90, 1.85, 0.68, 0.58),
        (-4.10, 1.50, 0.48, 0.42),
        (-5.10, 1.10, 0.30, 0.27),
        (-5.90, 0.80, 0.16, 0.15),
    ]):
        parts.append(iso(f"Tail{i + 1}", (0, y, z), (sx, 0.90, sz), sd=2))

    # ── Legs ──────────────────────────────────────────────────────────────
    for sx, s in ((0.90, "L"), (-0.90, "R")):
        parts += [
            iso(f"Thigh_{s}", ( sx, -0.30, 1.55), (0.50, 0.44, 0.88), rx=-12),
            iso(f"Shin_{s}",  ( sx,  0.28, 0.65), (0.34, 0.30, 0.80), rx=-30),
            iso(f"Foot_{s}",  ( sx,  0.58, 0.15), (0.36, 0.54, 0.18)),
        ]
        for ti, tx in enumerate((-0.16, 0.0, 0.16)):
            parts.append(iso(f"Toe_{s}{ti}",
                             (sx + tx, 0.90 + ti * 0.04, 0.07),
                             (0.09, 0.24, 0.07), sd=1))

    # ── Vestigial arms ────────────────────────────────────────────────────
    for sx, s, rz in ((0.70, "L", 15), (-0.70, "R", -15)):
        parts += [
            iso(f"UpperArm_{s}", ( sx,       1.75, 2.85), (0.15, 0.14, 0.30), rx=25, rz=rz),
            iso(f"LowerArm_{s}", ( sx * 1.12, 2.00, 2.55), (0.10, 0.10, 0.22), rx=15, rz=rz),
        ]
        for fi, fx in enumerate((-0.06, 0.06)):
            parts.append(iso(f"Finger_{s}{fi}",
                             (sx * 1.15 + fx, 2.18, 2.42),
                             (0.05, 0.05, 0.12), sd=1))

    # ── Join all parts into one mesh ──────────────────────────────────────
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()

    trex = bpy.context.active_object
    trex.name = "TyrannosaurusRex"
    bpy.ops.object.shade_smooth()

    sub = trex.modifiers.new("Subdivision", 'SUBSURF')
    sub.levels = 2
    sub.render_levels = 3

    return trex


# ══════════════════════════════════════════════════════════════════════════════
#  PBR SKIN MATERIAL
#  Principled BSDF + procedural scale bump (Voronoi) + colour variation (Noise)
# ══════════════════════════════════════════════════════════════════════════════

def build_material():
    mat = bpy.data.materials.new("TRex_Skin")
    mat.use_nodes = True
    nt = mat.node_tree
    ns = nt.nodes
    lk = nt.links
    ns.clear()

    # ── Output & Principled BSDF ──────────────────────────────────────────
    out  = ns.new('ShaderNodeOutputMaterial'); out.location  = (900, 0)
    bsdf = ns.new('ShaderNodeBsdfPrincipled'); bsdf.location = (500, 0)
    lk.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    bsdf.inputs['Roughness'].default_value = 0.88

    # Subsurface scattering — leathery skin translucency
    if BL4:
        bsdf.inputs['Subsurface Weight'].default_value = 0.04
    else:
        bsdf.inputs['Subsurface'].default_value        = 0.04
        bsdf.inputs['Subsurface Color'].default_value  = (0.45, 0.18, 0.10, 1)

    # ── Shared texture coordinates ────────────────────────────────────────
    tc = ns.new('ShaderNodeTexCoord'); tc.location = (-900, 0)
    mp = ns.new('ShaderNodeMapping');  mp.location = (-700, 0)
    mp.inputs['Scale'].default_value = (5.0, 5.0, 5.0)
    lk.new(tc.outputs['Object'], mp.inputs['Vector'])

    # ── Base colour: noise → 3-stop colour ramp ───────────────────────────
    cn = ns.new('ShaderNodeTexNoise'); cn.location = (-480, 300)
    cn.inputs['Scale'].default_value     = 2.5
    cn.inputs['Detail'].default_value    = 10.0
    cn.inputs['Roughness'].default_value = 0.65
    lk.new(mp.outputs['Vector'], cn.inputs['Vector'])

    cr = ns.new('ShaderNodeValToRGB'); cr.location = (-220, 300)
    cr.color_ramp.elements[0].position = 0.20
    cr.color_ramp.elements[0].color    = (0.055, 0.045, 0.025, 1)  # deep shadow
    cr.color_ramp.elements[1].position = 0.80
    cr.color_ramp.elements[1].color    = (0.195, 0.155, 0.085, 1)  # warm midtone
    mid = cr.color_ramp.elements.new(0.50)
    mid.color = (0.100, 0.130, 0.055, 1)                            # olive
    lk.new(cn.outputs['Fac'], cr.inputs['Fac'])
    lk.new(cr.outputs['Color'], bsdf.inputs['Base Color'])

    # ── Roughness variation ───────────────────────────────────────────────
    rn = ns.new('ShaderNodeTexNoise'); rn.location = (-480, -40)
    rn.inputs['Scale'].default_value  = 4.5
    rn.inputs['Detail'].default_value = 5.0
    lk.new(mp.outputs['Vector'], rn.inputs['Vector'])

    rr = ns.new('ShaderNodeValToRGB'); rr.location = (-220, -40)
    rr.color_ramp.elements[0].position = 0.30
    rr.color_ramp.elements[0].color    = (0.60, 0.60, 0.60, 1)
    rr.color_ramp.elements[1].position = 0.80
    rr.color_ramp.elements[1].color    = (0.95, 0.95, 0.95, 1)
    lk.new(rn.outputs['Fac'], rr.inputs['Fac'])
    lk.new(rr.outputs['Color'], bsdf.inputs['Roughness'])

    # ── Scale bump: Voronoi cells + fine noise, blended via Math nodes ────
    mp2 = ns.new('ShaderNodeMapping');  mp2.location = (-700, -320)
    mp2.inputs['Scale'].default_value = (16.0, 16.0, 16.0)
    lk.new(tc.outputs['Object'], mp2.inputs['Vector'])

    vor = ns.new('ShaderNodeTexVoronoi'); vor.location = (-480, -320)
    vor.voronoi_dimensions = '3D'
    vor.inputs['Scale'].default_value = 1.0
    lk.new(mp2.outputs['Vector'], vor.inputs['Vector'])

    fn = ns.new('ShaderNodeTexNoise'); fn.location = (-480, -520)
    fn.inputs['Scale'].default_value  = 9.0
    fn.inputs['Detail'].default_value = 3.0
    lk.new(mp.outputs['Vector'], fn.inputs['Vector'])

    # Average the two height sources (Math nodes — version-safe)
    add_n = ns.new('ShaderNodeMath'); add_n.location = (-220, -400)
    add_n.operation = 'ADD'
    lk.new(vor.outputs['Distance'], add_n.inputs[0])
    lk.new(fn.outputs['Fac'],       add_n.inputs[1])

    div_n = ns.new('ShaderNodeMath'); div_n.location = (-20, -400)
    div_n.operation = 'DIVIDE'
    div_n.inputs[1].default_value = 2.0
    lk.new(add_n.outputs['Value'], div_n.inputs[0])

    bmp = ns.new('ShaderNodeBump'); bmp.location = (200, -400)
    bmp.inputs['Strength'].default_value = 0.55
    bmp.inputs['Distance'].default_value = 0.04
    lk.new(div_n.outputs['Value'], bmp.inputs['Height'])
    lk.new(bmp.outputs['Normal'],  bsdf.inputs['Normal'])

    return mat


# ══════════════════════════════════════════════════════════════════════════════
#  LIGHTING & CAMERA
# ══════════════════════════════════════════════════════════════════════════════

def setup_scene():
    w = bpy.context.scene.world
    if w is None:
        w = bpy.data.worlds.new("World")
        bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value    = (0.06, 0.06, 0.08, 1)
        bg.inputs["Strength"].default_value = 0.5

    bpy.ops.object.light_add(type='SUN', location=(6, -6, 12))
    key = bpy.context.active_object
    key.name = "Key"
    key.data.energy = 4.0
    key.rotation_euler = (math.radians(40), 0, math.radians(50))

    bpy.ops.object.light_add(type='AREA', location=(-5, 3, 7))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 800
    fill.data.size   = 6

    bpy.ops.object.light_add(type='SPOT', location=(3, -7, 8))
    rim = bpy.context.active_object
    rim.name = "Rim"
    rim.data.energy = 500
    rim.rotation_euler = (math.radians(55), 0, math.radians(-30))

    bpy.ops.object.camera_add(location=(9, -9, 5.5))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.rotation_euler = (math.radians(68), 0, math.radians(45))
    bpy.context.scene.camera = cam


# ══════════════════════════════════════════════════════════════════════════════
#  GLB EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_glb():
    blend_path = bpy.data.filepath
    if blend_path:
        out = os.path.splitext(blend_path)[0] + ".glb"
    else:
        out = os.path.join(tempfile.gettempdir(), "TyrannosaurusRex.glb")

    bpy.ops.export_scene.gltf(
        filepath      = out,
        export_format = 'GLB',
        use_selection = False,
        export_apply  = True,   # bakes Subdivision Surface into the exported mesh
        export_yup    = True,   # standard glTF Y-up orientation
    )
    print(f"[T-Rex] GLB exported → {out}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

clear_scene()
setup_scene()

trex = build_trex()
mat  = build_material()
trex.data.materials.append(mat)

path = export_glb()
print(f"[T-Rex] Done.  GLB → {path}")
