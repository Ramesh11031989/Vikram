Shader "Vikram/Performance Textile"
{
    Properties
    {
        _Color ("Dye", Color) = (1, 1, 1, 1)
        _Glossiness ("Smoothness", Range(0, 1)) = 0.15
        _Metallic ("Metallic", Range(0, 1)) = 0
        _EmissionColor ("Lamp bounce", Color) = (0, 0, 0, 1)
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Cull Off

        CGPROGRAM
        #pragma target 3.0
        #pragma surface Surface Standard fullforwardshadows vertex:Vertex

        struct Input
        {
            float3 weavePosition;
            float side : VFACE;
        };

        half4 _Color;
        half _Glossiness;
        half _Metallic;
        half4 _EmissionColor;
        float _FilmTime;

        void Vertex(inout appdata_full vertex, out Input attributes)
        {
            UNITY_INITIALIZE_OUTPUT(Input, attributes);
            attributes.weavePosition = vertex.vertex.xyz;
        }

        half Thread(float phase)
        {
            return sin(phase) * (1 - smoothstep(0.8, 2.2, fwidth(phase)));
        }

        void Surface(Input input, inout SurfaceOutputStandard surface)
        {
            float3 cloth = input.weavePosition;
            half warp = Thread(dot(cloth, float3(184, 92, 166)));
            half weft = Thread(dot(cloth, float3(-75, 47, 209)));
            surface.Albedo = _Color.rgb * (1 + .05 * warp * weft);
            surface.Normal = half3(0, 0, input.side >= 0 ? 1 : -1);
            surface.Metallic = _Metallic;
            surface.Smoothness = _Glossiness;
            surface.Emission = _EmissionColor.rgb * (.92 + .08 * sin(_FilmTime * 11));
            surface.Alpha = 1;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
