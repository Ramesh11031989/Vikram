Shader "Vikram/Performance River"
{
    Properties
    {
        _Color ("River color", Color) = (0.08, 0.18, 0.23, 1)
        _SkyColor ("Sky reflection", Color) = (0.22, 0.34, 0.47, 1)
        _LanternColor ("Lantern reflection", Color) = (1, 0.47, 0.16, 1)
        _LanternPosition ("Lantern position", Vector) = (14.95, 2.34, 2.64, 1)
        _RippleScale ("Ripple scale", Range(0.25, 4)) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

            half4 _Color;
            half4 _SkyColor;
            half4 _LanternColor;
            float4 _LanternPosition;
            float _RippleScale;
            float _FilmTime;

            struct Interpolators
            {
                float4 position : SV_POSITION;
                float3 world : TEXCOORD0;
            };

            Interpolators Vert(float4 position : POSITION)
            {
                Interpolators result;
                result.position = UnityObjectToClipPos(position);
                result.world = mul(unity_ObjectToWorld, position).xyz;
                return result;
            }

            float Ripple(float phase)
            {
                return cos(phase) * (1.0 - smoothstep(0.7, 2.0, fwidth(phase)));
            }

            half4 Frag(Interpolators input) : SV_Target
            {
                float2 water = input.world.xz * _RippleScale;
                float crosswind = sin(dot(water, float2(1.8, -1.3)) + _FilmTime * 0.75);
                float longWave = Ripple(dot(water, float2(3.7, 8.1)) - _FilmTime * 2.4 + 0.8 * crosswind);
                float chop = Ripple(dot(water, float2(-7.8, 11.2)) + _FilmTime * 3.6 + crosswind);
                float capillary = Ripple(dot(water, float2(27, 14)) - _FilmTime * 5.8);
                float2 slope = longWave * float2(.036, .092) + chop * float2(-.048, .043)
                             + capillary * float2(.022, .017);
                float3 normal = normalize(float3(slope.x, 1.0, slope.y));
                float3 eye = normalize(_WorldSpaceCameraPos - input.world);
                float3 reflection = reflect(-eye, normal);
                half fresnel = .08 + .57 * pow(1.0 - saturate(dot(eye, normal)), 4.0);
                half skyAmount = .42 + .58 * smoothstep(-.08, .28, reflection.y);
                half3 color = _Color.rgb * (0.86 + .12 * longWave + .08 * chop);
                color = lerp(color, _SkyColor.rgb * (0.65 + 0.35 * skyAmount), fresnel);

                float3 lamp = _LanternPosition.xyz - input.world;
                float glint = pow(saturate(dot(normalize(lamp), reflection)), 36.0);
                glint *= saturate(1.0 - abs(lamp.x) * .44) / (1.0 + .23 * dot(lamp, lamp));
                return half4(color + _LanternColor.rgb * (.66 * glint), 1.0);
            }
            ENDCG
        }
    }
}
