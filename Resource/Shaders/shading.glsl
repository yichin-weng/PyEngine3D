#include "PCFKernels.glsl"
#include "utility.glsl"


const float PI = 3.141592;


float get_shadow_factor(vec3 world_position, sampler2D texture_shadow)
{
    float shadow_factor = 0.0;
    vec4 shadow_uv = SHADOW_MATRIX * vec4(world_position, 1.0);
    shadow_uv.xyz /= shadow_uv.w;
    shadow_uv.xyz = shadow_uv.xyz * 0.5 + 0.5;
    float shadow_depth = shadow_uv.z;

    const float shadow_radius = 1.0;
    const vec2 sample_scale = shadow_radius / textureSize(texture_shadow, 0);
    const int sample_count = PoissonSampleCount / 4;
    float weights = 0.0;
    for(int i=0; i<sample_count; ++i)
    {
        float weight = length(PoissonSamples[i]);
        weights += weight;
        vec2 uv = shadow_uv.xy + PoissonSamples[i] * sample_scale * 3.0;
        shadow_factor += texture(texture_shadow, uv).x <= shadow_depth ? 0.0 : weight;
    }
    shadow_factor /= weights;
    return shadow_factor;
}


// https://en.wikipedia.org/wiki/Oren%E2%80%93Nayar_reflectance_model
float oren_nayar(float roughness2, float NdotL, float NdotV, vec3 N, vec3 V, vec3 L)
{
    float incidentTheta = acos(NdotL);
    float outTheta = acos(NdotV);

    float A = 1.0 - 0.5 * (roughness2 / (roughness2 + 0.33));
    float B = (0.45 * roughness2) / (roughness2 + 0.09);
    float alpha = max(incidentTheta, outTheta);
    float beta  = min(incidentTheta, outTheta);

    vec3 u = normalize(V - N * NdotV);
    vec3 v = normalize(L - N * NdotL);
    float phiDiff = max(0.0, dot(u, v));

    // Exactly correct fomular.
    // return (A + (B * phiDiff * sin(alpha) * tan(beta))) * NdotL / PI;

    return (A + (B * phiDiff * sin(alpha) * tan(beta))) * NdotL;
}

// compute fresnel specular factor for given base specular and product
// product could be NdV or VdH depending on used technique
vec3 fresnel_factor(in vec3 f0, in float product)
{
    return mix(f0, vec3(1.0), pow(max(0.0, 1.01 - product), 5.0));
}

float D_blinn(in float roughness, in float NdH)
{
    float m = roughness * roughness;
    float m2 = m * m;
    float n = 2.0 / m2 - 2.0;
    return (n + 2.0) / (2.0 * PI) * pow(NdH, n);
}

float D_beckmann(in float roughness, in float NdH)
{
    float m = roughness * roughness;
    float m2 = m * m;
    float NdH2 = NdH * NdH;
    return exp((NdH2 - 1.0) / (m2 * NdH2)) / (PI * m2 * NdH2 * NdH2);
}

float D_GGX(in float roughness, in float NdH)
{
    float m = roughness * roughness;
    float m2 = m * m;
    float d = (NdH * m2 - NdH) * NdH + 1.0;
    return m2 / (PI * d * d);
}

float G_schlick(in float roughness, in float NdV, in float NdL)
{
    float k = roughness * roughness * 0.5;
    float V = NdV * (1.0 - k) + k;
    float L = NdL * (1.0 - k) + k;
    return 0.25 / (V * L);
}

// simple phong specular calculation with normalization
vec3 phong_specular(in vec3 V, in vec3 L, in vec3 N, in vec3 specular, in float roughness)
{
    vec3 R = reflect(-L, N);
    float spec = max(0.0, dot(V, R));
    float k = 1.999 / (roughness * roughness);
    return min(1.0, 3.0 * 0.0398 * k) * pow(spec, min(10000.0, k)) * specular;
}

// simple blinn specular calculation with normalization
vec3 blinn_specular(in float NdH, in vec3 specular, in float roughness)
{
    float k = 1.999 / (roughness * roughness);
    return min(1.0, 3.0 * 0.0398 * k) * pow(NdH, min(10000.0, k)) * specular;
}


// cook-torrance specular calculation
vec3 cooktorrance_specular(in float NdL, in float NdV, in float NdH, in vec3 specular, in float roughness)
{
    float D = D_GGX(roughness, NdH);
    float G = G_schlick(roughness, NdV, NdL);
    float rim = mix(1.0 - roughness * 0.9, 1.0, NdV);
    return (1.0 / rim) * specular * G * D;
}

vec2 env_BRDF_pproximate(float NoV, float roughness) {
    // see https://www.unrealengine.com/blog/physically-based-shading-on-mobile
    const vec4 c0 = vec4(-1.0, -0.0275, -0.572,  0.022);
    const vec4 c1 = vec4( 1.0,  0.0425,  1.040, -0.040);
    vec4 r = roughness * c0 + c1;
    float a004 = min(r.x * r.x, exp2(-9.28 * NoV)) * r.x + r.y;
    return vec2(-1.04, 1.04) * a004 + r.zw;
}


/* PBR reference
    - http://www.curious-creature.com/pbr_sandbox/shaders/pbr.fs
    - https://gist.github.com/galek/53557375251e1a942dfa */
vec4 surface_shading(vec4 base_color,
                    float metallic,
                    float roughness,
                    float reflectance,
                    samplerCube texture_cube,
                    vec3 light_color,
                    vec3 N,
                    vec3 V,
                    vec3 L,
                    float shadow_factor) {
    // compute material reflectance
    vec3 R = reflect(-V, N);
    vec3 H = normalize(V + L);
    float NdL = max(0.0, dot(N, L));
    float NdV = max(0.001, dot(N, V));
    float NdH = max(0.001, dot(N, H));
    float HdV = max(0.001, dot(H, V));
    float LdV = max(0.001, dot(L, V));

    // Fresnel specular reflectance at normal incidence
    const float ior = 1.38;
    vec3 f0 = vec3(abs ((1.0 - ior) / (1.0 + ior)));
    f0 = mix(max(vec3(0.04), f0 * reflectance * reflectance), base_color.xyz, metallic);

    // specular : mix between metal and non-metal material, for non-metal constant base specular factor of 0.04 grey is used
    vec3 specfresnel = fresnel_factor(f0, HdV);
    vec3 specular_lighting = cooktorrance_specular(NdL, NdV, NdH, specfresnel, roughness);
    specular_lighting = specular_lighting * light_color * NdL * shadow_factor;

    // diffuse
    vec3 diffuse_light = vec3(oren_nayar(roughness * roughness, NdL, NdV, N, V, L));
    diffuse_light = diffuse_light * base_color.xyz * (vec3(1.0) - specfresnel) * light_color * shadow_factor;

    // Image based lighting
    const float mipCount = 11.0;
    vec3 ibl_diffuse_color = textureLod(texture_cube, vec3(V.x, 1.0 - V.y, V.z), mipCount - 1.0).xyz;
    vec3 ibl_specular_color = textureLod(texture_cube, vec3(R.x, 1.0 - R.y, R.z), mipCount * roughness).xyz;
    ibl_diffuse_color = pow(ibl_diffuse_color, vec3(2.2));
    ibl_specular_color = pow(ibl_specular_color, vec3(2.2));

    diffuse_light += base_color.xyz * ibl_diffuse_color;
    vec2 envBRDF = clamp(env_BRDF_pproximate(NdV, roughness), 0.0, 1.0);
    specular_lighting += (fresnel_factor(f0, NdV) * envBRDF.x + envBRDF.y) * ibl_specular_color;

    // final result
    vec3 result = diffuse_light * (1.0 - metallic) + specular_lighting;
    return vec4(max(vec3(0.0), result), base_color.w);
}