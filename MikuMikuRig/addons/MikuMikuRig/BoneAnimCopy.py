import bpy
from . import data
from . import mapping
from .utilfuncs import *

class MMR_BAC_anel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_idname = "SCENE_PT_MMR_Rig_D"
    bl_region_type = "UI"
    bl_category = "MMR"
    bl_label = "骨骼映射工具"
    bl_parent_id = "SCENE_PT_MMR_Rig_B"

    def draw(self, context):
        layout = self.layout
        
        split = layout.row().split(factor=0.2)
        left = split.column()
        right = split.column()
        left.label(text='映射骨架:')
        left.label(text='约束目标:')
        right.prop(bpy.context.scene, 'mmr_kumopult_bac_owner', text='', icon='ARMATURE_DATA', translate=False)
        if bpy.context.scene.mmr_kumopult_bac_owner != None and bpy.context.scene.mmr_kumopult_bac_owner.type == 'ARMATURE':
            s = get_state()
            right.prop(s, 'selected_target', text='', icon='ARMATURE_DATA', translate=False)
            
            if s.target == None:
                layout.label(text='选择另一骨架对象作为约束目标以继续操作', icon='INFO')
            else:
                mapping.draw_panel(layout.row())
                row = layout.row()
                row.prop(s, 'preview', text='预览约束', icon= 'HIDE_OFF' if s.preview else 'HIDE_ON')
                row.operator('mmr_kumopult_bac.bake', text='烘培动画', icon='NLA')
        else:
            right.label(text='未选中映射骨架对象', icon='ERROR')

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.active_object

class MMR_BAC_State(bpy.types.PropertyGroup):
    def update_target(self, context):
        self.owner = bpy.context.scene.mmr_kumopult_bac_owner
        self.target = self.selected_target

        for m in self.mappings:
            m.apply()
    
    def update_preview(self, context):
        for m in self.mappings:
            m.apply()
    
    def update_active(self, context):
        if self.sync_select:
            self.update_select(bpy.context)
            owner_active = self.owner.data.bones.get(self.mappings[self.active_mapping].owner)
            self.owner.data.bones.active = owner_active
            target_active = self.target.data.bones.get(self.mappings[self.active_mapping].target)
            self.target.data.bones.active = target_active
    
    def update_select(self, context):
        if self.sync_select:
            owner_selection = []
            target_selection = []
            for m in self.mappings:
                if m.selected:
                    owner_selection.append(m.owner)
                    target_selection.append(m.target)
            for bone in self.owner.data.bones:
                bone.select = bone.name in owner_selection
            for bone in self.target.data.bones:
                bone.select = bone.name in target_selection
    
    selected_target: bpy.props.PointerProperty(
        type=bpy.types.Object,
        override={'LIBRARY_OVERRIDABLE'},
        poll=lambda self, obj: obj.type == 'ARMATURE' and obj != bpy.context.scene.mmr_kumopult_bac_owner,
        update=update_target
    )
    target: bpy.props.PointerProperty(type=bpy.types.Object, override={'LIBRARY_OVERRIDABLE'})
    owner: bpy.props.PointerProperty(type=bpy.types.Object, override={'LIBRARY_OVERRIDABLE'})
    
    mappings: bpy.props.CollectionProperty(type=data.MMR_BAC_BoneMapping, override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})
    active_mapping: bpy.props.IntProperty(default=-1, override={'LIBRARY_OVERRIDABLE'}, update=update_active)
    selected_count:bpy.props.IntProperty(default=0, override={'LIBRARY_OVERRIDABLE'}, update=update_select)
    
    editing_type: bpy.props.IntProperty(description="用于记录面板类型", override={'LIBRARY_OVERRIDABLE'})
    preview: bpy.props.BoolProperty(
        default=True, 
        description="开关所有约束以便预览烘培出的动画之类的",
        override={'LIBRARY_OVERRIDABLE'},
        update=update_preview
    )

    sync_select: bpy.props.BoolProperty(default=False, name='同步选择', description="点击列表项时会自动激活相应骨骼\n勾选列表项时会自动选中相应骨骼", override={'LIBRARY_OVERRIDABLE'})
    calc_offset: bpy.props.BoolProperty(default=True, name='自动旋转偏移', description="设定映射目标时自动计算旋转偏移", override={'LIBRARY_OVERRIDABLE'})
    ortho_offset: bpy.props.BoolProperty(default=True, name='正交', description="将计算结果近似至90°的倍数", override={'LIBRARY_OVERRIDABLE'})
    
    def get_target_armature(self):
        return self.target.data

    def get_owner_armature(self):
        return self.owner.data
    
    def get_target_pose(self):
        return self.target.pose

    def get_owner_pose(self):
        return self.owner.pose

    def get_active_mapping(self):
        return self.mappings[self.active_mapping]
    
    def get_mapping_by_target(self, name):
        if name != "":
            for i, m in enumerate(self.mappings):
                if m.target == name:
                    return m, i
        return None, -1

    def get_mapping_by_owner(self, name):
        if name != "":
            for i, m in enumerate(self.mappings):
                if m.owner == name:
                    return m, i
        return None, -1

    def get_selection(self):
        indices = []

        if self.selected_count == 0 and len(self.mappings) > self.active_mapping >= 0:
            indices.append(self.active_mapping)
        else:
            for i in range(len(self.mappings) - 1, -1, -1):
                if self.mappings[i].selected:
                    indices.append(i)
        return indices
    
    def add_mapping(self, owner, target, index=-1):
        # 未传入index时，以激活项作为index
        if index == -1:
            index = self.active_mapping + 1
        # 这里需要检测一下目标骨骼是否已存在映射
        m, i = self.get_mapping_by_owner(owner)
        if m:
            # 若已存在，则覆盖原本的源骨骼，并返回映射和索引值
            m.target = target
            self.active_mapping = i
            return m, i
        else:
            # 若不存在，则新建映射，同样返回映射和索引值
            m = self.mappings.add()
            m.selected_owner = owner
            m.target = target
            # return m, len(self.mappings) - 1
            self.mappings.move(len(self.mappings) - 1, index)
            self.active_mapping = index
            return self.mappings[index], index
    
    def remove_mapping(self):
        for i in self.get_selection():
            self.mappings[i].clear()
            self.mappings.remove(i)
        # 选中状态更新
        self.active_mapping = min(self.active_mapping, len(self.mappings) - 1)
        self.selected_count = 0

def register():
    bpy.types.Scene.mmr_kumopult_bac_owner = bpy.props.PointerProperty(type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE')
    bpy.types.Armature.mmr_kumopult_bac = bpy.props.PointerProperty(type=MMR_BAC_State, override={'LIBRARY_OVERRIDABLE'})
    print("hello kumopult!")

def unregister():
    del bpy.types.Scene.mmr_kumopult_bac_owner
    del bpy.types.Armature.mmr_kumopult_bac
    print("goodbye kumopult!")



