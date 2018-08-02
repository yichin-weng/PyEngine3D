#include "scene_constants.glsl"
#include "utility.glsl"


#ifdef GL_COMPUTE_SHADER
layout(local_size_x=1, local_size_y=1, local_size_z=1) in;

layout(std430, binding=0) buffer emitter_buffer { EmitterData emitter_datas[]; };

void refresh(uint id)
{
    // initialize
    float t1 = rand(vec2(TIME, float(id) + PI));
    float t2 = rand(vec2(TIME, t1 + PI));
    float t3 = rand(vec2(TIME, t2 + PI));
    float t4 = rand(vec2(TIME, t3 + PI));
    float t5 = rand(vec2(TIME, t4 + PI));
    float t6 = rand(vec2(TIME, t5 + PI));
    float t7 = rand(vec2(TIME, t6 + PI));
    float t8 = rand(vec2(TIME, t7 + PI));
    float t9 = rand(vec2(TIME, t8 + PI));
    float t10 = rand(vec2(TIME, t9 + PI));
    float t11 = rand(vec2(TIME, t10 + PI));
    float t12 = rand(vec2(TIME, t11 + PI));
    float t13 = rand(vec2(TIME, t12 + PI));
    float t14 = rand(vec2(TIME, t13 + PI));
    float t15 = rand(vec2(TIME, t14 + PI));
    float t16 = rand(vec2(TIME, t15 + PI));
    float t17 = rand(vec2(TIME, t16 + PI));
    float t18 = rand(vec2(TIME, t17 + PI));
    float t19 = rand(vec2(TIME, t18 + PI));
    float t20 = rand(vec2(TIME, t19 + PI));

    emitter_datas[id].delay = mix(EMITTER_DELAY.x, EMITTER_DELAY.y, t1);
    emitter_datas[id].state = (0.0 < emitter_datas[id].delay) ? EMITTER_STATE_DELAY : EMITTER_STATE_ALIVE;
    emitter_datas[id].life_time = mix(EMITTER_LIFE_TIME.x, EMITTER_LIFE_TIME.y, t2);
    emitter_datas[id].position = mix(EMITTER_POSITION_MIN, EMITTER_POSITION_MAX, vec3(t3, t4, t5));
    emitter_datas[id].velocity = mix(EMITTER_VELOCITY_MIN, EMITTER_VELOCITY_MAX, vec3(t6, t7, t8));
    emitter_datas[id].rotation = mix(EMITTER_ROTATION_MIN, EMITTER_ROTATION_MAX, vec3(t9, t10, t11));
    emitter_datas[id].rotation_velocity = mix(EMITTER_ROTATION_VELOCITY_MIN, EMITTER_ROTATION_VELOCITY_MAX, vec3(t12, t13, t14));
    emitter_datas[id].scale = mix(EMITTER_SCALE_MIN, EMITTER_SCALE_MAX, vec3(t15, t16, t17));
    emitter_datas[id].scale_velocity = mix(EMITTER_SCALE_VELOCITY_MIN, EMITTER_SCALE_VELOCITY_MAX, vec3(t18, t19, t20));

    emitter_datas[id].opacity = EMITTER_OPACITY;
    emitter_datas[id].local_matrix = mat4(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0);
}


void update_sequence(uint id, float life_ratio)
{
    if(1 < EMITTER_TOTAL_CELL_COUNT && 0.0 < EMITTER_PLAY_SPEED)
    {
        float ratio = life_ratio * EMITTER_PLAY_SPEED;
        ratio = float(EMITTER_TOTAL_CELL_COUNT - 1) * (ratio - floor(ratio));

        int index = clamp(int(floor(ratio)), 0, EMITTER_TOTAL_CELL_COUNT - 1);
        int next_index = (index == (EMITTER_TOTAL_CELL_COUNT - 1)) ? 0 : index + 1;

        emitter_datas[id].sequence_ratio = ratio - float(index);

        if(next_index == emitter_datas[id].next_sequence_index)
        {
            return;
        }

        emitter_datas[id].sequence_index = emitter_datas[id].next_sequence_index;
        emitter_datas[id].sequence_uv = emitter_datas[id].next_sequence_uv;
        emitter_datas[id].next_sequence_index = next_index;
        emitter_datas[id].next_sequence_uv.x = mod(next_index, EMITTER_CELL_COUNT.x) / float(EMITTER_CELL_COUNT.x);
        emitter_datas[id].next_sequence_uv.y = float(EMITTER_CELL_COUNT.y - 1 - int(floor(next_index / EMITTER_CELL_COUNT.x))) / float(EMITTER_CELL_COUNT.y);
    }
}


void main()
{
    uint id = gl_GlobalInvocationID.x;

    if(EMITTER_STATE_DEAD == emitter_datas[id].state)
    {
        return;
    }

    if(EMITTER_STATE_NONE == emitter_datas[id].state)
    {
        refresh(id);

        emitter_datas[id].loop_remain = EMITTER_LOOP;
        emitter_datas[id].elapsed_time = 0.0;
        emitter_datas[id].sequence_ratio = 0.0;
        emitter_datas[id].sequence_index = 0;
        emitter_datas[id].next_sequence_index = 0;
    }

    if(EMITTER_STATE_DELAY == emitter_datas[id].state)
    {
        emitter_datas[id].delay -= DELTA_TIME;
        if(0.0 < emitter_datas[id].delay)
        {
            return;
        }
        emitter_datas[id].delay = 0.0;
        emitter_datas[id].state = EMITTER_STATE_ALIVE;
    }

    if(EMITTER_STATE_ALIVE == emitter_datas[id].state)
    {
        emitter_datas[id].elapsed_time += DELTA_TIME;

        if(emitter_datas[id].life_time < emitter_datas[id].elapsed_time)
        {
            emitter_datas[id].elapsed_time = mod(emitter_datas[id].elapsed_time, emitter_datas[id].life_time);

            if(0 < emitter_datas[id].loop_remain)
            {
                emitter_datas[id].loop_remain -= 1;
            }

            if(0 == emitter_datas[id].loop_remain)
            {
                emitter_datas[id].state = EMITTER_STATE_DEAD;
                return;
            }

            refresh(id);
        }

        float life_ratio = 0.0;
        if(0.0 < emitter_datas[id].life_time)
        {
            life_ratio = clamp(emitter_datas[id].elapsed_time / emitter_datas[id].life_time, 0.0, 1.0);
        }

        update_sequence(id, life_ratio);

        emitter_datas[id].velocity += vec3(0.0, -EMITTER_GRAVITY, 0.0) * DELTA_TIME;
        emitter_datas[id].position += emitter_datas[id].velocity * DELTA_TIME;
        emitter_datas[id].rotation += emitter_datas[id].rotation_velocity * DELTA_TIME;
        emitter_datas[id].scale += emitter_datas[id].scale_velocity * DELTA_TIME;

        mat4 local_matrix = mat4(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0);

        if(emitter_datas[id].rotation.x != 0.0 || emitter_datas[id].rotation.y != 0.0 || emitter_datas[id].rotation.z != 0.0)
        {
            float ch = cos(emitter_datas[id].rotation.y);
            float sh = sin(emitter_datas[id].rotation.y);
            float ca = cos(emitter_datas[id].rotation.z);
            float sa = sin(emitter_datas[id].rotation.z);
            float cb = cos(emitter_datas[id].rotation.x);
            float sb = sin(emitter_datas[id].rotation.x);

            local_matrix[0] = vec4(ch*ca, sa, -sh*ca, 0.0);
            local_matrix[1] = vec4(sh*sb - ch*sa*cb, ca*cb, sh*sa*cb + ch*sb, 0.0);
            local_matrix[2] = vec4(ch*sa*sb + sh*cb, -ca*sb, -sh*sa*sb + ch*cb, 0.0);
        }

        local_matrix[0].x *= emitter_datas[id].scale.x;
        local_matrix[1].y *= emitter_datas[id].scale.y;
        local_matrix[2].z *= emitter_datas[id].scale.z;

        emitter_datas[id].local_matrix = local_matrix;

        if(0.0 != EMITTER_FADE_IN || 0.0 != EMITTER_FADE_OUT)
        {
            emitter_datas[id].opacity = EMITTER_OPACITY;

            float left_life_ratio = 1.0 - life_ratio;

            if(0.0 < EMITTER_FADE_IN && life_ratio < EMITTER_FADE_IN)
            {
                emitter_datas[id].opacity *= life_ratio / EMITTER_FADE_IN;
            }

            if(0.0 < EMITTER_FADE_OUT && left_life_ratio < EMITTER_FADE_OUT)
            {
                emitter_datas[id].opacity *= left_life_ratio / EMITTER_FADE_OUT;
            }
        }
    }
}
#endif