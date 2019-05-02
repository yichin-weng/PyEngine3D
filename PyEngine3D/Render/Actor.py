import math

import numpy as np

from PyEngine3D.Utilities import *
from PyEngine3D.App import CoreManager
from .Mesh import BoundBox


class StaticActor:
    def __init__(self, name, **object_data):
        self.name = name
        self.selected = False
        self.model = None
        self.has_mesh = False

        # transform
        self.bound_box = BoundBox()
        # self.geometry_bound_boxes = []
        self.transform = TransformObject()
        self.transform.set_pos(object_data.get('pos', [0, 0, 0]))
        self.transform.set_rotation(object_data.get('rot', [0, 0, 0]))
        self.transform.set_scale(object_data.get('scale', [1, 1, 1]))

        self.set_model(object_data.get('model'))

        self.instance_pos = RangeVariable(**object_data.get('instance_pos',
                                                            dict(min_value=Float3(-10.0, 0.0, -10.0),
                                                                 max_value=Float3(10.0, 0.0, 10.0))))
        self.instance_rot = RangeVariable(**object_data.get('instance_rot', dict(min_value=FLOAT3_ZERO)))
        self.instance_scale = RangeVariable(**object_data.get('instance_scale', dict(min_value=1.0)))
        self.instance_pos_list = object_data.get('instance_pos_list', [])
        self.instance_rot_list = object_data.get('instance_rot_list', [])
        self.instance_scale_list = object_data.get('instance_scale_list', [])

        self.instance_matrix = None
        self.instance_radius_offset = object_data.get('instance_radius_offset', 0.0)
        self.instance_radius_scale = object_data.get('instance_radius_scale', 1.0)

        self.instance_count = object_data.get('instance_count', 1)
        self.set_instance_count(self.instance_count)

        self.update_bound_box()

        self.attributes = Attributes()

    def delete(self):
        pass

    def set_model(self, model):
        self.model = model
        self.has_mesh = model is not None and model.mesh is not None
        # self.geometry_bound_boxes.clear()
        # if self.has_mesh:
        #     for geometry in self.model.mesh.geometries:
        #         self.geometry_bound_boxes.append(BoundBox())

    def get_save_data(self):
        save_data = dict(
            name=self.name,
            model=self.model.name if self.model else '',
            pos=self.transform.pos.tolist(),
            rot=self.transform.rot.tolist(),
            scale=self.transform.scale.tolist(),
            instance_count=self.instance_count,
            instance_pos=self.instance_pos.get_save_data(),
            instance_rot=self.instance_rot.get_save_data(),
            instance_scale=self.instance_scale.get_save_data(),
            instance_pos_list=self.instance_pos_list,
            instance_rot_list=self.instance_rot_list,
            instance_scale_list=self.instance_scale_list,
        )
        return save_data

    def set_instance_count(self, count):
        self.instance_count = count

        if 1 < count:
            self.instance_pos_list = [self.instance_pos.get_uniform() for i in range(count)]
            self.instance_rot_list = [self.instance_rot.get_uniform() for i in range(count)]
            self.instance_scale_list = [self.instance_scale.get_uniform() for i in range(count)]

            self.instance_matrix = np.zeros(count, (np.float32, (4, 4)))

            offset_max = FLOAT32_MIN
            scale_max = FLOAT32_MIN
            self.instance_radius_offset = 0.0
            self.instance_radius_scale = 1.0

            for i in range(count):
                uniform_scale = self.instance_scale_list[i]
                offset_max = max(offset_max, max(np.abs(self.instance_pos_list[i])))
                scale_max = max(scale_max, np.abs(uniform_scale))

                self.instance_matrix[i][...] = MATRIX4_IDENTITY
                matrix_scale(self.instance_matrix[i], uniform_scale, uniform_scale, uniform_scale)
                matrix_rotate(self.instance_matrix[i], *self.instance_rot_list[i])
                matrix_translate(self.instance_matrix[i], *self.instance_pos_list[i])
            self.instance_radius_offset = offset_max
            self.instance_radius_scale = scale_max
        else:
            self.instance_matrix = None

    def get_attribute(self):
        self.attributes.set_attribute('name', self.name)
        self.attributes.set_attribute('pos', self.transform.pos)
        self.attributes.set_attribute('rot', self.transform.rot)
        self.attributes.set_attribute('scale', self.transform.scale)
        self.attributes.set_attribute('model', self.model.name if self.model else '')
        self.attributes.set_attribute('instance_count', self.instance_count)
        self.attributes.set_attribute('instance_pos', self.instance_pos.get_save_data())
        self.attributes.set_attribute('instance_rot', self.instance_rot.get_save_data())
        self.attributes.set_attribute('instance_scale', self.instance_scale.get_save_data())
        return self.attributes

    def set_attribute(self, attribute_name, attribute_value, parent_info, attribute_index):
        item_info_history = []
        parent_attribute_name = attribute_name
        while parent_info is not None:
            parent_attribute_name = parent_info.attribute_name
            item_info_history.insert(0, parent_info)
            parent_info = parent_info.parent_info

        if 1 < len(item_info_history) or 'instance_scale' == parent_attribute_name:
            attribute = getattr(self, item_info_history[0].attribute_name)
            if attribute is not None and isinstance(attribute, RangeVariable):
                if 'min_value' == attribute_name:
                    attribute.set_range(attribute_value, attribute.value[1])
                elif 'max_value' == attribute_name:
                    attribute.set_range(attribute.value[0], attribute_value)
                self.set_instance_count(self.instance_count)
        else:
            if attribute_name == 'pos':
                self.transform.set_pos(attribute_value)
            elif attribute_name == 'rot':
                self.transform.set_rotation(attribute_value)
            elif attribute_name == 'scale':
                self.transform.set_scale(attribute_value)
            elif attribute_name == 'instance_count':
                self.set_instance_count(attribute_value)
            elif hasattr(self, attribute_name):
                setattr(self, attribute_name, attribute_value)

    def get_mesh(self):
        return self.model.mesh if self.has_mesh else None

    def get_geometries(self):
        return self.model.mesh.geometries if self.has_mesh else []

    def get_material_instance(self, index):
        return self.model.material_instances[index] if self.model else None

    def set_selected(self, selected):
        self.selected = selected

    def update_bound_box(self):
        if self.has_mesh:
            self.bound_box.update_with_matrix(self.model.mesh.bound_box, self.transform.matrix)
            # if 1 == len(self.model.mesh.geometries):
            #     self.geometry_bound_boxes[0].clone(self.bound_box)
            # else:
            #     for i, geometry in enumerate(self.model.mesh.geometries):
            #         self.geometry_bound_boxes[i].update_with_matrix(self.bound_box, self.transform.matrix)

    def update(self, dt):
        if self.transform.update_transform():
            self.update_bound_box()


class CollisionActor(StaticActor):
    pass


class SkeletonActor(StaticActor):
    def __init__(self, name, **object_data):
        StaticActor.__init__(self, name, **object_data)

        self.last_animation_frame = 0.0
        self.animation_loop = True
        self.animation_blend_time = 0.5
        self.animation_elapsed_time = 0.0
        self.animation_speed = 1.0
        self.animation_frame = 0.0
        self.animation_play_time = 0.0
        self.animation_buffers = []
        self.prev_animation_buffers = []
        self.blend_animation_buffers = []
        self.animation_count = 0
        self.animation_mesh = None

        if self.has_mesh:
            for animation in self.model.mesh.animations:
                if animation:
                    animation_buffer = animation.get_animation_transforms(0.0)
                    # just initialize
                    self.prev_animation_buffers.append(animation_buffer.copy())
                    self.animation_buffers.append(animation_buffer.copy())
                    self.blend_animation_buffers.append(animation_buffer.copy())
                else:
                    self.prev_animation_buffers.append(None)
                    self.animation_buffers.append(None)
                    self.blend_animation_buffers.append(None)
            self.animation_mesh = self.model.mesh

    def set_animation(self, mesh, speed=1.0, loop=True, blend_time=0.5, force=False, reset=True):
        if mesh != self.animation_mesh or force:
            self.animation_mesh = mesh
            self.animation_speed = speed
            self.animation_loop = loop
            self.animation_blend_time = blend_time
            if reset:
                self.animation_elapsed_time = 0.0
                self.animation_play_time = 0.0
                self.animation_frame = 0.0
            # swap
            self.animation_buffers, self.blend_animation_buffers = self.blend_animation_buffers, self.animation_buffers

    def get_prev_animation_buffer(self, index):
        return self.prev_animation_buffers[index]

    def get_animation_buffer(self, index):
        return self.animation_buffers[index]

    def update(self, dt):
        StaticActor.update(self, dt)

        # update animation
        update_animation_frame = True
        for i, animation in enumerate(self.animation_mesh.animations):
            if animation is not None:
                blend_ratio = 1.0

                # update animation frame only first animation
                if update_animation_frame:
                    update_animation_frame = False
                    frame_count = animation.frame_count
                    if frame_count > 1:
                        self.animation_play_time += dt * self.animation_speed
                        if self.animation_loop:
                            self.animation_play_time = math.fmod(self.animation_play_time + dt * self.animation_speed, animation.animation_length)
                        else:
                            self.animation_play_time = min(animation.animation_length, self.animation_play_time)

                        self.animation_frame = animation.get_time_to_frame(self.animation_frame, self.animation_play_time)
                    else:
                        self.animation_frame = 0.0
                    if self.animation_elapsed_time < self.animation_blend_time:
                        blend_ratio = self.animation_elapsed_time / self.animation_blend_time
                    self.animation_elapsed_time += dt

                # update animation buffers
                self.prev_animation_buffers[i][...] = self.animation_buffers[i]

                if self.last_animation_frame != self.animation_frame:
                    self.last_animation_frame = self.animation_frame
                    animation_buffer = animation.get_animation_transforms(self.animation_frame)

                    if blend_ratio < 1.0:
                        self.animation_buffers[i][...] = self.blend_animation_buffers[i] * (1.0 - blend_ratio) + animation_buffer * blend_ratio
                    else:
                        self.animation_buffers[i][...] = animation_buffer
