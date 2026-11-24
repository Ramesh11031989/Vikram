Shader "Vikram/River Sightline"
{
    Properties
    {
        _DayColor ("Day water", Color) = (0.16, 0.28, 0.34, 1)
        _NightColor ("Night water", Color) = (0.025, 0.041, 0.068, 1)
        _RippleScale ("Ripple scale", Range(0.1, 4)) = 1
        _RippleStrength ("Ripple strength", Range(0, 1)) = 0.45
        _RiverNight ("Night amount", Range(0, 1)) = 0
        _RiverTime ("Shot time", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

            float4 _DayColor;
            float4 _NightColor;
            float _RippleScale;
            float _RippleStrength;
            float _RiverNight;
            float _RiverTime;

            struct Interpolators
            {
                float4 position : SV_POSITION;
                float3 worldPosition : TEXCOORD0;
            };

            Interpolators Vert(float4 position : POSITION)
            {
                Interpolators output;
                output.position = UnityObjectToClipPos(position);
                output.worldPosition = mul(unity_ObjectToWorld, position).xyz;
                return output;
            }

            float Ripple(float phase)
            {
                // Fade subpixel ripples at a distance instead of letting them crawl over the horizon.
                return cos(phase) * (1.0 - smoothstep(0.6, 2.0, fwidth(phase)));
            }

            half4 Frag(Interpolators input) : SV_Target
            {
                float2 water = input.worldPosition.xz * _RippleScale;
                float coarse = Ripple(dot(water, float2(1.35, 0.75)) + _RiverTime * 1.1);
                float cross = Ripple(dot(water, float2(-0.85, 2.6)) - _RiverTime * 1.7);
                float fine = Ripple(dot(water, float2(2.8, -4.0)) + _RiverTime * 2.4);
                half ripple = _RippleStrength * (0.13 * coarse + 0.08 * cross + 0.04 * fine);
                float3 view = normalize(_WorldSpaceCameraPos - input.worldPosition);
                half horizon = pow(1.0 - saturate(view.y), 3.0);
                half rim = lerp(0.15, 0.09, _RiverNight) * horizon;
                half3 baseColor = lerp(_DayColor.rgb, _NightColor.rgb, _RiverNight);
                return half4(baseColor * (1.0 + ripple + rim), 1.0);
            }
            ENDCG
        }
    }
}
